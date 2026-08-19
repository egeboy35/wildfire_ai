"""
Contagion Node Corridor & "Quantification of the Negative" Model
Implements the Eric Saylors contagion node methodology for wildland-urban interface (WUI) risk.
Calculates 130-foot (39.6m) radiant heat propagation buffer corridors around fire ignition/WUI nodes
and evaluates threatened vs. saved property asset values (Municipal ROI).
"""

from typing import Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import geopandas as gpd
    from shapely.geometry import MultiPolygon, Polygon, box
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False


class ContagionCorridor:
    """Contagion corridor calculator for WUI wildfire risk mitigation ROI."""

    # 130 feet in meters (standard radiant heat propagation radius in WUI pilot spec)
    DEFAULT_HEAT_RADIUS_FEET = 130.0
    FEET_TO_METERS = 0.3048
    DEFAULT_HEAT_RADIUS_METERS = DEFAULT_HEAT_RADIUS_FEET * FEET_TO_METERS  # ~39.624 meters

    # Average San Francisco Bay Area / San Bruno residential structural value per sq ft
    AVG_PROPERTY_VAL_PER_SQFT = 650.0  # USD / sq ft

    def __init__(self, heat_radius_feet: float = 130.0):
        self.radius_feet = heat_radius_feet
        self.radius_meters = heat_radius_feet * self.FEET_TO_METERS

    def create_buffer_corridor(
        self, geometry: Union[Polygon, MultiPolygon, "gpd.GeoSeries"]
    ) -> Union[Polygon, MultiPolygon]:
        """
        Create a 130-foot radiant heat buffer around wildland fire boundaries or ignition nodes.
        Note: Geometry should ideally be in a projected CRS (e.g. EPSG:3857 or UTM zone 10N) for meter metrics.
        """
        if not HAS_GEOPANDAS:
            raise RuntimeError("geopandas and shapely are required for buffer operations.")

        buffer_geom = geometry.buffer(self.radius_meters)
        return buffer_geom

    def calculate_saved_assets(
        self,
        building_footprints: "gpd.GeoDataFrame",
        risk_corridor: Union[Polygon, MultiPolygon],
        intervention_success_rate: float = 0.85,
    ) -> Dict[str, Union[int, float]]:
        """
        Compute 'Quantification of the Negative' metrics:
        - Number of threatened properties inside the 130-foot corridor
        - Total square footage of threatened structures
        - Estimated property value saved by fire department intervention
        
        Args:
            building_footprints: GeoDataFrame containing building polygons
            risk_corridor: Polygon/MultiPolygon of the 130ft radiant heat corridor
            intervention_success_rate: Assumed fire service mitigation success rate (e.g., 85%)
        
        Returns:
            Dict of summary metrics
        """
        if not HAS_GEOPANDAS:
            raise RuntimeError("geopandas is required.")

        # Spatial intersection
        threatened = building_footprints[building_footprints.intersects(risk_corridor)]
        
        num_structures = len(threatened)
        
        # Calculate area in sq ft if available or converted
        if threatened.crs and threatened.crs.is_projected:
            total_area_sqm = threatened.geometry.area.sum()
            total_area_sqft = total_area_sqm * 10.7639
        else:
            # Fallback area calculation if approximate
            total_area_sqft = num_structures * 2200.0  # Assumed average 2200 sq ft home

        total_value_threatened = total_area_sqft * self.AVG_PROPERTY_VAL_PER_SQFT
        value_saved_by_intervention = total_value_threatened * intervention_success_rate

        metrics = {
            "threatened_structures_count": num_structures,
            "threatened_building_area_sqft": round(total_area_sqft, 2),
            "estimated_total_value_threatened_usd": round(total_value_threatened, 2),
            "estimated_value_saved_usd": round(value_saved_by_intervention, 2),
            "radiant_heat_radius_feet": self.radius_feet,
            "intervention_success_rate_pct": round(intervention_success_rate * 100, 1),
        }

        return metrics


if __name__ == "__main__":
    if HAS_GEOPANDAS:
        corridor = ContagionCorridor(heat_radius_feet=130.0)
        print(f"Radiant Heat Buffer Radius: {corridor.radius_feet} ft ({corridor.radius_meters:.2f} m)")
        
        # Create a mock polygon and mock building footprints for self-test
        poly = box(-122.42, 37.61, -122.41, 37.62)
        mock_buildings = gpd.GeoDataFrame(
            {"geometry": [box(-122.415, 37.615, -122.414, 37.616)]}, crs="EPSG:4326"
        )
        buffered = corridor.create_buffer_corridor(poly)
        metrics = corridor.calculate_saved_assets(mock_buildings, buffered)
        print("Mock Saved Asset Metrics:", metrics)
    else:
        print("geopandas not installed.")
