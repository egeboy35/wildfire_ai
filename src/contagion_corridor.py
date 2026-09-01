"""
Contagion Node Corridor & "Quantification of the Negative" Model
Implements the Eric Saylors contagion node methodology for wildland-urban interface (WUI) risk.
Calculates 130-foot (39.6m) radiant heat propagation buffer corridors around fire ignition/WUI nodes
and evaluates threatened vs. saved property asset values (Municipal ROI).
"""

import warnings
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import geopandas as gpd
    from shapely.geometry import MultiPolygon, Polygon, box
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

try:
    from pyproj import CRS
except ImportError:  # pyproj ships with geopandas; guard so the module still imports
    CRS = None

# pyproj spells the linear metre several ways depending on the CRS definition.
_METRE_UNIT_NAMES = {"metre", "meter", "m"}


class ContagionCorridor:
    """Contagion corridor calculator for WUI wildfire risk mitigation ROI."""

    # 130 feet in meters (standard radiant heat propagation radius in WUI pilot spec)
    DEFAULT_HEAT_RADIUS_FEET = 130.0
    FEET_TO_METERS = 0.3048
    DEFAULT_HEAT_RADIUS_METERS = DEFAULT_HEAT_RADIUS_FEET * FEET_TO_METERS  # ~39.624 meters

    # Average San Francisco Bay Area / San Bruno residential structural value per sq ft
    AVG_PROPERTY_VAL_PER_SQFT = 650.0  # USD / sq ft

    # Used only when footprint areas cannot be measured; see calculate_saved_assets.
    ASSUMED_STRUCTURE_SQFT = 2200.0

    def __init__(self, heat_radius_feet: float = 130.0):
        self.radius_feet = heat_radius_feet
        self.radius_meters = heat_radius_feet * self.FEET_TO_METERS

    def create_buffer_corridor(
        self,
        geometry: Union[Polygon, MultiPolygon, "gpd.GeoSeries"],
        crs: Optional[object] = None,
    ) -> Union[Polygon, MultiPolygon]:
        """
        Create a 130-foot radiant heat buffer around wildland fire boundaries or ignition nodes.

        ``shapely``'s ``buffer()`` works in whatever units the coordinates are
        in, so the geometry must be in a CRS whose axes are metres. Two ways to
        get that wrong are worth naming:

        * A geographic CRS such as EPSG:4326 is in degrees. Buffering by 39.624
          degrees gives a corridor about 4,400 km across -- roughly 111,000
          times too large -- and raises nothing.
        * A projected CRS in US survey feet, such as EPSG:2227 (California
          State Plane zone 3), buffers by 39.624 feet: 3.28 times too small.

        Both are refused when ``crs`` is passed. Nearly every source in this
        project's data index is EPSG:4326, so pass ``crs`` whenever you have it.

        Note that being projected is necessary but not sufficient for accurate
        ground distances. EPSG:3857 (Web Mercator) is in metres and would be
        accepted, but its scale factor at 37.6 deg N is 1.2624, so a 39.624 m
        buffer covers 31.4 m on the ground -- about 21 percent short. Prefer a
        local projection: EPSG:32610 (UTM zone 10N) for the Bay Area.

        Args:
            geometry: the geometry to buffer, in a metre-based projected CRS.
            crs: optional CRS of ``geometry``. When given and not in metres,
                this raises instead of returning a wrongly scaled corridor.
        """
        if not HAS_GEOPANDAS:
            raise RuntimeError("geopandas and shapely are required for buffer operations.")

        if crs is not None:
            crs_obj = CRS.from_user_input(crs) if CRS is not None else None
            if crs_obj is not None and not crs_obj.is_projected:
                raise ValueError(
                    f"create_buffer_corridor() buffers by {self.radius_meters:.3f} metres, but "
                    f"{crs_obj.name!r} is a geographic CRS whose units are degrees. Buffering "
                    f"by {self.radius_meters:.3f} degrees would give a corridor about "
                    f"{self.radius_meters * 111.32:,.0f} km across instead of "
                    f"{self.radius_meters:.1f} m. Reproject to a projected CRS first, "
                    "for example EPSG:32610 (UTM 10N) for the Bay Area."
                )
            if crs_obj is not None and crs_obj.is_projected:
                units = {axis.unit_name for axis in crs_obj.axis_info}
                if not units <= _METRE_UNIT_NAMES:
                    raise ValueError(
                        f"create_buffer_corridor() buffers by {self.radius_meters:.3f} metres, "
                        f"but {crs_obj.name!r} has axis units {sorted(units)}. The buffer would "
                        f"be {self.radius_meters:.3f} of those units instead. Reproject to a "
                        "metre-based CRS first, for example EPSG:32610 (UTM 10N)."
                    )

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
        area_is_measured = bool(threatened.crs and threatened.crs.is_projected)
        if area_is_measured:
            total_area_sqm = threatened.geometry.area.sum()
            total_area_sqft = total_area_sqm * 10.7639
        else:
            # No projected CRS, so polygon areas are in square degrees and cannot be
            # converted. Substitute a nominal footprint -- and say so, because every
            # dollar figure below is then derived from this assumption rather than
            # from the data. Silently substituting it is how a geometry error in the
            # corridor upstream stays invisible.
            total_area_sqft = num_structures * self.ASSUMED_STRUCTURE_SQFT
            warnings.warn(
                f"building_footprints has no projected CRS (crs={threatened.crs!r}), so "
                f"structure areas were not measured. Falling back to "
                f"{self.ASSUMED_STRUCTURE_SQFT:.0f} sq ft per structure; the value figures "
                "are estimates from that assumption, not from the footprints. Reproject to "
                "a projected CRS such as EPSG:32610 for measured areas.",
                stacklevel=2,
            )

        total_value_threatened = total_area_sqft * self.AVG_PROPERTY_VAL_PER_SQFT
        value_saved_by_intervention = total_value_threatened * intervention_success_rate

        metrics = {
            "threatened_structures_count": num_structures,
            "threatened_building_area_sqft": round(total_area_sqft, 2),
            "estimated_total_value_threatened_usd": round(total_value_threatened, 2),
            "estimated_value_saved_usd": round(value_saved_by_intervention, 2),
            "radiant_heat_radius_feet": self.radius_feet,
            "intervention_success_rate_pct": round(intervention_success_rate * 100, 1),
            # False when the areas above are the nominal per-structure assumption
            # rather than measured polygon areas.
            "building_area_is_measured": area_is_measured,
        }

        return metrics


if __name__ == "__main__":
    if HAS_GEOPANDAS:
        corridor = ContagionCorridor(heat_radius_feet=130.0)
        print(f"Radiant Heat Buffer Radius: {corridor.radius_feet} ft ({corridor.radius_meters:.2f} m)")
        
        # Self-test in a PROJECTED CRS. The buffer radius is in metres, so the
        # geometry has to be too; in EPSG:4326 the same call buffers by ~39.6
        # degrees and produces a corridor thousands of kilometres across.
        # EPSG:32610 is UTM zone 10N, which covers the Bay Area.
        wgs84_aoi = gpd.GeoDataFrame(
            {"geometry": [box(-122.42, 37.61, -122.41, 37.62)]}, crs="EPSG:4326"
        )
        # About 9.4 m x 11.8 m, i.e. a ~1,180 sq ft house. The 0.001-degree box
        # this replaced was 88.9 m x 111.5 m -- 2.4 acres, a city block.
        wgs84_buildings = gpd.GeoDataFrame(
            {"geometry": [box(-122.415, 37.615, -122.414894, 37.615106)]}, crs="EPSG:4326"
        )
        aoi = wgs84_aoi.to_crs("EPSG:32610")
        mock_buildings = wgs84_buildings.to_crs("EPSG:32610")

        buffered = corridor.create_buffer_corridor(aoi.geometry.iloc[0], crs=aoi.crs)
        metrics = corridor.calculate_saved_assets(mock_buildings, buffered)
        print("Mock Saved Asset Metrics:", metrics)

        # And show what the guard now prevents.
        try:
            corridor.create_buffer_corridor(wgs84_aoi.geometry.iloc[0], crs=wgs84_aoi.crs)
        except ValueError as exc:
            print()
            print(f"Guard on a geographic CRS: {exc}")
    else:
        print("geopandas not installed.")
