"""Terrain data processing and heightmap generation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from core.logging_config import get_logger
from models.terrain import HeightmapConfig, TerrainData

logger = get_logger(__name__)

#: scipy.ndimage.zoom spline order for each interpolation mode.
_INTERPOLATION_ORDER = {"nearest": 0, "bilinear": 1, "bicubic": 3}

#: Elevation values below this are treated as sentinel nodata markers. DEM
#: products commonly encode "no measurement" as -32768 (SRTM), -9999 (ASTER)
#: or -32767. Real terrain never goes below the Dead Sea shore (-430 m), so a
#: -1000 m threshold separates the two without false positives.
_NODATA_SENTINEL_THRESHOLD = -1000.0

#: Elevations above this cannot be real (Everest is 8849 m).
_MAX_PLAUSIBLE_ELEVATION = 9000.0


class TerrainProcessingError(RuntimeError):
    """Raised when a DEM cannot be turned into a usable heightmap."""


class TerrainProcessor:
    """Process terrain elevation data and generate BeamNG-compatible heightmaps."""

    def process_dem(self, elevation_data: np.ndarray) -> TerrainData:
        """
        Clean raw DEM data into a :class:`TerrainData`.

        Nodata handling is the important part. The previous implementation did
        ``np.nan_to_num(data, nan=0.0)``, which replaces every missing sample
        with sea level. On a mountain tile with a few voided pixels that
        produces vertical cliffs kilometres deep, and because the heightmap is
        normalised against min/max, a single voided pixel compressed the entire
        real elevation range into a sliver of the available bit depth.

        Here, nodata is detected (NaN, infinities, and the usual sentinel
        values), then filled from the nearest valid neighbour so the surface
        stays continuous.

        Args:
            elevation_data: Raw elevation array from a data source.

        Returns:
            Cleaned :class:`TerrainData`.

        Raises:
            TerrainProcessingError: If the array is empty or entirely nodata.
        """
        elevation = np.asarray(elevation_data, dtype=np.float32)

        if elevation.ndim != 2:
            raise TerrainProcessingError(
                f"Expected a 2D elevation array, got shape {elevation.shape}"
            )
        if elevation.size == 0:
            raise TerrainProcessingError("DEM contains no data (empty array)")

        logger.info("Processing DEM: %sx%s", elevation.shape[1], elevation.shape[0])

        invalid = (
            ~np.isfinite(elevation)
            | (elevation <= _NODATA_SENTINEL_THRESHOLD)
            | (elevation >= _MAX_PLAUSIBLE_ELEVATION)
        )
        nodata_fraction = float(invalid.mean())

        if invalid.all():
            raise TerrainProcessingError(
                "DEM contains no valid elevation samples. The selected region may be "
                "outside the dataset's coverage - try a different area or data source."
            )

        if nodata_fraction > 0:
            logger.warning(
                "DEM has %.2f%% missing samples; filling from nearest valid neighbours",
                nodata_fraction * 100,
            )
            elevation = self._fill_nodata(elevation, invalid)

        terrain = TerrainData.from_numpy(elevation, nodata_fraction=nodata_fraction)
        logger.info(
            "Elevation range: %.1fm to %.1fm (span %.1fm)",
            terrain.min_elevation,
            terrain.max_elevation,
            terrain.elevation_range,
        )
        return terrain

    @staticmethod
    def _fill_nodata(elevation: np.ndarray, invalid: np.ndarray) -> np.ndarray:
        """
        Replace invalid samples with the value of the nearest valid sample.

        Uses a distance transform to find, for every invalid pixel, the index of
        the closest valid one - a single O(n) pass rather than an iterative
        blur, and it never invents elevations outside the observed range.
        """
        filled = elevation.copy()
        # ``return_indices`` gives the coordinates of the nearest zero (i.e.
        # nearest *valid*) cell for every position in the input.
        _, nearest_index = ndimage.distance_transform_edt(
            invalid, return_distances=True, return_indices=True
        )
        filled[invalid] = elevation[tuple(idx[invalid] for idx in nearest_index)]
        return filled

    def generate_heightmap(
        self,
        terrain_data: TerrainData,
        config: HeightmapConfig,
    ) -> np.ndarray:
        """
        Generate a normalised heightmap array from terrain data.

        Args:
            terrain_data: Cleaned terrain elevation data.
            config: Heightmap generation configuration.

        Returns:
            Heightmap as a ``uint16`` (or ``uint8``) array of shape
            ``(config.size, config.size)``.
        """
        logger.info(
            "Generating %dx%d %d-bit heightmap (%s interpolation)",
            config.size,
            config.size,
            config.bit_depth,
            config.interpolation,
        )

        elevation = terrain_data.to_numpy()
        resized = self._resize_elevation(elevation, config.size, config.interpolation)
        return self._normalize(resized, config.bit_depth, config.vertical_scale)

    def save_heightmap(self, heightmap: np.ndarray, output_path: Path, bit_depth: int = 16) -> Path:
        """
        Save a heightmap as a grayscale PNG.

        Args:
            heightmap: Heightmap array.
            output_path: Destination file.
            bit_depth: 8 or 16.

        Returns:
            The path written to.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if bit_depth == 16:
            # Pillow infers I;16 from a uint16 array. Passing mode= explicitly
            # is deprecated (removed in Pillow 13) and emits a warning.
            image = Image.fromarray(heightmap.astype(np.uint16))
        elif bit_depth == 8:
            image = Image.fromarray(heightmap.astype(np.uint8))
        else:
            raise ValueError(f"bit_depth must be 8 or 16, got {bit_depth}")

        image.save(output_path, format="PNG", optimize=False)
        logger.info("Heightmap saved: %s", output_path)
        return output_path

    def generate_preview(
        self,
        heightmap: np.ndarray,
        output_path: Path,
        colormap: str = "terrain",
    ) -> Path:
        """
        Render a colourised preview of the heightmap.

        Args:
            heightmap: Heightmap array.
            output_path: Destination PNG.
            colormap: Matplotlib colormap name.

        Returns:
            The path written to.
        """
        import matplotlib

        matplotlib.use("Agg")  # Non-interactive backend; required on headless servers.
        import matplotlib.pyplot as plt

        # Normalise defensively: a perfectly flat region yields an all-zero
        # heightmap, and the previous ``/ np.max(heightmap)`` produced a
        # division by zero and an all-NaN image.
        values = heightmap.astype(np.float64)
        peak = float(values.max())
        normalised = values / peak if peak > 0 else np.zeros_like(values)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        figure, axes = plt.subplots(figsize=(10, 10), dpi=100)
        try:
            axes.imshow(normalised, cmap=colormap, vmin=0.0, vmax=1.0)
            axes.axis("off")
            figure.savefig(output_path, bbox_inches="tight", pad_inches=0)
        finally:
            plt.close(figure)

        logger.info("Preview saved: %s", output_path)
        return output_path

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _resize_elevation(elevation: np.ndarray, size: int, method: str) -> np.ndarray:
        """Resample an elevation grid to ``size`` x ``size``."""
        order = _INTERPOLATION_ORDER.get(method, 1)
        zoom_factors = (size / elevation.shape[0], size / elevation.shape[1])

        resized = ndimage.zoom(elevation, zoom_factors, order=order)

        # ndimage.zoom rounds the output shape, so a non-integer zoom factor can
        # land one pixel short or long. BeamNG requires the exact square size,
        # so pad or crop to guarantee it.
        if resized.shape != (size, size):
            corrected = np.empty((size, size), dtype=resized.dtype)
            rows = min(size, resized.shape[0])
            cols = min(size, resized.shape[1])
            corrected[:rows, :cols] = resized[:rows, :cols]
            if rows < size:
                corrected[rows:, :cols] = corrected[rows - 1, :cols]
            if cols < size:
                corrected[:, cols:] = corrected[:, cols - 1 : cols]
            resized = corrected

        return resized

    @staticmethod
    def _normalize(elevation: np.ndarray, bit_depth: int, vertical_scale: float) -> np.ndarray:
        """
        Normalise elevations into the full range of the target bit depth.

        BeamNG reads the heightmap as an unsigned integer image where 0 is the
        terrain's minimum height and the maximum value is its peak, so the real
        elevation span is carried by ``main.level.json``, not the image.
        """
        max_value, dtype = (65535, np.uint16) if bit_depth == 16 else (255, np.uint8)

        scaled = elevation.astype(np.float64) * vertical_scale
        minimum = float(scaled.min())
        maximum = float(scaled.max())
        span = maximum - minimum

        if span < 1e-6:
            # Perfectly flat terrain (a lake, or a region with a single value).
            return np.zeros(scaled.shape, dtype=dtype)

        normalised = (scaled - minimum) / span * max_value
        return np.clip(np.rint(normalised), 0, max_value).astype(dtype)
