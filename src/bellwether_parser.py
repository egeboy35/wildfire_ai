"""
Bellwether GeoTIFF & Risk Factor Parser
Provides tools to parse Google X Bellwether 1-year and 5-year wildfire probability models,
classify risk score categories, and decode feature importance weights.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Union
import numpy as np

try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False


class BellwetherParser:
    """Parser for Bellwether Wildfire Landscape Hazard Models (GeoTIFFs)."""

    # Risk score category thresholds based on Google X Bellwether Release Specs
    CATEGORIES_1_YEAR = [
        ("Very Low", 0.0, 0.00004),
        ("Low", 0.00004, 0.00020),
        ("Moderate", 0.00020, 0.00100),
        ("Significant", 0.00100, 0.00400),
        ("High", 0.00400, 0.00667),
        ("Very High", 0.00667, 0.01333),
        ("Extreme", 0.01333, 1.00000),
    ]

    CATEGORIES_5_YEAR = [
        ("Very Low", 0.0, 0.00020),
        ("Low", 0.00020, 0.00100),
        ("Moderate", 0.00100, 0.00500),
        ("Significant", 0.00500, 0.02000),
        ("High", 0.02000, 0.03333),
        ("Very High", 0.03333, 0.06667),
        ("Extreme", 0.06667, 1.00000),
    ]

    def __init__(self, ref_data_dir: Union[str, Path]):
        self.ref_data_dir = Path(ref_data_dir)

    def load_feature_mapping(self, is_5_year: bool = False) -> Dict[str, str]:
        """Load JSON mapping between feature ID and feature description string."""
        filename = "feature_mapping_5_year.json" if is_5_year else "feature_mapping_1_year.json"
        json_path = self.ref_data_dir / filename
        if not json_path.exists():
            raise FileNotFoundError(f"Feature mapping file not found: {json_path}")
        
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_prediction(self, tif_name: str) -> Tuple[np.ndarray, dict]:
        """
        Load prediction GeoTIFF raster.
        Returns:
            data: np.ndarray (H, W) containing probability values (0.0 to 1.0)
            meta: raster metadata dict (CRS, bounds, transform, etc.)
        """
        if not HAS_RASTERIO:
            raise RuntimeError("rasterio package is required to read GeoTIFF files.")
        
        tif_path = self.ref_data_dir / tif_name
        if not tif_path.exists():
            raise FileNotFoundError(f"Prediction TIF file not found: {tif_path}")

        with rasterio.open(tif_path) as src:
            data = src.read(1)  # Band 1 contains probability
            meta = {
                "driver": src.driver,
                "height": src.height,
                "width": src.width,
                "crs": src.crs,
                "transform": src.transform,
                "bounds": src.bounds,
                "nodata": src.nodata,
            }
        return data, meta

    def classify_risk(self, prob_data: np.ndarray, is_5_year: bool = False) -> np.ndarray:
        """
        Classify continuous probability array into 7 risk level integers (0=Very Low to 6=Extreme).
        NoData (NaN) remains NaN.
        """
        categories = self.CATEGORIES_5_YEAR if is_5_year else self.CATEGORIES_1_YEAR
        classified = np.full(prob_data.shape, np.nan, dtype=np.float32)
        valid_mask = ~np.isnan(prob_data)

        for idx, (name, low, high) in enumerate(categories):
            mask = valid_mask & (prob_data >= low) & (prob_data < high)
            if idx == len(categories) - 1:  # Include upper boundary for Extreme
                mask = valid_mask & (prob_data >= low)
            classified[mask] = idx

        return classified

    def load_risk_factors(
        self, cog_name: str, mapping_name: str, top_k: int = 10
    ) -> Dict[str, float]:
        """
        Parse top-10 risk factor COG GeoTIFF and return overall aggregated feature importance.
        Bands 1..10 store Feature IDs, Bands 11..20 store Feature Weight Percentages.
        """
        if not HAS_RASTERIO:
            raise RuntimeError("rasterio package is required.")

        cog_path = self.ref_data_dir / cog_name
        json_path = self.ref_data_dir / mapping_name
        
        with open(json_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        with rasterio.open(cog_path) as src:
            num_bands = src.count
            if num_bands < 20:
                raise ValueError(f"Expected at least 20 bands in risk factor COG, got {num_bands}")
            
            # Read all bands (20, H, W)
            bands = src.read()

        feature_ids = bands[0:10]    # Shape (10, H, W)
        weights = bands[10:20]       # Shape (10, H, W)

        # Mask invalid nodata values (-9999)
        valid_mask = (feature_ids != -9999) & (weights != -9999) & (~np.isnan(weights))

        feature_sums: Dict[str, float] = {}
        
        # Aggregate weights for each feature across all pixels
        for k in range(min(top_k, 10)):
            f_ids = feature_ids[k][valid_mask[k]]
            w_vals = weights[k][valid_mask[k]]
            
            for fid, w in zip(f_ids, w_vals):
                fid_str = str(int(fid))
                feat_name = mapping.get(fid_str, f"Unknown Feature ({fid_str})")
                feature_sums[feat_name] = feature_sums.get(feat_name, 0.0) + float(w)

        # Normalize to relative percentages
        total = sum(feature_sums.values())
        if total > 0:
            feature_importance = {
                k: round((v / total) * 100, 2)
                for k, v in sorted(feature_sums.items(), key=lambda item: item[1], reverse=True)
            }
        else:
            feature_importance = {}

        return feature_importance


if __name__ == "__main__":
    # Self-test if ref_data is available
    sample_dir = Path(__file__).resolve().parent.parent / "SBFire_SJSU-20260730T030001Z-1-001" / "SBFire_SJSU" / "ref_data"
    if sample_dir.exists() and HAS_RASTERIO:
        parser = BellwetherParser(sample_dir)
        prob_1yr, meta = parser.load_prediction("prediction_for_20260401_to_20270401.tif")
        print(f"1-Year Prediction shape: {prob_1yr.shape}, CRS: {meta['crs']}")
        print(f"Max 1-Year Probability: {np.nanmax(prob_1yr):.5f}")
        
        factors = parser.load_risk_factors("risk_factors_1_year_cog.tif", "feature_mapping_1_year.json")
        print("\nTop 5 Aggregated Risk Factors for 1-Year Model:")
        for name, pct in list(factors.items())[:5]:
            print(f"  - {name}: {pct}%")
