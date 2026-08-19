"""
Google Earth Engine (GEE) Python API Demo for San Bruno Wildfire Sentinel-2 Analysis
Uses GCP Project 'CMPElkk' to query Sentinel-2 L2A Harmonized dataset,
computes cloud-free composite and calculates NDVI/NDWI over San Bruno WUI area.
"""

import os
import sys
from pathlib import Path

try:
    import ee
    HAS_EE = True
except ImportError:
    HAS_EE = False


# Google Cloud Project ID from your GCP Console screenshot
GCP_PROJECT_ID = "CMPElkk"

# San Bruno Bounding Box: [min_lon, min_lat, max_lon, max_lat]
SAN_BRUNO_BBOX = [-122.465, 37.600, -122.400, 37.645]


def init_earth_engine(project_id: str = GCP_PROJECT_ID) -> bool:
    """Initialize Google Earth Engine API with specified GCP Project ID."""
    if not HAS_EE:
        print("❌ 'earthengine-api' package is not installed. Please run: pip install earthengine-api geemap")
        return False

    cred_file = os.path.expanduser("~/.config/earthengine/credentials")
    adc_file = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")

    # Check if either GEE credentials or gcloud ADC credentials exist
    if not os.path.exists(cred_file) and not os.path.exists(adc_file):
        print(f"⚠️ GEE Credentials not found.")
        print("🔑 Authentication is required for Google Earth Engine.")
        print("   Please run one of the following commands in your terminal to complete login:\n")
        print("   👉 [Recommended] Authenticate via gcloud (Google-verified, avoids 'App blocked' warning):")
        print("      earthengine authenticate --auth_mode=gcloud\n")
        print("   👉 [Alternative] Authenticate without Google Drive scope:")
        print("      earthengine authenticate --auth_mode=notebook\n")
        return False

    try:
        ee.Initialize(project=project_id)
        print(f"✅ Successfully initialized Google Earth Engine with Project: '{project_id}'")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Earth Engine: {e}")
        return False


def run_gee_sentinel2_demo():
    print("=" * 70)
    print("🌍 GOOGLE EARTH ENGINE (GEE) SENTINEL-2 DEMO - SAN BRUNO WUI")
    print("=" * 70)

    if not init_earth_engine(GCP_PROJECT_ID):
        return

    # Define Geometry Bounding Box
    min_lon, min_lat, max_lon, max_lat = SAN_BRUNO_BBOX
    san_bruno_roi = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)

    print(f"\n[1] Querying Sentinel-2 L2A Harmonized Collection for San Bruno ROI...")
    print(f"    • BBox: {SAN_BRUNO_BBOX}")

    # Query Sentinel-2 Surface Reflectance Collection
    s2_collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(san_bruno_roi)
        .filterDate("2026-05-01", "2026-07-29")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 15))
    )

    scene_count = s2_collection.size().getInfo()
    print(f"    • Found {scene_count} cloud-free Sentinel-2 scenes in date range.")

    if scene_count == 0:
        print("    ⚠️ No scenes found for the exact date range, expanding filter date...")
        s2_collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(san_bruno_roi)
            .filterDate("2025-06-01", "2026-07-29")
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        )
        scene_count = s2_collection.size().getInfo()
        print(f"    • Expanded Search Found: {scene_count} scenes.")

    # Create Median Cloud-Free Composite
    composite = s2_collection.median().clip(san_bruno_roi)

    # Calculate NDVI: (B8 - B4) / (B8 + B4)
    ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")

    # Calculate NDWI (Moisture Index): (B8 - B11) / (B8 + B11)
    ndwi = composite.normalizedDifference(["B8", "B11"]).rename("NDWI")

    # Reduce Region to get mean NDVI and NDWI over San Bruno WUI
    stats = ndvi.addBands(ndwi).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=san_bruno_roi,
        scale=10,  # 10m resolution for Sentinel-2
        maxPixels=1e9,
    ).getInfo()

    print("\n[2] Computed Vegetation Indices over San Bruno WUI (GEE Cloud Reduction):")
    print(f"    • Mean NDVI (Vegetation Greenness) : {stats.get('NDVI', 0):.4f}")
    print(f"    • Mean NDWI (Fuel Moisture Index)  : {stats.get('NDWI', 0):.4f}")

    print("\n" + "=" * 70)
    print("✅ GEE DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_gee_sentinel2_demo()
