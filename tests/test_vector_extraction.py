"""
Mask -> contours -> geographic vectors -> BeamNG level content.

This chain had no tests, and it is the only path that produces roads and
buildings, so a break in it silently yields an empty level rather than an
error. The last test walks the whole chain end to end: the seams between these
modules are exactly where the previous bugs lived.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.geo import meters_per_degree_lon
from core.projection import LocalProjection
from services.beamng_integration import BuildingPlacer, MeshBuilder, RoadBuilder
from services.vector_extraction.contour_extractor import ContourExtractor
from services.vector_extraction.skeleton import simplify_polyline, trace_skeleton
from services.vector_extraction.vectorizer import Vectorizer

SF_BBOX = [-122.62, 37.88, -122.55, 37.94]
IMAGE_SIZE = (512, 512)  # (height, width)


def polyline_length(points) -> float:
    return float(sum(np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])))


# -- skeleton tracing -----------------------------------------------------------


def skeletonise(mask: np.ndarray) -> np.ndarray:
    from skimage.morphology import skeletonize

    return skeletonize(mask > 0)


def test_straight_road_traces_to_one_branch():
    mask = np.zeros((80, 80), np.uint8)
    mask[40, 5:60] = 255

    paths = trace_skeleton(skeletonise(mask))

    assert len(paths) == 1
    assert polyline_length(paths[0]) == pytest.approx(54, abs=2)


def test_a_bent_road_is_not_retraced():
    """
    The regression.

    `cv2.findContours` over a skeleton traces the outline, so an L-shaped road
    of 85 skeleton pixels came back as a 137-pixel path that ran to the far end
    and back. Tracing the graph visits each pixel once.
    """
    mask = np.zeros((80, 80), np.uint8)
    mask[40, 5:60] = 255
    mask[10:40, 58] = 255

    skeleton = skeletonise(mask)
    paths = trace_skeleton(skeleton)

    long_branches = [path for path in paths if polyline_length(path) > 10]
    total = sum(polyline_length(path) for path in long_branches)

    assert len(long_branches) == 2
    # The retraced version was ~1.6x the true skeleton length.
    assert total <= int(skeleton.sum()) * 1.1


def test_a_junction_splits_into_separate_branches():
    mask = np.zeros((80, 80), np.uint8)
    mask[40, 5:75] = 255
    mask[10:40, 40] = 255

    paths = [p for p in trace_skeleton(skeletonise(mask)) if polyline_length(p) > 10]

    # Stem plus the two arms of the T.
    assert len(paths) == 3


def test_a_closed_loop_is_traced_once():
    import cv2

    mask = np.zeros((80, 80), np.uint8)
    cv2.circle(mask, (40, 40), 20, 255, 1)

    paths = [p for p in trace_skeleton(skeletonise(mask)) if polyline_length(p) > 10]

    assert len(paths) == 1
    # Circumference of a radius-20 circle is ~126.
    assert polyline_length(paths[0]) == pytest.approx(126, rel=0.25)


def test_empty_and_invalid_input():
    assert trace_skeleton(np.zeros((10, 10))) == []
    with pytest.raises(ValueError):
        trace_skeleton(np.zeros((4, 4, 3)))


def test_simplify_keeps_the_shape():
    straight = [(x, 10) for x in range(50)]
    assert simplify_polyline(straight, 2.0) == [(0, 10), (49, 10)]

    corner = [(x, 10) for x in range(25)] + [(24, y) for y in range(11, 35)]
    simplified = simplify_polyline(corner, 2.0)
    assert 3 <= len(simplified) <= 5  # the corner survives
    assert simplified[0] == corner[0]
    assert simplified[-1] == corner[-1]


# -- contour extraction ---------------------------------------------------------


@pytest.fixture
def extractor() -> ContourExtractor:
    return ContourExtractor(simplify_tolerance=2.0)


def test_contours_are_extracted_from_a_bool_mask(extractor):
    """skimage returns bool masks; OpenCV needs uint8."""
    mask = np.zeros((100, 100), dtype=bool)
    mask[20:60, 20:60] = True

    contours = extractor.extract_contours(mask, min_area=100)
    assert len(contours) == 1


def test_small_blobs_are_filtered_out(extractor):
    mask = np.zeros((100, 100), np.uint8)
    mask[10:14, 10:14] = 255      # 16 px
    mask[40:80, 40:80] = 255      # 1600 px

    assert len(extractor.extract_contours(mask, min_area=100)) == 1


def test_centerlines_have_opencv_contour_shape(extractor):
    mask = np.zeros((200, 200), np.uint8)
    mask[100, 10:190] = 255

    centerlines = extractor.extract_centerlines(mask, min_length=50)

    assert len(centerlines) == 1
    assert centerlines[0].ndim == 3
    assert centerlines[0].shape[1:] == (1, 2)


def test_short_centerlines_are_dropped(extractor):
    mask = np.zeros((200, 200), np.uint8)
    mask[100, 10:30] = 255  # 20 px, under the threshold

    assert extractor.extract_centerlines(mask, min_length=50) == []


def test_rectangle_to_polygon_works_on_numpy_2(extractor):
    """`np.int0` was removed in NumPy 2, so this used to raise AttributeError."""
    mask = np.zeros((100, 100), np.uint8)
    mask[20:60, 30:70] = 255

    rectangles = extractor.extract_rectangles(mask, min_area=100)
    polygon = extractor.rectangle_to_polygon(rectangles[0])

    assert len(polygon) == 4
    assert all(isinstance(value, int) for point in polygon for value in point)


# -- vectorising ----------------------------------------------------------------


@pytest.fixture
def vectorizer() -> Vectorizer:
    return Vectorizer(bbox=SF_BBOX, image_size=IMAGE_SIZE)


def test_pixel_corners_map_to_bbox_corners(vectorizer):
    top_left_lat, top_left_lon = vectorizer.pixel_to_geo((0, 0))
    bottom_right_lat, bottom_right_lon = vectorizer.pixel_to_geo((511, 511))

    assert top_left_lon == pytest.approx(SF_BBOX[0], abs=1e-6)
    assert top_left_lat == pytest.approx(SF_BBOX[3], abs=0.001)
    assert bottom_right_lon == pytest.approx(SF_BBOX[2], abs=0.001)
    assert bottom_right_lat == pytest.approx(SF_BBOX[1], abs=0.001)


def test_image_rows_run_north_to_south(vectorizer):
    north, _ = vectorizer.pixel_to_geo((256, 0))
    south, _ = vectorizer.pixel_to_geo((256, 511))
    assert north > south


def test_ground_scale_is_corrected_for_latitude(vectorizer):
    """
    The regression: `degrees * 111000` on the longitude axis.

    At 37.9 degrees that overstates east-west distance by about 21%, so every
    road width and feature area came out too large.
    """
    center_lat = (SF_BBOX[1] + SF_BBOX[3]) / 2
    expected = (SF_BBOX[2] - SF_BBOX[0]) * meters_per_degree_lon(center_lat) / IMAGE_SIZE[1]

    assert vectorizer.meters_per_pixel_x == pytest.approx(expected, rel=1e-6)
    # Naive version, for contrast.
    naive = (SF_BBOX[2] - SF_BBOX[0]) * 111_320 / IMAGE_SIZE[1]
    assert vectorizer.meters_per_pixel_x < naive * 0.85


def test_road_width_is_in_plausible_metres(vectorizer):
    centerline = np.array([[10, 10], [200, 200]], dtype=np.int32)
    roads = vectorizer.vectorize_road_network([centerline], width_pixels=5)

    assert 0 < roads[0]["width"] < 100
    assert len(roads[0]["centerline"]) == 2


def test_vectorizer_output_matches_what_the_exporter_consumes(vectorizer):
    """
    Contract between vector_extraction and beamng_integration.

    The producers and consumers of these dicts live in different packages and
    were never exercised together.
    """
    road = vectorizer.vectorize_road_network([np.array([[10, 10], [200, 200]])])[0]
    building = vectorizer.vectorize_buildings([[(10, 10), (40, 10), (40, 40), (10, 40)]])[0]

    assert {"centerline", "width", "type"} <= road.keys()
    assert {"footprint", "height", "type"} <= building.keys()
    # Consumers index points as [lat, lon].
    assert all(len(point) == 2 for point in road["centerline"])
    assert all(len(point) == 2 for point in building["footprint"])


def test_geojson_is_wellformed(vectorizer):
    roads = vectorizer.vectorize_road_network([np.array([[10, 10], [200, 200]])])
    geojson = vectorizer.create_geojson(roads, "roads")

    assert geojson["type"] == "FeatureCollection"
    assert geojson["features"]
    for feature in geojson["features"]:
        assert feature["type"] == "Feature"
        assert "coordinates" in feature["geometry"]


# -- the whole chain ------------------------------------------------------------


def test_mask_to_placed_level_content():
    """
    Mask -> contours -> vectors -> decal roads and building items.

    Every stage boundary in one test, because each of the three bugs fixed in
    this area lived at a boundary rather than inside a module.
    """
    road_mask = np.zeros(IMAGE_SIZE, np.uint8)
    road_mask[256, 20:490] = 255
    road_mask[60:256, 300] = 255

    building_mask = np.zeros(IMAGE_SIZE, np.uint8)
    building_mask[100:160, 100:160] = 255
    building_mask[300:340, 380:430] = 255

    extractor = ContourExtractor()
    vectorizer = Vectorizer(bbox=SF_BBOX, image_size=IMAGE_SIZE)

    roads = vectorizer.vectorize_road_network(
        extractor.extract_centerlines(road_mask, min_length=50)
    )
    buildings = vectorizer.vectorize_buildings(
        extractor.contours_to_polygons(extractor.extract_contours(building_mask, min_area=100))
    )

    assert len(roads) >= 2, "the road mask has a stem and two arms"
    assert len(buildings) == 2

    projection = LocalProjection.from_bbox(SF_BBOX)
    decal = RoadBuilder(projection).create_decal_roads(roads)
    assert decal["roads"], "vectorised roads must survive into level content"

    mesh_builder = MeshBuilder(projection)
    meshes = [mesh_builder.build_mesh(building, index) for index, building in enumerate(buildings, 1)]
    assert all(mesh is not None for mesh in meshes)

    items = BuildingPlacer(projection).create_building_items(
        buildings, [f"levels/x/art/shapes/buildings/b{i}.dae" for i in range(len(buildings))]
    )
    assert len(items) == 2

    # Everything must land inside the terrain block, not thousands of km away.
    for item in items:
        x, y, _ = item["position"]
        assert abs(x) < 5_000 and abs(y) < 5_000
    for entry in decal["roads"]:
        for node in entry["nodes"]:
            assert abs(node["pos"][0]) < 5_000 and abs(node["pos"][1]) < 5_000
