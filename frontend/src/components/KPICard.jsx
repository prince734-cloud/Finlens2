import React from 'react';
import { ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';

export default function KPICard({ title, value, change, isPositive = true, subtitle, icon: Icon }) {
  return (
    <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all shadow-sm">
      <div className="flex items-center justify-between text-slate-400 mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider">{title}</span>
        {Icon ? (
          <div className="p-2 rounded-lg bg-slate-800/80 text-emerald-400">
            <Icon className="w-4 h-4" />
          </div>
        ) : (
          <Activity className="w-4 h-4 text-slate-500" />
        )}
      </div>

      <div className="flex items-baseline justify-between">
        <h3 className="text-2xl font-bold tracking-tight text-white">{value}</h3>
        {change && (
          <span
            className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-md ${
              isPositive
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
            }`}
          >
            {isPositive ? (
              <ArrowUpRight className="w-3 h-3 mr-0.5" />
            ) : (
              <ArrowDownRight className="w-3 h-3 mr-0.5" />
            )}
            {change}
          </span>
        )}
      </div>

      {subtitle && <p className="mt-2 text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
}
