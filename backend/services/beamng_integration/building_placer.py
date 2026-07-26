"""
Place detected buildings into a BeamNG level.

Each building becomes a ``TSStatic`` item in ``items.level.json`` pointing at a
COLLADA mesh extruded from its footprint (see :mod:`mesh_builder`).

As with roads, the coordinate handling is the substance here. The previous
version computed ``x = lon * 111000, y = lat * 111000, z = 0.0``, which put
every building at an absolute position far outside the terrain block and at sea
level. Positions now come from :class:`LocalProjection` and heights from
:class:`TerrainSampler`, so buildings stand on the ground.
"""

from __future__ import annotations

from typing import Any

from core.logging_config import get_logger
from core.projection import LocalProjection, TerrainSampler

logger = get_logger(__name__)

#: Height used when the detector did not estimate one.
DEFAULT_HEIGHT = 10.0

#: A footprint needs three points to enclose any area.
MIN_FOOTPRINT_POINTS = 3


class BuildingPlacer:
    """Turns building vectors into level items."""

    def __init__(self, projection: LocalProjection, sampler: TerrainSampler | None = None) -> None:
        self.projection = projection
        self.sampler = sampler

    def create_building_items(
        self,
        buildings: list[dict[str, Any]],
        mesh_paths: list[str],
    ) -> list[dict[str, Any]]:
        """
        Build ``items.level.json`` entries.

        Args:
            buildings: Detected building vectors.
            mesh_paths: Level-relative mesh path per building, same order.

        Returns:
            One item per building that has both a usable footprint and a mesh.
        """
        if len(buildings) != len(mesh_paths):
            # Pairing by zip alone would silently truncate to the shorter list;
            # saying so makes a caller bug visible instead of producing a level
            # that is quietly missing buildings.
            logger.warning(
                "Building/mesh count mismatch: %d buildings, %d meshes - pairing the overlap",
                len(buildings),
                len(mesh_paths),
            )

        items = []
        for index, (building, mesh_path) in enumerate(
            zip(buildings, mesh_paths, strict=False), start=1
        ):
            item = self._build_item(building, mesh_path, index)
            if item is not None:
                items.append(item)

        logger.info("Placed %d building item(s)", len(items))
        return items

    def _build_item(
        self, building: dict[str, Any], mesh_path: str, building_id: int
    ) -> dict[str, Any] | None:
        footprint = [
            point for point in (building.get("footprint") or [])
            if isinstance(point, list | tuple) and len(point) >= 2
        ]
        if len(footprint) < MIN_FOOTPRINT_POINTS:
            return None

        center_lat = sum(float(point[0]) for point in footprint) / len(footprint)
        center_lon = sum(float(point[1]) for point in footprint) / len(footprint)

        x, y = self.projection.to_world(center_lat, center_lon)
        z = self.sampler.elevation_at(x, y) if self.sampler else 0.0

        return {
            "class": "TSStatic",
            "persistentId": f"worldforge_building_{building_id:04d}",
            "name": f"building_{building_id:04d}",
            "shapeName": mesh_path,
            "position": [round(x, 3), round(y, 3), round(z, 3)],
            # Identity rotation: the mesh is built in world-aligned local space,
            # so it needs no reorientation.
            "rotationMatrix": [1, 0, 0, 0, 1, 0, 0, 0, 1],
            "scale": [1, 1, 1],
            "collisionType": "Visible Mesh Final",
            "decalType": "None",
            "isRenderEnabled": True,
            "useInstanceRenderData": True,
            "height": round(float(building.get("height") or DEFAULT_HEIGHT), 2),
        }
