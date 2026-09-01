"""Regression tests for the radiant-heat corridor geometry.

The corridor radius is in metres, so the geometry it buffers has to be in a
projected CRS. Nearly every source in this project's data index is EPSG:4326,
whose units are degrees, and shapely's ``buffer()`` will happily apply a
39.624-*degree* radius without raising anything -- a corridor about 4,400 km
across where 39.6 m was intended. Downstream, ``calculate_saved_assets`` then
finds no projected CRS, substitutes a nominal per-structure footprint and
returns a tidy dollar figure, so nothing about the geometry error ever
surfaces. These tests pin both halves of that.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

gpd = pytest.importorskip("geopandas")
from shapely.geometry import box  # noqa: E402

from contagion_corridor import ContagionCorridor  # noqa: E402

# A small area of interest over San Bruno, in the geographic CRS the fetchers return.
AOI_WGS84 = box(-122.42, 37.61, -122.41, 37.62)
UTM10N = "EPSG:32610"


def _wgs84_frame(geom):
    return gpd.GeoDataFrame({"geometry": [geom]}, crs="EPSG:4326")


def test_buffer_refuses_a_geographic_crs():
    """The guard exists because the failure is silent, not loud."""
    corridor = ContagionCorridor(heat_radius_feet=130.0)
    with pytest.raises(ValueError, match="geographic CRS"):
        corridor.create_buffer_corridor(AOI_WGS84, crs="EPSG:4326")


def test_buffer_refuses_a_projected_crs_measured_in_feet():
    """Being projected is not enough: the axes have to be metres.

    EPSG:2227 is California State Plane zone 3 in US survey feet. It is a
    projected CRS, so an is_projected check alone would accept it, and the
    buffer would then be 39.624 feet -- 3.28 times too small.
    """
    gpd = pytest.importorskip("geopandas")
    aoi = gpd.GeoDataFrame(
        {"geometry": [box(-122.42, 37.61, -122.41, 37.62)]}, crs="EPSG:4326"
    ).to_crs("EPSG:2227")
    assert aoi.crs.is_projected, "EPSG:2227 must be projected for this test to mean anything"

    corridor = ContagionCorridor(heat_radius_feet=130.0)
    with pytest.raises(ValueError) as excinfo:
        corridor.create_buffer_corridor(aoi.geometry.iloc[0], crs=aoi.crs)
    assert "foot" in str(excinfo.value).lower() or "feet" in str(excinfo.value).lower()


def test_buffer_in_a_projected_crs_has_the_requested_radius():
    """130 ft = 39.624 m, and in UTM the buffer must actually be that wide."""
    corridor = ContagionCorridor(heat_radius_feet=130.0)
    aoi = _wgs84_frame(AOI_WGS84).to_crs(UTM10N)
    geom = aoi.geometry.iloc[0]
    buffered = corridor.create_buffer_corridor(geom, crs=aoi.crs)

    # The bounding box grows by one radius on each side, in metres. The tolerance
    # is 0.1% rather than exact because reprojecting an axis-aligned lat/lon box
    # into UTM yields a very slightly rotated quadrilateral, so its bounds grow
    # by marginally less than 2r.
    grew_x = (buffered.bounds[2] - buffered.bounds[0]) - (geom.bounds[2] - geom.bounds[0])
    grew_y = (buffered.bounds[3] - buffered.bounds[1]) - (geom.bounds[3] - geom.bounds[1])
    assert grew_x == pytest.approx(2 * corridor.radius_meters, rel=1e-3)
    assert grew_y == pytest.approx(2 * corridor.radius_meters, rel=1e-3)

    # The semantic check, independent of bounding boxes and of the slight rotation:
    # the buffer must be exactly the set of points within the radius of the
    # geometry, with the distance measured in metres.
    from shapely.geometry import Point

    r = corridor.radius_meters
    probes = []
    for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (0.7071, 0.7071)):
        cx = geom.bounds[0] + dx * (r * 3) + (geom.bounds[2] - geom.bounds[0]) / 2
        cy = geom.bounds[1] + dy * (r * 3) + (geom.bounds[3] - geom.bounds[1]) / 2
        probes.append(Point(cx, cy))
    for scale in (0.90, 0.99, 1.01, 1.10):
        for probe in probes:
            # Walk from the probe toward the geometry until we are `scale * r` away.
            d = geom.distance(probe)
            if d == 0:
                continue
            t = (d - scale * r) / d
            near = Point(
                probe.x + (geom.centroid.x - probe.x) * t,
                probe.y + (geom.centroid.y - probe.y) * t,
            )
            inside_radius = geom.distance(near) < r
            assert buffered.contains(near) == inside_radius, (
                f"point at {geom.distance(near):.3f} m from the geometry: "
                f"in buffer={buffered.contains(near)}, within {r:.3f} m={inside_radius}"
            )


def test_the_unguarded_degree_buffer_is_the_size_this_guards_against():
    """Document the magnitude, so the guard is not mistaken for pedantry.

    Buffering the same geometry by 39.624 in degrees spans latitudes far outside
    the area of interest -- this is what the shipped self-test used to do.
    """
    corridor = ContagionCorridor(heat_radius_feet=130.0)
    degrees = AOI_WGS84.buffer(corridor.radius_meters)  # no crs given: unguarded
    min_lat, max_lat = degrees.bounds[1], degrees.bounds[3]
    assert max_lat - min_lat > 70.0, "a 130 ft corridor should not span 70 degrees of latitude"


def test_area_fallback_is_announced_and_flagged():
    """When areas cannot be measured, the caller must be able to tell."""
    corridor = ContagionCorridor(heat_radius_feet=130.0)
    buildings = _wgs84_frame(box(-122.415, 37.615, -122.414, 37.616))
    corridor_geom = AOI_WGS84  # geographic, so areas are in square degrees

    with pytest.warns(UserWarning, match="no projected CRS"):
        metrics = corridor.calculate_saved_assets(buildings, corridor_geom)

    assert metrics["building_area_is_measured"] is False
    assert metrics["threatened_building_area_sqft"] == pytest.approx(
        corridor.ASSUMED_STRUCTURE_SQFT
    )


def test_measured_areas_are_flagged_as_measured():
    corridor = ContagionCorridor(heat_radius_feet=130.0)
    buildings = _wgs84_frame(box(-122.415, 37.615, -122.414, 37.616)).to_crs(UTM10N)
    aoi = _wgs84_frame(AOI_WGS84).to_crs(UTM10N)
    corridor_geom = corridor.create_buffer_corridor(aoi.geometry.iloc[0], crs=aoi.crs)

    metrics = corridor.calculate_saved_assets(buildings, corridor_geom)
    assert metrics["building_area_is_measured"] is True
    # Measured, so it must not be the nominal figure.
    assert metrics["threatened_building_area_sqft"] != pytest.approx(
        corridor.ASSUMED_STRUCTURE_SQFT
    )


def test_shipped_self_test_runs_clean():
    """`python src/contagion_corridor.py` is the module's own demonstration."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.run(
        [sys.executable, os.path.join(root, "src", "contagion_corridor.py")],
        capture_output=True, text=True, timeout=180, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "'building_area_is_measured': True" in proc.stdout
