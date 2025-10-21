"""Terrain data processing and heightmap generation"""

import numpy as np
from PIL import Image
from scipy import ndimage
from pathlib import Path
from typing import Tuple, Optional

from models.terrain import TerrainData, HeightmapConfig


class TerrainProcessor:
    """Process terrain elevation data and generate heightmaps"""
    
    def __init__(self):
        self.terrain_data: Optional[TerrainData] = None
    
    def process_dem(self, elevation_data: np.ndarray) -> TerrainData:
        """
        Process raw DEM data into TerrainData model
        
        Args:
            elevation_data: Raw elevation array from GEE
        
        Returns:
            TerrainData object
        """
        print(f"🏔️  Processing DEM data: {elevation_data.shape}")
        
        # Handle NaN and invalid values
        elevation_clean = np.nan_to_num(elevation_data, nan=0.0)
        
        # Create TerrainData object
        self.terrain_data = TerrainData.from_numpy(elevation_clean)
        
        print(f"   Elevation range: [{self.terrain_data.min_elevation:.1f}, "
              f"{self.terrain_data.max_elevation:.1f}]m")
        
        return self.terrain_data
    
    def generate_heightmap(
        self,
        terrain_data: TerrainData,
        config: HeightmapConfig
    ) -> np.ndarray:
        """
        Generate a heightmap image from terrain data
        
        Args:
            terrain_data: Processed terrain elevation data
            config: Heightmap generation configuration
        
        Returns:
            Heightmap as numpy array
        """
        print(f"🗺️  Generating heightmap: {config.size}x{config.size}, {config.bit_depth}-bit")
        
        # Get elevation array
        elevation = terrain_data.to_numpy()
        
        # Resize to target size using interpolation
        heightmap = self._resize_elevation(
            elevation,
            (config.size, config.size),
            method=config.interpolation
        )
        
        # Normalize to target bit depth range
        if config.bit_depth == 16:
            heightmap_normalized = self._normalize_to_16bit(
                heightmap,
                vertical_scale=config.vertical_scale
            )
        else:  # 8-bit
            heightmap_normalized = self._normalize_to_8bit(
                heightmap,
                vertical_scale=config.vertical_scale
            )
        
        print(f"✅ Heightmap generated: {heightmap_normalized.shape}, "
              f"dtype: {heightmap_normalized.dtype}")
        
        return heightmap_normalized
    
    def save_heightmap(
        self,
        heightmap: np.ndarray,
        output_path: Path,
        bit_depth: int = 16
    ):
        """
        Save heightmap as PNG image
        
        Args:
            heightmap: Heightmap array
            output_path: Output file path
            bit_depth: 8 or 16
        """
        print(f"💾 Saving heightmap to {output_path}")
        
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to PIL Image
        if bit_depth == 16:
            # Save as 16-bit grayscale PNG
            img = Image.fromarray(heightmap.astype(np.uint16), mode='I;16')
        else:
            # Save as 8-bit grayscale PNG
            img = Image.fromarray(heightmap.astype(np.uint8), mode='L')
        
        img.save(output_path)
        print(f"✅ Heightmap saved: {output_path}")
    
    def _resize_elevation(
        self,
        elevation: np.ndarray,
        target_size: Tuple[int, int],
        method: str = "bilinear"
    ) -> np.ndarray:
        """
        Resize elevation array to target size
        
        Args:
            elevation: Original elevation array
            target_size: (height, width)
            method: Interpolation method
        
        Returns:
            Resized elevation array
        """
        original_shape = elevation.shape
        zoom_factors = (
            target_size[0] / original_shape[0],
            target_size[1] / original_shape[1]
        )
        
        # Map interpolation method
        order_map = {
            'nearest': 0,
            'bilinear': 1,
            'bicubic': 3
        }
        order = order_map.get(method, 1)
        
        # Resize using scipy
        resized = ndimage.zoom(elevation, zoom_factors, order=order)
        
        return resized
    
    def _normalize_to_16bit(
        self,
        elevation: np.ndarray,
        vertical_scale: float = 1.0
    ) -> np.ndarray:
        """
        Normalize elevation data to 16-bit range (0-65535)
        
        BeamNG.drive heightmap format:
        - 16-bit grayscale PNG
        - 0 = minimum elevation
        - 65535 = maximum elevation
        """
        # Apply vertical scale
        scaled = elevation * vertical_scale
        
        # Get min/max
        min_elev = np.min(scaled)
        max_elev = np.max(scaled)
        
        # Avoid division by zero
        if max_elev - min_elev < 0.001:
            return np.zeros_like(scaled, dtype=np.uint16)
        
        # Normalize to 0-65535
        normalized = ((scaled - min_elev) / (max_elev - min_elev)) * 65535
        
        return normalized.astype(np.uint16)
    
    def _normalize_to_8bit(
        self,
        elevation: np.ndarray,
        vertical_scale: float = 1.0
    ) -> np.ndarray:
        """
        Normalize elevation data to 8-bit range (0-255)
        """
        # Apply vertical scale
        scaled = elevation * vertical_scale
        
        # Get min/max
        min_elev = np.min(scaled)
        max_elev = np.max(scaled)
        
        # Avoid division by zero
        if max_elev - min_elev < 0.001:
            return np.zeros_like(scaled, dtype=np.uint8)
        
        # Normalize to 0-255
        normalized = ((scaled - min_elev) / (max_elev - min_elev)) * 255
        
        return normalized.astype(np.uint8)
    
    def generate_preview(
        self,
        heightmap: np.ndarray,
        output_path: Path,
        colormap: str = 'terrain'
    ):
        """
        Generate a colored preview of the heightmap
        
        Args:
            heightmap: Heightmap array
            output_path: Output file path for preview
            colormap: Color scheme (terrain, viridis, etc.)
        """
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        
        print(f"🎨 Generating heightmap preview...")
        
        # Normalize to 0-1 for visualization
        normalized = heightmap.astype(float) / np.max(heightmap)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 10), dpi=100)
        ax.imshow(normalized, cmap=colormap)
        ax.axis('off')
        ax.set_title('Heightmap Preview')
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
        plt.close()
        
        print(f"✅ Preview saved: {output_path}")

