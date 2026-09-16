import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, ChevronDown, ChevronUp, FileText } from 'lucide-react';

export default function RecommendationCard({ candidate }) {
  const [showBreakdown, setShowBreakdown] = useState(false);

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
    if (score >= 60) return 'text-sky-400 border-sky-500/30 bg-sky-500/10';
    return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
  };

  return (
    <div className="bg-[#111827] border border-slate-800 hover:border-slate-700 rounded-2xl p-6 transition-all shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {candidate.asset_type}
            </span>
            <span className="text-xs font-mono text-slate-500">{candidate.symbol_or_code}</span>
          </div>
          <h3 className="text-xl font-bold text-white tracking-tight">{candidate.asset_name}</h3>
        </div>

        {/* Match Score Badge */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold block">
              Match Score
            </span>
            <span className="text-xs text-slate-500">Deterministic Logic</span>
          </div>
          <div
            className={`w-14 h-14 rounded-2xl border flex items-center justify-center font-bold text-xl shadow-inner ${getScoreColor(
              candidate.match_score
            )}`}
          >
            {Math.round(candidate.match_score)}
          </div>
        </div>
      </div>

      {/* Rationale: Positives & Considerations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-5">
        {/* Positive Factors */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2.5">
            <CheckCircle2 className="w-4 h-4" />
            <span>Positive Factors</span>
          </div>
          <ul className="space-y-1.5">
            {candidate.positive_factors.map((item, idx) => (
              <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                <span className="text-emerald-500 font-bold">✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Considerations / Risks */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2.5">
            <AlertTriangle className="w-4 h-4" />
            <span>Risk Considerations</span>
          </div>
          <ul className="space-y-1.5">
            {candidate.considerations.map((item, idx) => (
              <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                <span className="text-amber-500 font-bold">⚠</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Score Breakdown Accordion */}
      {candidate.score_breakdown && (
        <div className="pt-2">
          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="flex items-center justify-between w-full text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors py-1.5"
          >
            <span>View Transparent Scoring Weights</span>
            {showBreakdown ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showBreakdown && (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3 p-3 bg-slate-900/80 rounded-xl border border-slate-800 text-center">
              <div>
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Risk Match</div>
                <div className="text-sm font-bold text-slate-200 mt-0.5">
                  {candidate.score_breakdown.risk_match_score}/30
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Horizon</div>
                <div className="text-sm font-bold text-slate-200 mt-0.5">
                  {candidate.score_breakdown.horizon_match_score}/25
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Quality</div>
                <div className="text-sm font-bold text-slate-200 mt-0.5">
                  {candidate.score_breakdown.financial_quality_score}/25
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Valuation</div>
                <div className="text-sm font-bold text-slate-200 mt-0.5">
                  {candidate.score_breakdown.valuation_score}/10
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Diversification</div>
                <div className="text-sm font-bold text-slate-200 mt-0.5">
                  {candidate.score_breakdown.diversification_score}/10
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer Source Citation */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-slate-400" />
          <span>Verified Source: <strong className="text-slate-400">{candidate.source_reference}</strong></span>
        </div>
        <span className="text-[11px] text-slate-500">Not personalized financial advice</span>
      </div>
    </div>
  );
}
