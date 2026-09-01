"""
Sentinel-2 Satellite Imagery Fetcher & Index Calculator
Uses SpatioTemporal Asset Catalog (STAC) via Microsoft Planetary Computer
to search and stream cloud-free Sentinel-2 L2A imagery for wildland-urban interface (WUI) analysis.
Calculates NDVI, NDWI, and NBR indices for fuel moisture & vegetation greenness.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    import pystac_client
    import planetary_computer
    import rioxarray
    HAS_STAC = True
except ImportError:
    HAS_STAC = False


class SentinelFetcher:
    """Fetcher for Sentinel-2 satellite data and vegetation index computer."""

    STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

    # Default Bounding Box for San Bruno / Watershed Wildland-Urban Interface (WUI)
    # [min_longitude, min_latitude, max_longitude, max_latitude]
    SAN_BRUNO_BBOX = [-122.465, 37.600, -122.400, 37.645]

    def __init__(self, bbox: Optional[List[float]] = None):
        self.bbox = bbox or self.SAN_BRUNO_BBOX

    def search_scenes(
        self,
        date_range: str = "2026-05-01/2026-07-29",
        max_cloud_cover: float = 15.0,
        limit: int = 5,
    ) -> List[dict]:
        """
        Search for cloud-free Sentinel-2 L2A scenes over the bounding box.
        
        Args:
            date_range: ISO 8601 date range string, e.g., '2026-05-01/2026-07-29'
            max_cloud_cover: Max allowed cloud cover percentage
            limit: Maximum scenes to return
        
        Returns:
            List of scene summary dicts containing ID, datetime, cloud cover, assets
        """
        if not HAS_STAC:
            raise RuntimeError(
                "pystac_client, planetary_computer, and rioxarray packages are required for Sentinel-2 STAC querying."
            )

        catalog = pystac_client.Client.open(
            self.STAC_URL,
            modifier=planetary_computer.sign_inplace,
        )

        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=self.bbox,
            datetime=date_range,
            query={"eo:cloud_cover": {"lt": max_cloud_cover}},
            max_items=limit,
        )

        items = list(search.items())
        scenes = []

        for item in items:
            scenes.append({
                "id": item.id,
                "datetime": item.datetime.isoformat(),
                "cloud_cover": item.properties.get("eo:cloud_cover", 0.0),
                "item_obj": item,
            })

        return scenes

    @staticmethod
    def calculate_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Calculate Normalized Difference Vegetation Index (NDVI).
        NDVI = (NIR - Red) / (NIR + Red)
        """
        denom = nir + red
        denom[denom == 0] = np.nan
        ndvi = (nir - red) / denom
        return np.clip(ndvi, -1.0, 1.0)

    @staticmethod
    def calculate_ndwi(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
        """
        Calculate Normalized Difference Water / Moisture Index (NDWI/NDMI).
        NDWI = (NIR - SWIR) / (NIR + SWIR)
        """
        denom = nir + swir
        denom[denom == 0] = np.nan
        ndwi = (nir - swir) / denom
        return np.clip(ndwi, -1.0, 1.0)

    @staticmethod
    def calculate_nbr(nir: np.ndarray, swir2: np.ndarray) -> np.ndarray:
        """
        Calculate Normalized Burn Ratio (NBR).
        NBR = (NIR - SWIR2) / (NIR + SWIR2)
        """
        denom = nir + swir2
        denom[denom == 0] = np.nan
        nbr = (nir - swir2) / denom
        return np.clip(nbr, -1.0, 1.0)

    def fetch_scene_indices(
        self, item_obj
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
        """
        Stream Band 4 (Red), Band 8 (NIR), Band 11 (SWIR1) and Band 12 (SWIR2)
        for the target scene and compute NDVI, NDWI, and NBR.

        NDWI uses SWIR1 (B11); NBR is defined on SWIR2 (B12). Passing B11 to
        both makes the two indices the same array.
        
        Returns:
            (ndvi, ndwi, nbr, metadata)
        """
        if not HAS_STAC:
            raise RuntimeError("rioxarray & pystac_client required.")

        # Read bands using COG streaming
        b4_asset = item_obj.assets["B04"].href
        b8_asset = item_obj.assets["B08"].href
        b11_asset = item_obj.assets["B11"].href
        b12_asset = item_obj.assets["B12"].href

        da_b4 = rioxarray.open_rasterio(b4_asset, masked=True)
        da_b8 = rioxarray.open_rasterio(b8_asset, masked=True)
        da_b11 = rioxarray.open_rasterio(b11_asset, masked=True)
        da_b12 = rioxarray.open_rasterio(b12_asset, masked=True)

        # Clip to bounding box
        da_b4_clipped = da_b4.rio.clip_box(*self.bbox)
        da_b8_clipped = da_b8.rio.clip_box(*self.bbox)
        da_b11_clipped = da_b11.rio.clip_box(*self.bbox)
        da_b12_clipped = da_b12.rio.clip_box(*self.bbox)

        red = da_b4_clipped.values[0].astype(np.float32)
        nir = da_b8_clipped.values[0].astype(np.float32)
        swir1 = da_b11_clipped.values[0].astype(np.float32)
        swir2 = da_b12_clipped.values[0].astype(np.float32)

        ndvi = self.calculate_ndvi(red, nir)
        ndwi = self.calculate_ndwi(nir, swir1)
        nbr = self.calculate_nbr(nir, swir2)

        metadata = {
            "scene_id": item_obj.id,
            "datetime": item_obj.datetime.isoformat(),
            "crs": str(da_b4_clipped.rio.crs),
            "transform": da_b4_clipped.rio.transform(),
        }

        return ndvi, ndwi, nbr, metadata


if __name__ == "__main__":
    fetcher = SentinelFetcher()
    print(f"San Bruno WUI Bounding Box: {fetcher.SAN_BRUNO_BBOX}")
    if HAS_STAC:
        try:
            results = fetcher.search_scenes(limit=2)
            print(f"Found {len(results)} cloud-free scenes.")
            for r in results:
                print(f"  Scene: {r['id']}, Date: {r['datetime']}, Cloud: {r['cloud_cover']:.1f}%")
        except Exception as e:
            print(f"STAC Search error: {e}")
    else:
        print("pystac_client or planetary_computer not installed.")
