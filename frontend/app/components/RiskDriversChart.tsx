'use client';

import React, { useEffect, useState } from 'react';
import { Activity, BarChart2 } from 'lucide-react';

export default function RiskDriversChart() {
  const [factors, setFactors] = useState<any[]>([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/risk-factors')
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.factors) {
          setFactors(data.factors.slice(0, 5));
        }
      })
      .catch((err) => console.error('Failed to fetch risk factors:', err));
  }, []);

  if (factors.length === 0) return null;

  return (
    <div className="absolute bottom-5 right-5 w-96 glass-panel rounded-2xl p-4 shadow-2xl z-20 border border-slate-800">
      <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
        <BarChart2 className="w-4 h-4 text-orange-400" />
        San Bruno Aggregated Risk Drivers (Bellwether COG)
      </div>

      <div className="space-y-2.5">
        {factors.map((item, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex justify-between text-xs text-slate-300">
              <span className="truncate pr-2 font-medium">{item.feature}</span>
              <span className="font-mono text-orange-400 font-bold">{item.weight_pct}%</span>
            </div>
            <div className="w-full bg-slate-900/80 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-orange-500 to-amber-400 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(item.weight_pct, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
