"""
Projection, terrain sampling, and the level content built from detected vectors.

The single most important property here: object positions must be *local* to
the level. The original implementation used ``x = lon * 111000``, which placed
a San Francisco road node at x = -13,586,400 - about 13,600 km from the level
origin, far outside both the terrain block and the range where 32-bit floats
keep centimetre precision.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import numpy as np
import pytest

from core.geo import bbox_dimensions
from core.projection import LocalProjection, TerrainSampler
from services.beamng_integration import BuildingPlacer, MeshBuilder, RoadBuilder
from services.beamng_integration.mesh_builder import polygon_area, simplify_footprint

SF_BBOX = [-122.62, 37.88, -122.55, 37.94]


@pytest.fixture
def projection() -> LocalProjection:
    return LocalProjection.from_bbox(SF_BBOX)


@pytest.fixture
def sampler() -> TerrainSampler:
    """A 256x256 ramp from 100 m (north-west) to 800 m (south-east)."""
    heightmap = np.linspace(0, 65535, 256 * 256).reshape(256, 256).astype(np.uint16)
    return TerrainSampler(
        heightmap, min_elevation=100.0, elevation_range=700.0, square_size=10.0
    )


# -- projection -----------------------------------------------------------------


def test_centre_of_the_region_is_the_origin(projection):
    x, y = projection.to_world(37.91, -122.585)
    assert x == pytest.approx(0.0, abs=0.1)
    assert y == pytest.approx(0.0, abs=0.1)


def test_corners_land_at_half_the_ground_size(projection):
    """The regression: positions must be local metres, not absolute ones."""
    dimensions = bbox_dimensions(*SF_BBOX)

    x, y = projection.to_world(37.94, -122.55)

    assert x == pytest.approx(dimensions.width_meters / 2, rel=0.01)
    assert y == pytest.approx(dimensions.height_meters / 2, rel=0.01)
    # The old formula produced ~-13.6 million here.
    assert abs(x) < 10_000
    assert abs(y) < 10_000


def test_longitude_is_scaled_by_latitude():
    """One degree of longitude is half as long at 60 degrees as at the equator."""
    equator = LocalProjection.from_bbox([-0.1, -0.1, 0.1, 0.1])
    high_latitude = LocalProjection.from_bbox([-0.1, 59.9, 0.1, 60.1])

    assert high_latitude.meters_per_deg_lon == pytest.approx(
        equator.meters_per_deg_lon / 2, rel=0.01
    )


def test_projection_round_trips(projection):
    lat, lon = projection.to_geographic(*projection.to_world(37.9, -122.6))
    assert lat == pytest.approx(37.9, abs=1e-9)
    assert lon == pytest.approx(-122.6, abs=1e-9)


def test_north_is_positive_y(projection):
    _, south = projection.to_world(37.89, -122.585)
    _, north = projection.to_world(37.93, -122.585)
    assert north > south


# -- terrain sampling -----------------------------------------------------------


def test_samples_the_real_elevation_range(sampler):
    # Row 0 / column 0 is the north-west corner of the ramp.
    assert sampler.elevation_at(-1280, 1280) == pytest.approx(100.0, abs=1.0)
    assert sampler.elevation_at(1270, -1270) == pytest.approx(800.0, abs=2.0)


def test_positions_outside_the_terrain_are_clamped(sampler):
    """A feature detected just off the DEM edge must not crash the export."""
    assert 100.0 <= sampler.elevation_at(1e6, 1e6) <= 800.0
    assert 100.0 <= sampler.elevation_at(-1e6, -1e6) <= 800.0


def test_sampler_rejects_non_2d_heightmaps():
    with pytest.raises(ValueError):
        TerrainSampler(
            np.zeros((4, 4, 3), dtype=np.uint16),
            min_elevation=0,
            elevation_range=1,
            square_size=1,
        )


# -- roads ----------------------------------------------------------------------


def test_road_nodes_sit_on_the_terrain(projection, sampler):
    roads = [{"centerline": [[37.90, -122.60], [37.91, -122.58]], "width": 9.0, "type": "primary"}]

    result = RoadBuilder(projection, sampler).create_decal_roads(roads)

    nodes = result["roads"][0]["nodes"]
    assert len(nodes) == 2
    for node in nodes:
        x, y, z = node["pos"]
        assert abs(x) < 10_000 and abs(y) < 10_000
        # z = 0 was the old behaviour; every node now tracks the ground.
        assert z > 100.0


def test_degenerate_roads_are_dropped(projection, sampler):
    roads = [
        {"centerline": [[37.90, -122.60]]},            # single point
        {"centerline": []},                            # empty
        {},                                            # no centerline at all
        {"centerline": [[37.90, -122.60], [37.91, -122.58]]},  # valid
    ]

    result = RoadBuilder(projection, sampler).create_decal_roads(roads)
    assert len(result["roads"]) == 1


def test_road_material_follows_the_detected_type(projection, sampler):
    builder = RoadBuilder(projection, sampler)

    highway = builder.create_decal_roads(
        [{"centerline": [[37.90, -122.60], [37.91, -122.58]], "type": "highway"}]
    )["roads"][0]
    dirt = builder.create_decal_roads(
        [{"centerline": [[37.90, -122.60], [37.91, -122.58]], "type": "dirt"}]
    )["roads"][0]

    assert highway["material"] == "road_asphalt_highway"
    assert dirt["material"] == "road_dirt"
    assert dirt["drivability"] < highway["drivability"]


def test_roads_work_without_a_sampler(projection):
    """No terrain available is a degraded case, not a crash."""
    result = RoadBuilder(projection).create_decal_roads(
        [{"centerline": [[37.90, -122.60], [37.91, -122.58]]}]
    )
    assert result["roads"][0]["nodes"][0]["pos"][2] == pytest.approx(0.05)


# -- buildings ------------------------------------------------------------------


def square_footprint(lat: float = 37.90, lon: float = -122.60, size: float = 0.0005) -> list:
    return [[lat, lon], [lat + size, lon], [lat + size, lon + size], [lat, lon + size]]


def test_building_is_positioned_locally_and_on_the_ground(projection, sampler):
    building = {"footprint": square_footprint(), "height": 24.0}

    items = BuildingPlacer(projection, sampler).create_building_items(
        [building], ["levels/x/art/shapes/buildings/b.dae"]
    )

    x, y, z = items[0]["position"]
    assert abs(x) < 10_000 and abs(y) < 10_000
    assert z > 100.0
    assert items[0]["shapeName"] == "levels/x/art/shapes/buildings/b.dae"


def test_buildings_without_a_usable_footprint_are_skipped(projection, sampler):
    buildings = [{"footprint": [[37.9, -122.6], [37.9, -122.59]]}, {"footprint": []}]

    items = BuildingPlacer(projection, sampler).create_building_items(
        buildings, ["a.dae", "b.dae"]
    )
    assert items == []


# -- meshes ---------------------------------------------------------------------


def test_mesh_is_well_formed_collada(projection):
    mesh = MeshBuilder(projection).build_mesh(
        {"footprint": square_footprint(), "height": 20.0}, 1
    )

    assert mesh is not None
    root = ET.fromstring(mesh.split("?>", 1)[1])
    assert root.tag.endswith("COLLADA")
    assert root.get("version") == "1.4.1"


def test_mesh_geometry_is_closed_and_correctly_sized(projection):
    mesh = MeshBuilder(projection).build_mesh(
        {"footprint": square_footprint(), "height": 20.0}, 1
    )
    root = ET.fromstring(mesh.split("?>", 1)[1])
    namespace = {"c": "http://www.collada.org/2005/11/COLLADASchema"}

    positions = [
        float(value)
        for value in root.find(".//c:float_array", namespace).text.split()
    ]
    coordinates = np.array(positions).reshape(-1, 3)

    # Four footprint points -> four base + four top vertices.
    assert coordinates.shape == (8, 3)
    # Base at z = 0, roof at the requested height.
    assert coordinates[:, 2].min() == pytest.approx(0.0)
    assert coordinates[:, 2].max() == pytest.approx(20.0)
    # Centred on its own origin so the item can place it by translation alone.
    assert coordinates[:, 0].mean() == pytest.approx(0.0, abs=0.01)

    triangle_count = int(root.find(".//c:triangles", namespace).get("count"))
    # 2 roof + 2 floor + 2 per wall edge.
    assert triangle_count == 2 + 2 + 4 * 2


def test_tiny_footprints_are_rejected(projection):
    """Sub-square-metre detections are noise, and extrude into visual glitches."""
    tiny = [[37.90, -122.60], [37.900001, -122.60], [37.900001, -122.599999]]
    assert MeshBuilder(projection).build_mesh({"footprint": tiny, "height": 10}, 1) is None


def test_clockwise_footprints_are_reoriented(projection):
    clockwise = list(reversed(square_footprint()))
    mesh = MeshBuilder(projection).build_mesh({"footprint": clockwise, "height": 10}, 1)
    assert mesh is not None  # would otherwise be inside out


def test_simplify_caps_the_vertex_count():
    footprint = [(37.9 + i * 1e-5, -122.6) for i in range(200)]
    assert len(simplify_footprint(footprint, max_points=12)) == 12
    assert simplify_footprint(footprint[:5], max_points=12) == footprint[:5]


def test_polygon_area_sign_indicates_winding():
    counter_clockwise = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    assert polygon_area(counter_clockwise) == pytest.approx(1.0)
    assert polygon_area(list(reversed(counter_clockwise))) == pytest.approx(-1.0)
