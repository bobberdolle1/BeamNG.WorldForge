"""
Rasterising AI detections back into masks.

The important property is that this is the exact inverse of
:class:`Vectorizer`: detections are drawn into a mask, contours are traced out
of it, and the result is vectorised back to coordinates. If the two disagree,
features drift across the map with no error anywhere.
"""

from __future__ import annotations

import numpy as np
import pytest

from services.ai_segmentation.mask_generator import MaskGenerator
from services.vector_extraction.vectorizer import Vectorizer

SF_BBOX = [-122.62, 37.88, -122.55, 37.94]
IMAGE_SIZE = (512, 512)


@pytest.fixture
def generator() -> MaskGenerator:
    return MaskGenerator(image_size=IMAGE_SIZE)


def square_footprint(lat: float, lon: float, size: float = 0.002) -> list[list[float]]:
    return [[lat, lon], [lat + size, lon], [lat + size, lon + size], [lat, lon + size]]


# -- coordinate conversion ------------------------------------------------------

def test_corners_map_to_image_corners(generator):
    min_lon, min_lat, max_lon, max_lat = SF_BBOX

    assert generator._geo_to_pixel([max_lat, min_lon], SF_BBOX) == (0, 0)

    x, y = generator._geo_to_pixel([min_lat, max_lon], SF_BBOX)
    assert (x, y) == (IMAGE_SIZE[1] - 1, IMAGE_SIZE[0] - 1)


def test_geo_to_pixel_is_the_inverse_of_pixel_to_geo(generator):
    """
    The two modules must agree, or features move between rasterising and
    vectorising.
    """
    vectorizer = Vectorizer(bbox=SF_BBOX, image_size=IMAGE_SIZE)

    for pixel in [(0, 0), (100, 250), (511, 511), (256, 256)]:
        lat, lon = vectorizer.pixel_to_geo(pixel)
        assert generator._geo_to_pixel([lat, lon], SF_BBOX) == pytest.approx(pixel, abs=1)


def test_points_outside_the_bbox_are_clamped(generator):
    x, y = generator._geo_to_pixel([90.0, 179.0], SF_BBOX)
    assert 0 <= x < IMAGE_SIZE[1]
    assert 0 <= y < IMAGE_SIZE[0]


def test_degenerate_bbox_does_not_divide_by_zero(generator):
    flat = [-122.6, 37.9, -122.6, 37.9]
    assert generator._geo_to_pixel([37.9, -122.6], flat) == (256, 256)


# -- rasterising ----------------------------------------------------------------

def test_masks_are_uint8_and_binary(generator):
    masks = generator.generate_masks(
        {"buildings": [{"footprint": square_footprint(37.90, -122.60)}]}, SF_BBOX
    )

    mask = masks["buildings"]
    assert mask.dtype == np.uint8
    assert mask.shape == IMAGE_SIZE
    assert set(np.unique(mask)) <= {0, 255}


def test_a_building_covers_a_plausible_area(generator):
    masks = generator.generate_masks(
        {"buildings": [{"footprint": square_footprint(37.90, -122.60, size=0.002)}]}, SF_BBOX
    )

    covered = int((masks["buildings"] > 0).sum())
    assert covered > 0
    assert covered < masks["buildings"].size // 2


def test_road_width_uses_latitude_corrected_scale(generator):
    """
    Regression: the metres-to-pixels conversion treated a degree of longitude
    as a degree of latitude, so a 20 m road was drawn ~21% too narrow here.
    """
    masks = generator.generate_masks(
        {"roads": [{"centerline": [[37.90, -122.61], [37.90, -122.56]], "width": 40.0}]},
        SF_BBOX,
    )

    rows = np.where(masks["roads"] > 0)[0]
    drawn_width = rows.max() - rows.min() + 1

    metres_per_pixel_y = (SF_BBOX[3] - SF_BBOX[1]) * 111_320 / IMAGE_SIZE[0]
    expected = 40.0 / metres_per_pixel_y

    assert drawn_width == pytest.approx(expected, rel=0.35)


def test_degenerate_features_are_skipped(generator):
    masks = generator.generate_masks(
        {
            "roads": [{"centerline": [[37.90, -122.60]]}],       # single point
            "buildings": [{"footprint": [[37.90, -122.60]]}],    # not a polygon
        },
        SF_BBOX,
    )

    assert not masks["roads"].any()
    assert not masks["buildings"].any()


def test_empty_detections_yield_empty_masks(generator):
    masks = generator.generate_masks({"roads": [], "buildings": []}, SF_BBOX)

    assert set(masks) == {"roads", "buildings"}
    assert not masks["roads"].any()


# -- the round trip -------------------------------------------------------------

def test_a_building_survives_rasterise_then_vectorise(generator):
    """
    Draw a footprint into a mask, trace it back out, and check it lands where
    it started. This is the seam between ai_segmentation and vector_extraction.
    """
    from services.vector_extraction.contour_extractor import ContourExtractor

    original = square_footprint(37.90, -122.60, size=0.004)
    masks = generator.generate_masks({"buildings": [{"footprint": original}]}, SF_BBOX)

    extractor = ContourExtractor(simplify_tolerance=1.0)
    polygons = extractor.contours_to_polygons(
        extractor.extract_contours(masks["buildings"], min_area=50)
    )
    assert len(polygons) == 1

    vectorizer = Vectorizer(bbox=SF_BBOX, image_size=IMAGE_SIZE)
    recovered = vectorizer.vectorize_buildings(polygons)[0]["footprint"]

    original_lats = [point[0] for point in original]
    original_lons = [point[1] for point in original]
    recovered_lats = [point[0] for point in recovered]
    recovered_lons = [point[1] for point in recovered]

    # Within a pixel of where it was drawn.
    tolerance = (SF_BBOX[3] - SF_BBOX[1]) / IMAGE_SIZE[0] * 2
    assert min(recovered_lats) == pytest.approx(min(original_lats), abs=tolerance)
    assert max(recovered_lats) == pytest.approx(max(original_lats), abs=tolerance)
    assert min(recovered_lons) == pytest.approx(min(original_lons), abs=tolerance)
    assert max(recovered_lons) == pytest.approx(max(original_lons), abs=tolerance)
