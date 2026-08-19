'use client';

import React from 'react';
import { Home, ShieldCheck, DollarSign, Flame, Activity, X, TrendingUp, AlertTriangle, Wind, MapPin, TreePine } from 'lucide-react';

interface CorridorMetricsCardProps {
  data: any;
  onClose: () => void;
}

export default function CorridorMetricsCard({ data, onClose }: CorridorMetricsCardProps) {
  if (!data) return null;

  const {
    center,
    radius_feet,
    wind_adjusted_major_radius_meters,
    live_weather,
    local_risk,
    land_cover_and_cropland,
    parcel_assessor,
    quantification_of_negative,
    top_local_drivers,
  } = data;

  const formatUSD = (val: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);

  return (
    <div className="absolute top-5 right-5 w-[420px] glass-panel rounded-2xl p-5 shadow-2xl z-30 border border-slate-700/80 animate-in fade-in slide-in-from-right duration-300 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-orange-500/20 text-orange-400 border border-orange-500/30">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-slate-100">Wind-Adjusted Radiant Heat Corridor</h3>
            <p className="text-xs text-slate-400 font-mono">
              Lat: {center.lat.toFixed(4)}, Lng: {center.lng.toFixed(4)}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Local Risk & Insurance Rating */}
      <div className="my-3.5 p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
        <div>
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
            Bellwether Burn Probability
          </span>
          <span className="text-lg font-bold text-orange-400">{local_risk.probability_percentage}</span>
          <div className="text-[10px] text-slate-400 mt-0.5">{local_risk.insurance_risk_rating}</div>
        </div>
        <div className="text-right">
          <div className="px-3 py-1 rounded-full bg-orange-500/20 border border-orange-500/40 text-orange-300 text-xs font-bold inline-block">
            {local_risk.risk_category} Risk
          </div>
        </div>
      </div>

      {/* Land Cover / Cropland & San Mateo Parcel Info */}
      <div className="grid grid-cols-2 gap-2 mb-3.5">
        <div className="p-2.5 rounded-xl bg-slate-900/40 border border-slate-800/80">
          <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-semibold mb-1">
            <TreePine className="w-3.5 h-3.5" /> Land Cover (USDA CDL)
          </div>
          <div className="text-xs font-bold text-slate-200 truncate">{land_cover_and_cropland.classification}</div>
          <div className="text-[10px] text-slate-400">{land_cover_and_cropland.fuel_model}</div>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-900/40 border border-slate-800/80">
          <div className="flex items-center gap-1.5 text-[11px] text-blue-400 font-semibold mb-1">
            <MapPin className="w-3.5 h-3.5" /> San Mateo Assessor
          </div>
          <div className="text-xs font-bold text-slate-200 font-mono">APN: {parcel_assessor.apn}</div>
          <div className="text-[10px] text-slate-400">{parcel_assessor.assessed_avg_val_per_sqft}</div>
        </div>
      </div>

      {/* Live Wind Vector */}
      {live_weather && (
        <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 mb-3.5 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-blue-300 font-medium">
            <Wind className="w-4 h-4 text-blue-400 animate-pulse" /> Live Wind Vector: {live_weather.wind_direction_cardinal} ({live_weather.wind_speed_mph} mph)
          </div>
          <span className="text-[10px] text-blue-400 font-bold font-mono">Corridor: {wind_adjusted_major_radius_meters}m</span>
        </div>
      )}

      {/* Quantification of the Negative Metrics */}
      <div className="space-y-2.5">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          Quantification of the Negative (SBFD ROI)
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800">
            <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
              <Home className="w-3.5 h-3.5 text-blue-400" /> Threatened Assets
            </div>
            <div className="text-base font-bold text-slate-100">
              {quantification_of_negative.threatened_structures_count}{' '}
              <span className="text-xs font-normal text-slate-400">structures</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              {quantification_of_negative.total_threatened_area_sqft.toLocaleString()} sq ft
            </div>
          </div>

          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold mb-1">
              <DollarSign className="w-3.5 h-3.5" /> Value Saved
            </div>
            <div className="text-base font-bold text-emerald-300">
              {formatUSD(quantification_of_negative.estimated_saved_value_usd)}
            </div>
            <div className="text-[10px] text-emerald-400/80 mt-0.5 font-medium flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> {quantification_of_negative.roi_multiplier}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
