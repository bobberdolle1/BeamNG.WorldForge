"""
Extrude building footprints into COLLADA meshes.

Deterministic, and deliberately so. The previous implementation asked a
language model to emit COLLADA XML for each building and fell back to
procedural extrusion whenever the generated document failed validation. Writing
a fixed-schema XML file is not a task that benefits from a model: the
procedural path produces correct geometry every time, in microseconds, with no
network call, no API key and no nondeterminism. Only the fallback survives.

The mesh is built in the building's own local space, centred on its footprint
centroid with its base at z = 0, so the level item can place it with a plain
translation.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from core.logging_config import get_logger
from core.projection import LocalProjection

logger = get_logger(__name__)

COLLADA_NAMESPACE = "http://www.collada.org/2005/11/COLLADASchema"

#: Footprints are simplified to at most this many points. Detected outlines can
#: carry hundreds of near-collinear vertices, which bloat the mesh without
#: changing its silhouette at the scale a building is viewed from.
MAX_FOOTPRINT_POINTS = 12

DEFAULT_HEIGHT = 10.0
MIN_HEIGHT = 2.0


def simplify_footprint(
    footprint: list[tuple[float, float]], max_points: int = MAX_FOOTPRINT_POINTS
) -> list[tuple[float, float]]:
    """Reduce a footprint to at most ``max_points`` evenly spaced vertices."""
    if len(footprint) <= max_points:
        return list(footprint)

    step = len(footprint) / max_points
    return [footprint[int(index * step)] for index in range(max_points)]


def polygon_area(points: list[tuple[float, float]]) -> float:
    """Signed area of a polygon via the shoelace formula."""
    area = 0.0
    for index, (x0, y0) in enumerate(points):
        x1, y1 = points[(index + 1) % len(points)]
        area += x0 * y1 - x1 * y0
    return area / 2.0


class MeshBuilder:
    """Builds extruded building meshes as COLLADA documents."""

    def __init__(self, projection: LocalProjection) -> None:
        self.projection = projection

    def build_mesh(self, building: dict[str, Any], building_id: int) -> str | None:
        """
        Extrude one building footprint.

        Returns:
            A COLLADA document, or ``None`` if the footprint is unusable.
        """
        raw_footprint = [
            point for point in (building.get("footprint") or [])
            if isinstance(point, list | tuple) and len(point) >= 2
        ]
        if len(raw_footprint) < 3:
            return None

        simplified = simplify_footprint([(float(p[0]), float(p[1])) for p in raw_footprint])

        # Project to metres, then re-centre on the centroid so the mesh sits at
        # its own origin and the level item positions it with a translation.
        world = [self.projection.to_world(lat, lon) for lat, lon in simplified]
        center_x = sum(x for x, _ in world) / len(world)
        center_y = sum(y for _, y in world) / len(world)
        local = [(x - center_x, y - center_y) for x, y in world]

        if abs(polygon_area(local)) < 1.0:
            # Under a square metre of floor area is detector noise, not a
            # building; extruding it produces a sliver that renders as a glitch.
            return None

        # A negative signed area means clockwise winding, which would leave the
        # roof facing downwards and the walls inside out.
        if polygon_area(local) < 0:
            local.reverse()

        height = max(float(building.get("height") or DEFAULT_HEIGHT), MIN_HEIGHT)
        vertices, triangles = self._extrude(local, height)
        return self._to_collada(vertices, triangles, building_id)

    @staticmethod
    def _extrude(
        footprint: list[tuple[float, float]], height: float
    ) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
        """Extrude a counter-clockwise polygon upwards into a closed solid."""
        count = len(footprint)
        base = [(x, y, 0.0) for x, y in footprint]
        top = [(x, y, height) for x, y in footprint]
        vertices = base + top

        triangles: list[tuple[int, int, int]] = []

        # Roof: fan triangulation, counter-clockwise seen from above.
        for index in range(1, count - 1):
            triangles.append((count, count + index, count + index + 1))

        # Floor: same fan with reversed winding so it faces down.
        for index in range(1, count - 1):
            triangles.append((0, index + 1, index))

        # Walls: two triangles per edge.
        for index in range(count):
            next_index = (index + 1) % count
            triangles.append((index, next_index, next_index + count))
            triangles.append((index, next_index + count, index + count))

        return vertices, triangles

    @staticmethod
    def _to_collada(
        vertices: list[tuple[float, float, float]],
        triangles: list[tuple[int, int, int]],
        building_id: int,
    ) -> str:
        """
        Serialise geometry as a COLLADA 1.4.1 document.

        Built with ElementTree rather than string formatting so the output is
        always well-formed XML - the string-building version could emit invalid
        documents for footprints containing unexpected values.
        """
        ET.register_namespace("", COLLADA_NAMESPACE)
        name = f"building_{building_id:04d}"

        collada = ET.Element(f"{{{COLLADA_NAMESPACE}}}COLLADA", version="1.4.1")

        asset = ET.SubElement(collada, "asset")
        ET.SubElement(asset, "up_axis").text = "Z_UP"
        ET.SubElement(asset, "unit", name="meter", meter="1")

        geometries = ET.SubElement(collada, "library_geometries")
        geometry = ET.SubElement(geometries, "geometry", id=f"{name}_geo", name=name)
        mesh = ET.SubElement(geometry, "mesh")

        positions = [coordinate for vertex in vertices for coordinate in vertex]
        source = ET.SubElement(mesh, "source", id=f"{name}_positions")
        float_array = ET.SubElement(
            source,
            "float_array",
            id=f"{name}_positions_array",
            count=str(len(positions)),
        )
        float_array.text = " ".join(f"{value:.4f}" for value in positions)

        technique = ET.SubElement(source, "technique_common")
        accessor = ET.SubElement(
            technique,
            "accessor",
            source=f"#{name}_positions_array",
            count=str(len(vertices)),
            stride="3",
        )
        for axis in ("X", "Y", "Z"):
            ET.SubElement(accessor, "param", name=axis, type="float")

        vertices_element = ET.SubElement(mesh, "vertices", id=f"{name}_vertices")
        ET.SubElement(
            vertices_element, "input", semantic="POSITION", source=f"#{name}_positions"
        )

        triangles_element = ET.SubElement(mesh, "triangles", count=str(len(triangles)))
        ET.SubElement(
            triangles_element,
            "input",
            semantic="VERTEX",
            source=f"#{name}_vertices",
            offset="0",
        )
        ET.SubElement(triangles_element, "p").text = " ".join(
            str(index) for triangle in triangles for index in triangle
        )

        scenes = ET.SubElement(collada, "library_visual_scenes")
        scene = ET.SubElement(scenes, "visual_scene", id="Scene", name="Scene")
        node = ET.SubElement(scene, "node", id=name, name=name, type="NODE")
        ET.SubElement(node, "instance_geometry", url=f"#{name}_geo")

        ET.SubElement(
            ET.SubElement(collada, "scene"), "instance_visual_scene", url="#Scene"
        )

        return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(
            collada, encoding="unicode"
        )
