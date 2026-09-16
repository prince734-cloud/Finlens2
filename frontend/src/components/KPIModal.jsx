import React from 'react';
import { X, DollarSign, TrendingUp, ShieldAlert, CheckCircle2, Building, Calendar, Layers } from 'lucide-react';

export default function KPIModal({ kpi, onClose }) {
  if (!kpi) return null;

  const formatCurrency = (val, currency = 'USD') => {
    if (val === null || val === undefined) return '—';
    const abs = Math.abs(val);
    const sym = currency === 'INR' ? '₹' : '$';
    
    if (abs >= 1e12) return `${sym}${(val / 1e12).toFixed(2)}T`;
    if (abs >= 1e9) return `${sym}${(val / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `${sym}${(val / 1e6).toFixed(2)}M`;
    if (abs >= 1e3) return `${sym}${(val / 1e3).toFixed(2)}K`;
    return `${sym}${val.toLocaleString()}`;
  };

  const formatGrowth = (rate) => {
    if (rate === null || rate === undefined) return null;
    const pct = (rate * 100).toFixed(1);
    const isPos = rate >= 0;
    return (
      <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
        isPos ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
      }`}>
        {isPos ? `+${pct}%` : `${pct}%`} YoY
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#111827] border border-slate-800 rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-[#111827]/95 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Building className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-tight">{kpi.company_name}</h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono font-medium">
                  FY {kpi.financial_year}
                </span>
              </div>
              <p className="text-xs text-slate-400">Structured Financial Key Performance Indicators</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {/* Top Primary Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {/* Revenue */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 block mb-1">
                Total Revenue
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold text-white font-mono">
                  {formatCurrency(kpi.revenue, kpi.currency)}
                </span>
                {formatGrowth(kpi.revenue_growth)}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Consolidated Net Sales</span>
            </div>

            {/* Net Income */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 block mb-1">
                Net Income
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-bold text-emerald-400 font-mono">
                  {formatCurrency(kpi.net_income, kpi.currency)}
                </span>
                {formatGrowth(kpi.net_income_growth)}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Net Profit After Tax</span>
            </div>

            {/* Operating Cash Flow */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 block mb-1">
                Operating Cash Flow
              </span>
              <span className="text-xl font-bold text-white font-mono">
                {formatCurrency(kpi.operating_cash_flow, kpi.currency)}
              </span>
              <span className="text-[10px] text-slate-500 mt-1 block">Cash From Operations</span>
            </div>

            {/* Operating Income */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 block mb-1">
                Operating Income (EBIT)
              </span>
              <span className="text-xl font-bold text-white font-mono">
                {formatCurrency(kpi.operating_income, kpi.currency)}
              </span>
              <span className="text-[10px] text-slate-500 mt-1 block">Core Business Operations</span>
            </div>

            {/* Total Assets */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 block mb-1">
                Total Assets
              </span>
              <span className="text-xl font-bold text-slate-200 font-mono">
                {formatCurrency(kpi.total_assets, kpi.currency)}
              </span>
              <span className="text-[10px] text-slate-500 mt-1 block">Balance Sheet Assets</span>
            </div>

            {/* Total Liabilities */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 block mb-1">
                Total Liabilities
              </span>
              <span className="text-xl font-bold text-slate-200 font-mono">
                {formatCurrency(kpi.total_liabilities, kpi.currency)}
              </span>
              <span className="text-[10px] text-slate-500 mt-1 block">Balance Sheet Obligations</span>
            </div>
          </div>

          {/* Growth Drivers & Risk Factors */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Growth Drivers */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-3">
                <CheckCircle2 className="w-4 h-4" />
                <span>Extracted Growth Drivers</span>
              </div>
              {kpi.growth_drivers && kpi.growth_drivers.length > 0 ? (
                <ul className="space-y-2">
                  {kpi.growth_drivers.map((driver, idx) => (
                    <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-emerald-500 font-bold">✓</span>
                      <span>{driver}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">No specific growth drivers listed.</p>
              )}
            </div>

            {/* Major Risk Factors */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-3">
                <ShieldAlert className="w-4 h-4" />
                <span>Major Risk Factors (Item 1A)</span>
              </div>
              {kpi.risk_factors && kpi.risk_factors.length > 0 ? (
                <ul className="space-y-2">
                  {kpi.risk_factors.map((risk, idx) => (
                    <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-amber-500 font-bold">⚠</span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">No specific risk factors extracted.</p>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500 bg-slate-900/40">
          <span>Grounded extraction persisted in database.</span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
