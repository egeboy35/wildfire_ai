'use client';

import React, { useEffect, useState } from 'react';
import L from 'leaflet';
import { API_BASE } from '@/app/lib/api';

interface MapViewProps {
  activeLayer: '1yr' | '5yr' | 'none';
  selectedRegion: string;
  showSentinel: boolean;
  showCalFire: boolean;
  showWeather: boolean;
  showBuildings: boolean;
  showCalfirePerimeters: boolean;
  showFirmsHotspots: boolean;
  showFuelMoisture: boolean;
  showTerrainSlope: boolean;
  opacity: number;
  onSelectLocation: (data: any) => void;
  onLayerStatsUpdate: (stats: any) => void;
}

const REGION_CENTERS: Record<string, [number, number]> = {
  san_bruno: [37.618, -122.425],
  san_jose: [37.338, -121.886],
  santa_cruz: [37.125, -122.050],
};

export default function MapView({
  activeLayer,
  selectedRegion,
  showSentinel,
  showCalFire,
  showWeather,
  showBuildings,
  showCalfirePerimeters,
  showFirmsHotspots,
  showFuelMoisture,
  showTerrainSlope,
  opacity,
  onSelectLocation,
  onLayerStatsUpdate,
}: MapViewProps) {
  const [map, setMap] = useState<L.Map | null>(null);
  const [bellwetherOverlay, setBellwetherOverlay] = useState<L.ImageOverlay | null>(null);
  const [calfireOverlay, setCalfireOverlay] = useState<L.ImageOverlay | null>(null);
  const [terrainSlopeOverlay, setTerrainSlopeOverlay] = useState<L.ImageOverlay | null>(null);
  const [buildingsLayer, setBuildingsLayer] = useState<L.GeoJSON | null>(null);
  const [perimetersLayer, setPerimetersLayer] = useState<L.GeoJSON | null>(null);
  const [firmsLayer, setFirmsLayer] = useState<L.GeoJSON | null>(null);
  const [fuelMoistureLayer, setFuelMoistureLayer] = useState<L.GeoJSON | null>(null);
  const [corridorCircle, setCorridorCircle] = useState<L.Circle | null>(null);
  const [fireMarker, setFireMarker] = useState<L.Marker | null>(null);

  // Initialize Leaflet Map
  useEffect(() => {
    const mapInstance = L.map('leaflet-map', {
      center: REGION_CENTERS[selectedRegion] || [37.618, -122.425],
      zoom: 13,
      zoomControl: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; CARTO &copy; Bellwether / CAL FIRE / NASA FIRMS / CDEC / USGS',
    }).addTo(mapInstance);

    L.control.zoom({ position: 'bottomleft' }).addTo(mapInstance);

    setMap(mapInstance);

    return () => {
      mapInstance.remove();
    };
  }, []);

  // Handle Region Change (FlyTo)
  useEffect(() => {
    if (!map) return;
    const targetCenter = REGION_CENTERS[selectedRegion] || [37.618, -122.425];
    map.flyTo(targetCenter, 13, { duration: 1.5 });
  }, [map, selectedRegion]);

  // Update Bellwether Probability Layer (Dynamic Region BBox Crop)
  useEffect(() => {
    if (!map) return;

    if (bellwetherOverlay) {
      map.removeLayer(bellwetherOverlay);
      setBellwetherOverlay(null);
    }

    if (activeLayer === 'none') return;

    const is5Yr = activeLayer === '5yr';
    fetch(`${API_BASE}/api/layers/bellwether?is_5_year=${is5Yr}&region=${selectedRegion}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.layer) {
          const { image_url, bounds, stats } = data.layer;
          const overlayUrl = `${API_BASE}${image_url}`;
          
          const newOverlay = L.imageOverlay(overlayUrl, bounds, {
            opacity: opacity,
            interactive: false,
          }).addTo(map);

          setBellwetherOverlay(newOverlay);
          onLayerStatsUpdate(stats);
        }
      })
      .catch((err) => console.error('Failed to load Bellwether overlay:', err));
  }, [map, activeLayer, selectedRegion]);

  // Update CAL FIRE Fire Perimeters Layer
  useEffect(() => {
    if (!map) return;
    if (perimetersLayer) {
      map.removeLayer(perimetersLayer);
      setPerimetersLayer(null);
    }
    if (!showCalfirePerimeters) return;

    fetch(`${API_BASE}/api/layers/calfire-perimeters`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.perimeters) {
          const geoJsonLayer = L.geoJSON(data.perimeters, {
            style: (feature) => ({
              color: feature?.properties?.color || '#dc2626',
              weight: 2.5,
              fillColor: '#ef4444',
              fillOpacity: 0.35,
              dashArray: '6, 6',
            }),
            onEachFeature: (feature, layer) => {
              const p = feature.properties;
              layer.bindTooltip(`
                <div class="p-1 text-xs space-y-1 font-sans">
                  <div class="font-bold text-red-400">${p.fire_name}</div>
                  <div><strong class="text-slate-300">Burned:</strong> ${p.acres_burned} Acres</div>
                  <div><strong class="text-slate-300">Containment:</strong> ${p.containment_pct}%</div>
                  <div><strong class="text-slate-300">Agency:</strong> ${p.agency}</div>
                  <div class="text-[10px] text-amber-400 mt-1">${p.status}</div>
                </div>
              `, { sticky: true });
            },
          }).addTo(map);
          setPerimetersLayer(geoJsonLayer);
        }
      });
  }, [map, showCalfirePerimeters]);

  // Update NASA FIRMS Satellite Thermal Hotspots Layer
  useEffect(() => {
    if (!map) return;
    if (firmsLayer) {
      map.removeLayer(firmsLayer);
      setFirmsLayer(null);
    }
    if (!showFirmsHotspots) return;

    fetch(`${API_BASE}/api/layers/firms-hotspots`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.hotspots) {
          const geoJsonLayer = L.geoJSON(data.hotspots, {
            pointToLayer: (feature, latlng) => {
              return L.circleMarker(latlng, {
                radius: 8,
                fillColor: '#f59e0b',
                color: '#b45309',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8,
              });
            },
            onEachFeature: (feature, layer) => {
              const p = feature.properties;
              layer.bindTooltip(`
                <div class="p-1 text-xs space-y-1 font-sans">
                  <div class="font-bold text-amber-400">🛰️ ${p.sensor} Thermal Hotspot</div>
                  <div><strong class="text-slate-300">Brightness:</strong> ${p.brightness_kelvin} K</div>
                  <div><strong class="text-slate-300">Radiative Power:</strong> ${p.frp_mw} MW</div>
                  <div><strong class="text-slate-300">Confidence:</strong> ${p.confidence}</div>
                  <div class="text-[10px] text-slate-400">${p.acquisition_time}</div>
                </div>
              `, { sticky: true });
            },
          }).addTo(map);
          setFirmsLayer(geoJsonLayer);
        }
      });
  }, [map, showFirmsHotspots]);

  // Update CDEC Fuel Moisture Layer
  useEffect(() => {
    if (!map) return;
    if (fuelMoistureLayer) {
      map.removeLayer(fuelMoistureLayer);
      setFuelMoistureLayer(null);
    }
    if (!showFuelMoisture) return;

    fetch(`${API_BASE}/api/layers/fuel-moisture`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.stations) {
          const geoJsonLayer = L.geoJSON(data.stations, {
            pointToLayer: (feature, latlng) => {
              return L.circleMarker(latlng, {
                radius: 9,
                fillColor: '#14b8a6',
                color: '#0f766e',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.85,
              });
            },
            onEachFeature: (feature, layer) => {
              const p = feature.properties;
              layer.bindTooltip(`
                <div class="p-1 text-xs space-y-1 font-sans">
                  <div class="font-bold text-teal-400">🧪 RAWS Station: ${p.station_name} (${p.station_id})</div>
                  <div><strong class="text-slate-300">10-hr DFM:</strong> ${p.ten_hour_dfm_pct}%</div>
                  <div><strong class="text-slate-300">100-hr DFM:</strong> ${p.hundred_hour_dfm_pct}%</div>
                  <div><strong class="text-slate-300">Live LFMC:</strong> ${p.lfmc_pct}%</div>
                  <div class="text-[10px] text-red-400 font-bold mt-1">${p.status}</div>
                </div>
              `, { sticky: true });
            },
          }).addTo(map);
          setFuelMoistureLayer(geoJsonLayer);
        }
      });
  }, [map, showFuelMoisture]);

  // Update USGS Terrain Slope Overlay Layer
  useEffect(() => {
    if (!map) return;
    if (terrainSlopeOverlay) {
      map.removeLayer(terrainSlopeOverlay);
      setTerrainSlopeOverlay(null);
    }
    if (!showTerrainSlope) return;

    fetch(`${API_BASE}/api/layers/terrain-slope`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.layer) {
          const { image_url, bounds } = data.layer;
          const newOverlay = L.imageOverlay(`${API_BASE}${image_url}`, bounds, {
            opacity: 0.55,
            interactive: false,
          }).addTo(map);
          setTerrainSlopeOverlay(newOverlay);
        }
      });
  }, [map, showTerrainSlope]);

  // Update Building Footprints GeoJSON Layer
  useEffect(() => {
    if (!map) return;

    if (buildingsLayer) {
      map.removeLayer(buildingsLayer);
      setBuildingsLayer(null);
    }

    if (!showBuildings) return;

    fetch(`${API_BASE}/api/layers/buildings`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.buildings) {
          const geoJsonLayer = L.geoJSON(data.buildings, {
            style: () => ({
              color: '#10b981',
              weight: 1.5,
              fillColor: '#059669',
              fillOpacity: 0.45,
            }),
            onEachFeature: (feature, layer) => {
              const p = feature.properties;
              const tooltipContent = `
                <div class="p-1.5 text-xs space-y-1 font-sans">
                  <div class="font-bold text-emerald-400 border-b border-slate-700 pb-1">${p.building_id} (${p.structure_type})</div>
                  <div><strong class="text-slate-300">Source:</strong> ${p.source}</div>
                  <div><strong class="text-slate-300">APN:</strong> ${p.apn}</div>
                  <div><strong class="text-slate-300">Area:</strong> ${p.area_sqft.toLocaleString()} sq ft</div>
                  <div><strong class="text-slate-300">Value:</strong> $${p.assessed_value_usd.toLocaleString()} USD</div>
                  <div><strong class="text-slate-300">Nearest Hydrant:</strong> ${p.nearest_hydrant_distance_ft} ft</div>
                  <div class="text-[10px] text-amber-400 font-semibold mt-1">IBHS: ${p.roof_class}</div>
                </div>
              `;
              layer.bindTooltip(tooltipContent, { sticky: true, className: 'glass-panel text-slate-100 rounded-xl' });
            },
          }).addTo(map);

          setBuildingsLayer(geoJsonLayer);
        }
      })
      .catch((err) => console.error('Failed to load building footprints:', err));
  }, [map, showBuildings]);

  // Update CAL FIRE FHSZ Overlay
  useEffect(() => {
    if (!map) return;

    if (calfireOverlay) {
      map.removeLayer(calfireOverlay);
      setCalfireOverlay(null);
    }

    if (!showCalFire) return;

    fetch(`${API_BASE}/api/layers/calfire`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.layer) {
          const { image_url, bounds } = data.layer;
          const newOverlay = L.imageOverlay(`${API_BASE}${image_url}`, bounds, {
            opacity: 0.65,
            interactive: false,
          }).addTo(map);
          setCalfireOverlay(newOverlay);
        }
      })
      .catch((err) => console.error('Failed to load CAL FIRE overlay:', err));
  }, [map, showCalFire]);

  // Update Opacity
  useEffect(() => {
    if (bellwetherOverlay) {
      bellwetherOverlay.setOpacity(opacity);
    }
  }, [opacity, bellwetherOverlay]);

  // Handle Map Clicks for Wind-Adjusted 130ft Radiant Heat Corridor
  useEffect(() => {
    if (!map) return;

    const handleMapClick = (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;

      if (fireMarker) map.removeLayer(fireMarker);
      if (corridorCircle) map.removeLayer(corridorCircle);

      const fireIcon = L.divIcon({
        className: 'custom-fire-marker',
        html: `
          <div class="relative flex items-center justify-center">
            <span class="animate-ping absolute inline-flex h-8 w-8 rounded-full bg-orange-400 opacity-75"></span>
            <div class="relative p-2 bg-orange-600 border-2 border-amber-300 rounded-full shadow-lg text-white font-bold text-xs flex items-center justify-center">
              🔥
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const newMarker = L.marker([lat, lng], { icon: fireIcon }).addTo(map);
      setFireMarker(newMarker);

      fetch(`${API_BASE}/api/query-corridor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lng, radius_feet: 130 }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success && data.data) {
            onSelectLocation(data.data);
            const majorRadius = data.data.wind_adjusted_major_radius_meters || 39.62;

            const newCircle = L.circle([lat, lng], {
              radius: majorRadius,
              color: '#f97316',
              weight: 2,
              fillColor: '#ea580c',
              fillOpacity: 0.35,
              dashArray: '4, 6',
            }).addTo(map);

            setCorridorCircle(newCircle);
          }
        })
        .catch((err) => console.error('Failed to query corridor API:', err));
    };

    map.on('click', handleMapClick);

    return () => {
      map.off('click', handleMapClick);
    };
  }, [map, fireMarker, corridorCircle]);

  return (
    <div className="w-full h-full relative">
      <div id="leaflet-map" className="w-full h-full z-10" />
    </div>
  );
}
