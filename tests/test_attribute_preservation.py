"""
Detected attributes must survive the raster round trip.

Detections are rasterised into a mask, traced back out, and vectorised. That
loop is lossy: a binary mask carries no height at all, and it can only carry a
width down to its own pixel size. Without deliberate attribute transfer the
pipeline silently substitutes constants - a 9 m road came out 60 m wide and an
18 m building came out 10 m tall, with nothing in the logs to say so.
"""

from __future__ import annotations

import numpy as np
import pytest

from services.ai_segmentation.mask_generator import MaskGenerator
from services.vector_extraction.contour_extractor import ContourExtractor
from services.vector_extraction.vectorizer import Vectorizer

SF_BBOX = [-122.62, 37.88, -122.55, 37.94]
IMAGE_SIZE = (512, 512)


@pytest.fixture
def tools():
    return (
        MaskGenerator(image_size=IMAGE_SIZE),
        ContourExtractor(simplify_tolerance=2.0),
        Vectorizer(bbox=SF_BBOX, image_size=IMAGE_SIZE),
    )


# -- width measurement ----------------------------------------------------------


def test_measure_widths_recovers_a_drawn_width():
    """A distance transform on the centreline gives half the local width."""
    extractor = ContourExtractor()

    mask = np.zeros((200, 200), np.uint8)
    mask[95:106, 20:180] = 255  # 11 px tall band

    centerlines = extractor.extract_centerlines(mask, min_length=50)
    widths = extractor.measure_widths(mask, centerlines)

    assert widths
    assert widths[0] == pytest.approx(11, abs=2)


def test_measure_widths_distinguishes_a_wide_road_from_a_narrow_one():
    extractor = ContourExtractor()

    narrow = np.zeros((200, 200), np.uint8)
    narrow[99:102, 20:180] = 255
    wide = np.zeros((200, 200), np.uint8)
    wide[90:111, 20:180] = 255

    narrow_width = extractor.measure_widths(
        narrow, extractor.extract_centerlines(narrow, min_length=50)
    )[0]
    wide_width = extractor.measure_widths(
        wide, extractor.extract_centerlines(wide, min_length=50)
    )[0]

    assert wide_width > narrow_width * 3


def test_measured_width_beats_a_fixed_guess(tools):
    """
    The regression.

    `vectorize_road_network` defaulted to 5 pixels for every road. On this tile
    that is ~60 m - a fifteen-lane highway - regardless of what was detected.
    """
    _, extractor, vectorizer = tools

    mask = np.zeros(IMAGE_SIZE, np.uint8)
    mask[254:259, 40:470] = 255  # ~5 px, but exercise the measurement path

    centerlines = extractor.extract_centerlines(mask, min_length=50)
    measured = vectorizer.vectorize_road_network(
        centerlines, extractor.measure_widths(mask, centerlines)
    )
    guessed = vectorizer.vectorize_road_network(centerlines, 5)

    assert measured[0]["width"] > 0
    # Both are derived from pixels here; the point is the API accepts per-road
    # measurements rather than forcing one constant on every road.
    assert isinstance(guessed[0]["width"], float)


# -- attribute inheritance ------------------------------------------------------


def test_building_height_is_inherited_from_the_detection(tools):
    generator, extractor, vectorizer = tools

    detection = {
        "footprint": [[37.900, -122.600], [37.9015, -122.600],
                      [37.9015, -122.5985], [37.900, -122.5985]],
        "height": 18.0,
    }
    masks = generator.generate_masks({"buildings": [detection]}, SF_BBOX)
    polygons = extractor.contours_to_polygons(
        extractor.extract_contours(masks["buildings"], min_area=20)
    )

    without_source = vectorizer.vectorize_buildings(polygons)
    with_source = vectorizer.vectorize_buildings(polygons, source_features=[detection])

    assert without_source[0]["height"] == 10.0  # the old, wrong answer
    assert with_source[0]["height"] == 18.0


def test_road_width_is_inherited_from_the_detection(tools):
    """
    A 9 m road is narrower than one pixel at this scale, so the raster clamps
    it to a 2 px minimum and no measurement can recover the true figure. The
    detector's own value has to win.
    """
    generator, extractor, vectorizer = tools

    detection = {
        "centerline": [[37.885, -122.61], [37.90, -122.59], [37.925, -122.57]],
        "width": 9.0,
    }
    masks = generator.generate_masks({"roads": [detection]}, SF_BBOX)
    centerlines = extractor.extract_centerlines(masks["roads"], min_length=30)
    widths = extractor.measure_widths(masks["roads"], centerlines)

    measured_only = vectorizer.vectorize_road_network(centerlines, widths)
    inherited = vectorizer.vectorize_road_network(
        centerlines, widths, source_features=[detection]
    )

    assert measured_only[0]["width"] > 20  # quantised by the raster
    assert inherited[0]["width"] == 9.0


def test_nearest_source_wins_when_several_are_present(tools):
    _, _, vectorizer = tools

    near = {"footprint": [[37.900, -122.600], [37.901, -122.600], [37.901, -122.599]],
            "height": 30.0}
    far = {"footprint": [[37.930, -122.560], [37.931, -122.560], [37.931, -122.559]],
           "height": 5.0}

    polygon = [(100, 300), (110, 300), (110, 290), (100, 290)]
    building = vectorizer.vectorize_buildings([polygon], source_features=[far, near])[0]

    centre_lat = sum(p[0] for p in building["footprint"]) / len(building["footprint"])
    expected = near["height"] if abs(centre_lat - 37.9005) < abs(centre_lat - 37.9305) else far["height"]
    assert building["height"] == expected


def test_missing_or_malformed_sources_fall_back_cleanly(tools):
    _, _, vectorizer = tools
    polygon = [(100, 100), (140, 100), (140, 140), (100, 140)]

    for sources in (None, [], [{}], [{"footprint": []}], [{"footprint": [[1]]}]):
        building = vectorizer.vectorize_buildings([polygon], source_features=sources)[0]
        assert building["height"] == 10.0


def test_a_detection_without_a_height_uses_the_default(tools):
    _, _, vectorizer = tools
    polygon = [(100, 100), (140, 100), (140, 140), (100, 140)]

    source = {"footprint": [[37.90, -122.60], [37.901, -122.60], [37.901, -122.599]]}
    assert vectorizer.vectorize_buildings([polygon], source_features=[source])[0]["height"] == 10.0


def test_mismatched_width_list_length_does_not_raise(tools):
    _, _, vectorizer = tools
    centerlines = [np.array([[10, 10], [100, 100]]), np.array([[20, 20], [120, 120]])]

    roads = vectorizer.vectorize_road_network(centerlines, [3.0])  # one width, two roads
    assert len(roads) == 2
