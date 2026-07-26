"""
Build a BeamNG decalRoad network from detected road vectors.

Decal roads are BeamNG's lightweight road primitive: a polyline of nodes, each
with a position and a width, that the engine paints onto the terrain surface.
That makes them the right target for AI-detected roads - no mesh, no physics
bodies, and they follow the ground automatically as long as the node heights
are close to it.

Coordinates are the part that has to be right. The previous implementation did
``x = lon * 111000`` with ``z = 0.0``, which placed every node thousands of
kilometres from the level origin at sea level. Here positions come from
:class:`LocalProjection` (metres from the region centre) and heights from
:class:`TerrainSampler`, so a road sits on the hill it was detected on.
"""

from __future__ import annotations

from typing import Any

from core.logging_config import get_logger
from core.projection import LocalProjection, TerrainSampler

logger = get_logger(__name__)

#: Material per detected road class.
MATERIAL_BY_TYPE = {
    "highway": "road_asphalt_highway",
    "motorway": "road_asphalt_highway",
    "primary": "road_asphalt",
    "secondary": "road_asphalt",
    "residential": "road_asphalt_residential",
    "service": "road_asphalt_residential",
    "track": "road_dirt",
    "dirt": "road_dirt",
    "gravel": "road_gravel",
}

#: Default width in metres when the detector did not supply one.
DEFAULT_WIDTH = 8.0

#: Nodes are lifted slightly so the decal renders above the terrain surface
#: instead of z-fighting with it.
SURFACE_OFFSET = 0.05

#: A polyline needs at least two nodes to be a road.
MIN_NODES = 2


class RoadBuilder:
    """Converts road vectors into a ``decalRoad.json`` structure."""

    def __init__(self, projection: LocalProjection, sampler: TerrainSampler | None = None) -> None:
        """
        Args:
            projection: Maps lat/lon to level-space metres.
            sampler: Supplies ground height. When omitted, nodes sit at z = 0,
                which is only correct for flat terrain.
        """
        self.projection = projection
        self.sampler = sampler

    def create_decal_roads(self, roads: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Build the decal road collection.

        Roads with fewer than two usable nodes are dropped rather than emitted
        as degenerate geometry, which BeamNG renders as a visual artefact.
        """
        entries = []
        skipped = 0

        for index, road in enumerate(roads, start=1):
            entry = self._build_road(road, index)
            if entry is None:
                skipped += 1
                continue
            entries.append(entry)

        if skipped:
            logger.info("Skipped %d road(s) with too few points", skipped)
        logger.info("Built %d decal road(s)", len(entries))

        return {"version": 1, "roads": entries}

    def _build_road(self, road: dict[str, Any], road_id: int) -> dict[str, Any] | None:
        centerline = road.get("centerline") or []
        if len(centerline) < MIN_NODES:
            return None

        width = float(road.get("width") or DEFAULT_WIDTH)
        road_type = str(road.get("type") or "residential").lower()

        nodes = []
        for point in centerline:
            if not isinstance(point, list | tuple) or len(point) < 2:
                continue
            lat, lon = float(point[0]), float(point[1])
            x, y = self.projection.to_world(lat, lon)
            z = self.sampler.elevation_at(x, y) + SURFACE_OFFSET if self.sampler else SURFACE_OFFSET
            nodes.append({"pos": [round(x, 3), round(y, 3), round(z, 3)], "width": width})

        if len(nodes) < MIN_NODES:
            return None

        return {
            "name": f"road_{road_id:04d}",
            "class": "DecalRoad",
            "persistentId": f"worldforge_road_{road_id:04d}",
            "material": MATERIAL_BY_TYPE.get(road_type, "road_asphalt"),
            "drivability": 0.7 if road_type in ("dirt", "track", "gravel") else 1.0,
            "improvedSpline": True,
            "overObjects": True,
            "renderPriority": 10,
            "breakAngle": 3.0,
            "textureLength": 5.0,
            "nodes": nodes,
        }
