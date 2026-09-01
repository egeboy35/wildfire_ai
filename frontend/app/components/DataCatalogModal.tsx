'use client';

import React, { useEffect, useState } from 'react';
import { BookOpen, X, Layers, Sparkles, Shield, Wind, Home, ExternalLink, CheckCircle2 } from 'lucide-react';
import { API_BASE } from '@/app/lib/api';

interface DataCatalogModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DataCatalogModal({ isOpen, onClose }: DataCatalogModalProps) {
  const [catalog, setCatalog] = useState<any[]>([]);

  useEffect(() => {
    if (isOpen) {
      fetch(`${API_BASE}/api/data-catalog`)
        .then((res) => res.json())
        .then((data) => {
          if (data.success && data.catalog) {
            setCatalog(data.catalog);
          }
        })
        .catch((err) => console.error('Failed to fetch data catalog:', err));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const getIcon = (id: string) => {
    switch (id) {
      case 'bellwether':
        return <Layers className="w-5 h-5 text-orange-400" />;
      case 'sentinel2':
        return <Sparkles className="w-5 h-5 text-cyan-400" />;
      case 'calfire_insurance':
        return <Shield className="w-5 h-5 text-red-400" />;
      case 'noaa_hrrr':
        return <Wind className="w-5 h-5 text-blue-400" />;
      case 'parcels_cropland':
        return <Home className="w-5 h-5 text-emerald-400" />;
      default:
        return <BookOpen className="w-5 h-5 text-amber-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-4xl max-h-[85vh] rounded-3xl p-6 shadow-2xl border border-slate-700/80 flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/30">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Multi-Source Data Catalog & Documentation</h2>
              <p className="text-xs text-slate-400">
                Detailed specifications of Bellwether AI, Sentinel-2, CAL FIRE, NOAA HRRR & Assessor Parcels
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content - Data Source Cards */}
        <div className="flex-1 overflow-y-auto py-5 space-y-4 pr-2">
          {catalog.map((item) => (
            <div
              key={item.id}
              className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/90 hover:border-slate-700 transition-all space-y-3"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-slate-800 border border-slate-700">
                    {getIcon(item.id)}
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-slate-100">{item.name}</h3>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                      <span className="text-orange-400 font-semibold">{item.provider}</span>
                      <span>•</span>
                      <span>Resolution: {item.resolution}</span>
                      <span>•</span>
                      <span>Update: {item.update_cadence}</span>
                    </div>
                  </div>
                </div>
                <div className="px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Active Stream
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/40 p-3 rounded-xl border border-slate-800/50">
                {item.description}
              </p>

              <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800/60">
                <span className="text-slate-400 font-medium">Application Role:</span>
                <span className="text-slate-200 font-semibold">{item.usage_in_app}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Modal Footer */}
        <div className="pt-4 border-t border-slate-800 shrink-0 flex items-center justify-between text-xs text-slate-400">
          <span>San Bruno Fire Department × SJSU WIRC Data Governance</span>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-orange-500 text-white font-bold hover:bg-orange-600 transition-colors shadow-lg glow-orange"
          >
            Close Documentation
          </button>
        </div>
      </div>
    </div>
  );
}
