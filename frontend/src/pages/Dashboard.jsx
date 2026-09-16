import React, { useEffect, useState } from 'react';
import { 
  TrendingUp, 
  FileText, 
  ShieldCheck, 
  DollarSign, 
  PieChart, 
  Bot, 
  ArrowRight,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  Building,
  Sparkles
} from 'lucide-react';
import KPICard from '../components/KPICard';
import api from '../services/api';

export default function Dashboard({ setActiveTab }) {
  const [profile, setProfile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [recommendations, setRecommendations] = useState(null);
  const [kpis, setKpis] = useState([]);
  const [selectedKpiIndex, setSelectedKpiIndex] = useState(0);
  const [_loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [profData, docsData, recsData, kpiData] = await Promise.all([
          api.getProfile().catch(() => null),
          api.getDocuments().catch(() => []),
          api.getRecommendations().catch(() => null),
          api.getAllKPIs().catch(() => []),
        ]);
        setProfile(profData);
        setDocuments(docsData || []);
        setRecommendations(recsData);
        setKpis(kpiData || []);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const activeKpi = kpis.length > 0 ? kpis[selectedKpiIndex] : null;

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
    return rate >= 0 ? `+${pct}% YoY` : `${pct}% YoY`;
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-slate-900 to-[#0e1f2b] border border-slate-800 p-6 sm:p-8 shadow-xl">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold uppercase tracking-wider mb-4">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>AI Financial Intelligence Platform</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Institutional-Grade Research & <br className="hidden sm:inline" />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 via-teal-300 to-sky-400">
              Grounded Document Intelligence
            </span>
          </h1>
          <p className="mt-3 text-sm text-slate-300 leading-relaxed max-w-2xl">
            Upload annual reports, 10-K filings, and mutual fund factsheets. Query grounded facts with 
            exact page citations, extract verified financial KPIs, and evaluate deterministic investment matches.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => setActiveTab('documents')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-all shadow-lg shadow-emerald-600/20"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Upload Document</span>
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-sm transition-all"
            >
              <Bot className="w-4 h-4 text-emerald-400" />
              <span>Ask AI Analyst</span>
            </button>
          </div>
        </div>
      </div>

      {/* Primary KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Uploaded Documents"
          value={String(documents.length)}
          subtitle={`${kpis.length} Reports with Extracted KPIs`}
          icon={FileText}
        />
        <KPICard
          title="Active Investment Capital"
          value={profile ? `₹${profile.investment_amount?.toLocaleString()}` : '₹500,000'}
          change="+₹25,000/mo"
          subtitle="Profile Capital Allocation"
          icon={DollarSign}
        />
        <KPICard
          title="Assigned Risk Profile"
          value={profile ? profile.risk_tolerance : 'Moderate'}
          subtitle={profile ? `${profile.investment_horizon} Horizon` : 'Medium (3-5y)'}
          icon={PieChart}
        />
        <KPICard
          title="Top Candidate Match"
          value={recommendations?.candidates?.[0] ? `${Math.round(recommendations.candidates[0].match_score)}%` : '88%'}
          subtitle="Deterministic Multi-factor Score"
          icon={TrendingUp}
        />
      </div>

      {/* Structured Financial KPIs Section */}
      {activeKpi ? (
        <div className="bg-[#111827] border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
          {/* Section Header with Company Selector */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Building className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-white tracking-tight">{activeKpi.company_name}</h2>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-emerald-400 font-mono font-medium border border-slate-700">
                    FY {activeKpi.financial_year}
                  </span>
                </div>
                <p className="text-xs text-slate-400">Verified Financial Key Performance Indicators (PostgreSQL)</p>
              </div>
            </div>

            {/* Dropdown if multiple company reports have extracted KPIs */}
            {kpis.length > 1 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Company:</span>
                <select
                  value={selectedKpiIndex}
                  onChange={(e) => setSelectedKpiIndex(parseInt(e.target.value, 10))}
                  className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                >
                  {kpis.map((item, idx) => (
                    <option key={item.id} value={idx}>
                      {item.company_name} ({item.financial_year})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* KPI Metrics 6-Box Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <KPICard
              title="Consolidated Revenue"
              value={formatCurrency(activeKpi.revenue, activeKpi.currency)}
              change={formatGrowth(activeKpi.revenue_growth)}
              isPositive={activeKpi.revenue_growth >= 0}
              subtitle="Total Net Sales"
              icon={DollarSign}
            />
            <KPICard
              title="Net Income"
              value={formatCurrency(activeKpi.net_income, activeKpi.currency)}
              change={formatGrowth(activeKpi.net_income_growth)}
              isPositive={activeKpi.net_income_growth >= 0}
              subtitle="Profit After Tax"
              icon={TrendingUp}
            />
            <KPICard
              title="Operating Cash Flow"
              value={formatCurrency(activeKpi.operating_cash_flow, activeKpi.currency)}
              subtitle="Cash Provided by Operations"
              icon={TrendingUp}
            />
            <KPICard
              title="Operating Income (EBIT)"
              value={formatCurrency(activeKpi.operating_income, activeKpi.currency)}
              subtitle="Core Operating Profit"
              icon={DollarSign}
            />
            <KPICard
              title="Total Assets"
              value={formatCurrency(activeKpi.total_assets, activeKpi.currency)}
              subtitle="Consolidated Balance Sheet"
              icon={Building}
            />
            <KPICard
              title="Total Liabilities"
              value={formatCurrency(activeKpi.total_liabilities, activeKpi.currency)}
              subtitle="Total Balance Sheet Obligations"
              icon={Building}
            />
          </div>

          {/* Growth Drivers & Risk Factors */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            {/* Growth Drivers */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-3">
                <CheckCircle2 className="w-4 h-4" />
                <span>Extracted Growth Drivers</span>
              </div>
              {activeKpi.growth_drivers && activeKpi.growth_drivers.length > 0 ? (
                <ul className="space-y-2">
                  {activeKpi.growth_drivers.map((driver, idx) => (
                    <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-emerald-400 font-bold">✓</span>
                      <span>{driver}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">No specific growth drivers extracted.</p>
              )}
            </div>

            {/* Risk Factors */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-3">
                <AlertTriangle className="w-4 h-4" />
                <span>Major Risk Factors (Item 1A)</span>
              </div>
              {activeKpi.risk_factors && activeKpi.risk_factors.length > 0 ? (
                <ul className="space-y-2">
                  {activeKpi.risk_factors.map((risk, idx) => (
                    <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-amber-400 font-bold">⚠</span>
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
      ) : (
        /* Empty State Prompt if no KPIs extracted yet */
        <div className="bg-[#111827] border border-dashed border-slate-800 rounded-3xl p-8 text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-white">No Extracted Financial KPIs Yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Upload an annual report or 10-K filing in the Documents vault and click <strong className="text-emerald-400">"Extract KPIs"</strong> to extract verified financial metrics, growth drivers, and risk factors.
          </p>
          <button
            onClick={() => setActiveTab('documents')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition-colors"
          >
            <FileText className="w-4 h-4 text-emerald-400" />
            <span>Go to Documents Vault</span>
          </button>
        </div>
      )}

      {/* Two Column Section: Profile Summary & Recent Candidates */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Investment Profile Snapshot */}
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
            <h2 className="text-base font-bold text-white">Investment Profile</h2>
            <button
              onClick={() => setActiveTab('profile')}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1"
            >
              <span>Edit</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-4 text-sm">
            <div className="flex items-center justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">Total Capital</span>
              <span className="font-semibold text-white">
                {profile ? `₹${profile.investment_amount.toLocaleString()}` : '₹500,000'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">Risk Tolerance</span>
              <span className="font-semibold text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs">
                {profile ? profile.risk_tolerance : 'Moderate'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">Time Horizon</span>
              <span className="font-semibold text-white">
                {profile ? profile.investment_horizon : 'Medium (3-5 Years)'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-slate-400">Primary Goal</span>
              <span className="font-semibold text-white">
                {profile ? profile.goal : 'Wealth creation'}
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Top Candidate Matches Preview */}
        <div className="lg:col-span-2 bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
            <div>
              <h2 className="text-base font-bold text-white">Top Investment Matches</h2>
              <p className="text-xs text-slate-400">Calculated via multi-factor quantitative ranking</p>
            </div>
            <button
              onClick={() => setActiveTab('recommendations')}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {recommendations?.candidates?.length > 0 ? (
            <div className="space-y-3">
              {recommendations.candidates.map((cand) => (
                <div
                  key={cand.id}
                  className="bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-400 uppercase">{cand.asset_type}</span>
                      <span className="text-xs font-mono text-slate-500">• {cand.symbol_or_code}</span>
                    </div>
                    <h4 className="text-base font-bold text-white mt-0.5">{cand.asset_name}</h4>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-1">
                      {cand.positive_factors[0]}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <div className="text-right">
                      <div className="text-xs text-slate-400">Score</div>
                      <div className="text-lg font-bold text-emerald-400">
                        {Math.round(cand.match_score)}/100
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-10 text-slate-500 text-sm">
              No matching candidates loaded yet. Configure profile or upload reports.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
