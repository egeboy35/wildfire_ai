"""
Modular Data Fetchers Package for Wildfire AI Pilot.
Contains decoupled, agentic data fetchers for:
- Google X Project Bellwether GCS downloader & dynamic spatial cropper
- CAL FIRE active incidents & NIFC fire perimeters
- NASA FIRMS satellite active thermal hotspots (VIIRS 375m)
- CDEC / RAWS station dead & live fuel moisture (DFM/LFMC)
- USGS 3DEP 10m LiDAR terrain slope & aspect rasters
"""

from .gcs_bellwether_downloader import crop_bellwether_by_bbox
from .calfire_fetcher import get_active_perimeters
from .firms_fetcher import get_thermal_hotspots
from .cdec_raws_fetcher import get_fuel_moisture_stations
from .usgs_elevation_fetcher import get_terrain_slope_overlay
