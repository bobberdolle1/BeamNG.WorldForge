"""
Export generated maps to BeamNG.drive mod format.

Layout produced::

    <map_name>.zip
    └── levels/<map_name>/
        ├── info.json                     Level metadata shown in-game
        ├── main.level.json               Level configuration
        ├── items.level.json              Objects placed on the map
        ├── preview.png                   Thumbnail
        ├── WORLDFORGE.md                 Provenance + import notes
        ├── decalRoad.json                Detected roads (when AI is enabled)
        ├── art/
        │   ├── terrains/main_terrain/
        │   │   ├── main_terrain.ter      Binary terrain the engine loads
        │   │   ├── heightmap.png         16-bit heightmap, for manual import
        │   │   └── layers.json           Terrain material layers
        │   └── shapes/buildings/*.dae    Extruded building meshes
        └── vectors/*.json                Detected features (when AI is enabled)
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from core.geo import bbox_dimensions
from core.logging_config import get_logger
from core.paths import is_valid_map_name, safe_join
from models.terrain import TerrainData

logger = get_logger(__name__)

#: Fallback horizontal scale when the real bbox is unknown (metres per pixel).
DEFAULT_SQUARE_SIZE = 2.0


class BeamNGExporter:
    """Packages generated terrain into a BeamNG.drive mod archive."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_map_structure(
        self,
        map_name: str,
        heightmap_path: Path,
        preview_path: Path | None = None,
        *,
        terrain: TerrainData | None = None,
        bbox: list[float] | None = None,
        source_name: str = "unknown",
        vector_data: dict[str, list] | None = None,
        jbeam_roads: dict | None = None,
        decal_roads: dict | None = None,
        building_items: list | None = None,
        mesh_files: list | None = None,
    ) -> Path:
        """
        Build the mod directory tree and zip it.

        Args:
            map_name: Validated map slug; also the archive filename.
            heightmap_path: 16-bit heightmap PNG to embed.
            preview_path: Optional thumbnail. Previously this argument was
                accepted and then never used, so ``info.json`` pointed at a
                preview file that was not in the archive and the level showed
                a blank thumbnail in game.
            terrain: Terrain data, used to record the real elevation range.
            bbox: ``[min_lon, min_lat, max_lon, max_lat]``, used to derive the
                terrain's horizontal scale.
            source_name: Data source credited in the level metadata.
            vector_data: Detected roads/buildings, written as GeoJSON.
            jbeam_roads: Optional JBeam road network.
            decal_roads: Optional decal road definitions.
            building_items: Optional level items for buildings.
            mesh_files: Optional building mesh files to copy in.

        Returns:
            Path to the created ZIP archive.
        """
        if not is_valid_map_name(map_name):
            raise ValueError(f"Refusing to export unsafe map name: {map_name!r}")

        heightmap_path = Path(heightmap_path)
        if not heightmap_path.exists():
            raise FileNotFoundError(f"Heightmap not found: {heightmap_path}")

        logger.info("Packaging BeamNG mod for %r", map_name)

        square_size = self._square_size(bbox, heightmap_path)
        staging = safe_join(self.output_dir, ".staging", map_name)
        if staging.exists():
            shutil.rmtree(staging)

        try:
            level_dir = staging / "levels" / map_name
            terrain_dir = level_dir / "art" / "terrains" / "main_terrain"
            terrain_dir.mkdir(parents=True, exist_ok=True)

            shutil.copy2(heightmap_path, terrain_dir / "heightmap.png")

            # BeamNG loads terrain from a binary .ter, not from a PNG - the PNG
            # is only what the World Editor's import command reads. Writing both
            # means the level has a chance of loading as-is, while the PNG keeps
            # the manual import path open if the binary is rejected.
            self._write_terrain_file(terrain_dir / "main_terrain.ter", heightmap_path)

            if preview_path and Path(preview_path).exists():
                shutil.copy2(preview_path, level_dir / "preview.png")
            else:
                logger.warning("No preview image available for %s", map_name)

            self._write_json(level_dir / "info.json", self._info_json(map_name, source_name))
            self._write_json(
                level_dir / "main.level.json",
                self._main_level_json(map_name, square_size, terrain),
            )
            self._write_json(terrain_dir / "layers.json", self._terrain_layers())
            self._write_json(level_dir / "items.level.json", self._items_json(building_items))

            if decal_roads:
                self._write_json(level_dir / "decalRoad.json", decal_roads)
            if jbeam_roads:
                jbeam_dir = level_dir / "vehicles" / "road_network"
                jbeam_dir.mkdir(parents=True, exist_ok=True)
                self._write_json(jbeam_dir / "roads.jbeam", jbeam_roads)

            if vector_data:
                vectors_dir = level_dir / "vectors"
                vectors_dir.mkdir(parents=True, exist_ok=True)
                for feature_type, features in vector_data.items():
                    self._write_json(
                        vectors_dir / f"{feature_type}.json", {"features": features}
                    )

            if mesh_files:
                # art/shapes/, not art/terrains/*/shapes/: shapes live at the
                # level root in BeamNG, and the item entries reference them as
                # levels/<name>/art/shapes/buildings/<file>.
                shapes_dir = level_dir / "art" / "shapes" / "buildings"
                shapes_dir.mkdir(parents=True, exist_ok=True)
                copied = 0
                for mesh_file in mesh_files:
                    mesh_path = Path(mesh_file)
                    if mesh_path.exists():
                        shutil.copy2(mesh_path, shapes_dir / mesh_path.name)
                        copied += 1
                logger.info("Copied %d building mesh(es)", copied)

            (level_dir / "WORLDFORGE.md").write_text(
                self._readme(map_name, square_size, terrain, bbox, source_name),
                encoding="utf-8",
            )

            archive_path = safe_join(self.output_dir, f"{map_name}.zip")
            self._create_zip(staging, archive_path)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        logger.info(
            "Mod created: %s (%.2f MB)", archive_path, archive_path.stat().st_size / (1024 * 1024)
        )
        return archive_path

    @staticmethod
    def _write_terrain_file(destination: Path, heightmap_path: Path) -> None:
        """
        Convert the heightmap PNG into a binary ``.ter``.

        Non-fatal: if the conversion fails, the archive still ships the PNG and
        the WORLDFORGE notes explain how to import it by hand. Losing the whole
        export over an optional convenience would be the wrong trade.
        """
        try:
            import numpy as np
            from PIL import Image

            from .terrain_file import write_ter

            with Image.open(heightmap_path) as image:
                heights = np.array(image)

            write_ter(destination, heights.astype(np.uint16))
        except Exception as exc:  # noqa: BLE001 - optional artefact
            logger.warning("Could not write .ter terrain file (%s); PNG only", exc)

    # -- metadata -------------------------------------------------------------

    @staticmethod
    def _square_size(bbox: list[float] | None, heightmap_path: Path) -> float:
        """
        Metres represented by one heightmap pixel.

        This used to be hardcoded to 2.0, which means a 1 km box and a 20 km box
        produced terrain of identical in-game size - the generated world had no
        relationship to the region the user selected. Deriving it from the bbox
        and the heightmap resolution makes the exported terrain the right size.
        """
        if not bbox:
            return DEFAULT_SQUARE_SIZE

        try:
            from PIL import Image

            with Image.open(heightmap_path) as image:
                pixels = max(image.size)
        except Exception as exc:  # noqa: BLE001 - fall back rather than fail the export
            logger.warning("Could not read heightmap size (%s); using default scale", exc)
            return DEFAULT_SQUARE_SIZE

        if pixels <= 0:
            return DEFAULT_SQUARE_SIZE

        min_lon, min_lat, max_lon, max_lat = bbox
        dimensions = bbox_dimensions(min_lon, min_lat, max_lon, max_lat)
        return round(dimensions.max_side_meters / pixels, 4)

    @staticmethod
    def _info_json(map_name: str, source_name: str) -> dict:
        """Level metadata shown in the in-game level picker."""
        return {
            "title": map_name.replace("_", " ").title(),
            "description": f"Generated by BeamNG.WorldForge from {source_name} data",
            "authors": "BeamNG.WorldForge",
            "version": "1.0",
            "previews": ["preview.png"],
            "size": [1, 1],
            "difficulty": 0,
            "spawnPoints": [
                {"objectname": "spawn_default", "translation": [0, 0, 100], "rotationMatrix": [1, 0, 0, 0, 1, 0, 0, 0, 1]}
            ],
        }

    @staticmethod
    def _main_level_json(
        map_name: str, square_size: float, terrain: TerrainData | None
    ) -> dict:
        """
        Level configuration.

        ``heightScale`` carries the real elevation span. The heightmap PNG is
        normalised to the full 16-bit range, so without this value the terrain
        renders with an arbitrary vertical exaggeration.
        """
        min_height = terrain.min_elevation if terrain else 0.0
        height_scale = terrain.elevation_range if terrain else 100.0

        return {
            "name": map_name,
            "levelName": map_name,
            "description": "Generated terrain from real elevation data",
            "sun": {"azimuth": 0, "elevation": 45, "shadowDistance": 1600, "shadowSoftness": 0.15},
            "time": {"time": 0.5, "timeScale": 1.0, "play": False},
            "gravity": -9.81,
            "terrain": {
                # The engine reads the binary .ter; heightmap.png is kept
                # alongside it for a manual World Editor import.
                "terrainFile": "art/terrains/main_terrain/main_terrain.ter",
                "heightmapImage": "art/terrains/main_terrain/heightmap.png",
                "squareSize": square_size,
                "heightScale": round(max(height_scale, 1.0), 3),
                "minHeight": round(min_height, 3),
                "baseTexture": "grid512",
            },
            "weather": {"fogDensity": 0.0005, "fogDensityOffset": 0, "cloudCover": 0.4},
        }

    @staticmethod
    def _terrain_layers() -> dict:
        """Default terrain material set."""
        materials = [
            ("grass", "grass_green"),
            ("dirt", "dirt_brown"),
            ("rock", "rock_grey"),
        ]
        return {
            "version": 1,
            "materials": [
                {
                    "name": name,
                    "internalName": name,
                    "diffuseMap": f"art/terrains/{asset}_d.dds",
                    "normalMap": f"art/terrains/{asset}_n.dds",
                    "detailMap": f"art/terrains/{asset}_d.dds",
                    "detailSize": 4.0,
                }
                for name, asset in materials
            ],
            "layers": [
                {
                    "name": "base_layer",
                    "material": "grass",
                    "minHeight": -1000,
                    "maxHeight": 9000,
                    "minSlope": 0,
                    "maxSlope": 90,
                }
            ],
        }

    @staticmethod
    def _items_json(building_items: list | None) -> dict:
        """Level items (objects placed on the map)."""
        return {"version": 1, "items": building_items or []}

    @staticmethod
    def _readme(
        map_name: str,
        square_size: float,
        terrain: TerrainData | None,
        bbox: list[float] | None,
        source_name: str,
    ) -> str:
        """
        Provenance and import notes shipped inside the archive.

        BeamNG's level format is not fully documented and its terrain is
        normally authored in the in-game World Editor. Stating plainly what
        this archive contains - and that the heightmap may need importing
        through the editor - is more useful than implying it always drops in
        untouched.
        """
        lines = [
            f"# {map_name}",
            "",
            f"Generated by BeamNG.WorldForge on {datetime.now(UTC):%Y-%m-%d %H:%M UTC}.",
            "",
            "## Source data",
            f"- Provider: {source_name}",
        ]
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            dimensions = bbox_dimensions(min_lon, min_lat, max_lon, max_lat)
            lines += [
                f"- Bounding box: {min_lat:.5f},{min_lon:.5f} to {max_lat:.5f},{max_lon:.5f}",
                f"- Ground size: {dimensions.width_meters / 1000:.2f} x "
                f"{dimensions.height_meters / 1000:.2f} km ({dimensions.area_km2:.2f} km2)",
            ]
        if terrain:
            lines += [
                f"- Elevation range: {terrain.min_elevation:.1f} m to {terrain.max_elevation:.1f} m",
                f"- Missing samples in source DEM: {terrain.nodata_fraction * 100:.2f}%",
            ]

        lines += [
            f"- Terrain scale: {square_size} m per heightmap pixel",
            "",
            "## Installing",
            "1. Copy this ZIP into `Documents/BeamNG.drive/<version>/mods/`.",
            "2. Start the game; the level appears under Freeroam.",
            "",
            "## Terrain files",
            "This level ships the terrain twice:",
            "",
            "- `art/terrains/main_terrain/main_terrain.ter` - the binary format the",
            "  engine loads. Written to the community-documented `.ter` layout; it has",
            "  not been verified by loading this level in the game.",
            "- `art/terrains/main_terrain/heightmap.png` - a 16-bit grayscale heightmap.",
            "  Value 0 maps to `terrain.minHeight` and 65535 to `minHeight + heightScale`",
            "  (both in `main.level.json`).",
            "",
            "If the level loads with no terrain, import the PNG through the in-game",
            "World Editor (Terrain > Import Heightmap) using the scale values above.",
            "That path always works.",
        ]
        return "\n".join(lines) + "\n"

    # -- io -------------------------------------------------------------------

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _create_zip(source_dir: Path, output_zip: Path) -> None:
        """Zip ``source_dir`` with deterministic ordering."""
        output_zip.parent.mkdir(parents=True, exist_ok=True)

        # Sorted so repeated runs over identical input produce byte-comparable
        # archives, which makes "did anything actually change?" answerable.
        files = sorted(p for p in source_dir.rglob("*") if p.is_file())

        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for file_path in files:
                archive.write(file_path, file_path.relative_to(source_dir).as_posix())
