"""
GCS Bellwether Downloader & Dynamic Spatial Cropper.
Downloads or crops Google X Project Bellwether 100m Cloud-Optimized GeoTIFFs (COGs)
for any lat/lng bounding box (San Bruno, San Jose, Santa Cruz, etc.).
"""

import os
from pathlib import Path
from typing import Dict, Tuple, Optional
import numpy as np

try:
    import rasterio
    from rasterio.windows import from_bounds
    from PIL import Image
    HAS_GIS = True
except ImportError:
    HAS_GIS = False

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REF_DATA_DIR = BASE_DIR / "SBFire_SJSU-20260730T030001Z-1-001" / "SBFire_SJSU" / "ref_data"
STATIC_DIR = BASE_DIR / "backend" / "static"


def crop_bellwether_by_bbox(
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    is_5_year: bool = False,
    output_filename: Optional[str] = None
) -> Dict:
    """
    Dynamically crop Bellwether probability rasters for any city or region bbox.
    """
    if not HAS_GIS:
        raise RuntimeError("rasterio and PIL packages are required for GIS processing.")

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    tif_name = "prediction_for_20260401_to_30310401.tif" if is_5_year else "prediction_for_20260401_to_20270401.tif"
    if not (REF_DATA_DIR / tif_name).exists():
        for file in REF_DATA_DIR.glob("prediction_for_2026*.tif"):
            if ("2031" in file.name and is_5_year) or ("2027" in file.name and not is_5_year):
                tif_name = file.name
                break

    tif_path = REF_DATA_DIR / tif_name

    with rasterio.open(tif_path) as src:
        # Clamp bounds to src.bounds
        c_min_lng = max(min_lng, src.bounds.left)
        c_max_lng = min(max_lng, src.bounds.right)
        c_min_lat = max(min_lat, src.bounds.bottom)
        c_max_lat = min(max_lat, src.bounds.top)

        if c_min_lng >= c_max_lng or c_min_lat >= c_max_lat:
            # Fallback to entire raster if bbox outside bounds
            data = src.read(1)
            c_min_lat, c_min_lng = src.bounds.bottom, src.bounds.left
            c_max_lat, c_max_lng = src.bounds.top, src.bounds.right
        else:
            try:
                window = from_bounds(c_min_lng, c_min_lat, c_max_lng, c_max_lat, transform=src.transform)
                data = src.read(1, window=window)
            except Exception:
                data = src.read(1)

    h, w = data.shape
    if h == 0 or w == 0:
        h, w = 200, 200
        data = np.zeros((h, w), dtype=np.float32)

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    valid_mask = ~np.isnan(data) & (data >= 0)

    colors = [
        [34, 139, 34, 130],    # Very Low
        [144, 238, 144, 150],  # Low
        [255, 255, 102, 170],  # Moderate
        [255, 204, 0, 190],    # Significant
        [255, 128, 0, 210],    # High
        [238, 34, 34, 230],    # Very High
        [148, 0, 211, 240],    # Extreme
    ]

    cutoffs = [0.00004, 0.00020, 0.00100, 0.00400, 0.00667, 0.01333] if not is_5_year else [0.00020, 0.00100, 0.00500, 0.02000, 0.03333, 0.06667]

    cat_indices = np.zeros((h, w), dtype=int)
    for idx, cutoff in enumerate(cutoffs):
        cat_indices[data >= cutoff] = idx + 1

    for cat_idx, color in enumerate(colors):
        mask = valid_mask & (cat_indices == cat_idx)
        rgba[mask] = color

    if not output_filename:
        output_filename = f"bellwether_crop_{'5yr' if is_5_year else '1yr'}_{abs(hash((min_lat, min_lng))) % 10000}.png"

    out_path = STATIC_DIR / output_filename
    img = Image.fromarray(rgba, mode="RGBA")
    img.save(out_path)

    cat_names = ["Very Low", "Low", "Moderate", "Significant", "High", "Very High", "Extreme"]
    total_valid = int(np.sum(valid_mask))
    stats = {}
    for c_idx, name in enumerate(cat_names):
        cnt = int(np.sum(valid_mask & (cat_indices == c_idx)))
        stats[name] = {
            "count": cnt,
            "percentage": round((cnt / total_valid) * 100, 2) if total_valid > 0 else 0.0
        }

    return {
        "image_url": f"/static/{output_filename}",
        "bounds": [[c_min_lat, c_min_lng], [c_max_lat, c_max_lng]],
        "width": w,
        "height": h,
        "stats": stats,
        "max_probability": float(np.nanmax(data)) if total_valid > 0 else 0.0,
        "mean_probability": float(np.nanmean(data)) if total_valid > 0 else 0.0,
    }
