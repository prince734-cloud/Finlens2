import React, { useEffect, useState } from 'react';
import { ShieldAlert, Sparkles, RefreshCw, SlidersHorizontal, Building2, Layers, CheckCircle } from 'lucide-react';
import RecommendationCard from '../components/RecommendationCard';
import api from '../services/api';

export default function Recommendations({ setActiveTab }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [assetFilter, setAssetFilter] = useState('All');
  const [simulating, setSimulating] = useState(false);
  const [showSimulator, setShowSimulator] = useState(false);

  // Simulation parameters
  const [simRisk, setSimRisk] = useState('Moderate');
  const [simHorizon, setSimHorizon] = useState('Medium');
  const [simGoal, setSimGoal] = useState('Wealth creation');

  const fetchRecommendations = async (filter = assetFilter) => {
    try {
      setLoading(true);
      const params = filter !== 'All' ? { asset_type: filter } : {};
      const res = await api.getRecommendations(params);
      setData(res);
      if (res?.user_risk_tolerance) setSimRisk(res.user_risk_tolerance);
      if (res?.user_investment_horizon) setSimHorizon(res.user_investment_horizon);
      if (res?.user_goal) setSimGoal(res.user_goal);
    } catch (err) {
      console.error('Failed to load recommendations:', err);
    } finally {
      setLoading(false);
    }
  };

  const runSimulation = async () => {
    try {
      setSimulating(true);
      const res = await api.evaluateRecommendations({
        risk_tolerance: simRisk,
        investment_horizon: simHorizon,
        goal: simGoal,
        asset_type_filter: assetFilter !== 'All' ? assetFilter : null,
      });
      setData(res);
    } catch (err) {
      console.error('Failed to run simulation:', err);
    } finally {
      setSimulating(false);
    }
  };

  useEffect(() => {
    fetchRecommendations(assetFilter);
  }, [assetFilter]);

  const candidates = data?.candidates || [];
  const avgScore =
    candidates.length > 0
      ? Math.round(candidates.reduce((acc, c) => acc + c.match_score, 0) / candidates.length)
      : 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Page Title & Profile Context */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Deterministic Ranking Engine</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Research-Based Candidate Matches
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Ranked through quantitative suitability scoring, risk filtering, and financial quality analysis.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSimulator(!showSimulator)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl border text-xs font-medium transition-colors ${
              showSimulator
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                : 'bg-slate-900 border-slate-700 hover:border-slate-600 text-slate-300'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-emerald-400" />
            <span>{showSimulator ? 'Close Simulator' : 'What-If Simulator'}</span>
          </button>
          <button
            onClick={() => fetchRecommendations(assetFilter)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 hover:border-slate-600 text-xs font-medium text-slate-300 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setActiveTab('profile')}
            className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-medium text-white transition-colors"
          >
            Adjust Saved Profile
          </button>
        </div>
      </div>

      {/* Simulator Bar (Collapsible) */}
      {showSimulator && (
        <div className="bg-slate-900/90 border border-emerald-500/30 rounded-2xl p-5 space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
              <SlidersHorizontal className="w-4 h-4" />
              <span>Interactive Scenario Simulator (What-If Analysis)</span>
            </div>
            <span className="text-[11px] text-slate-400">Tests ranking without saving to database</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">Simulated Risk Appetite</label>
              <select
                value={simRisk}
                onChange={(e) => setSimRisk(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="Conservative">Conservative (Capital preservation priority)</option>
                <option value="Moderate">Moderate (Balanced risk & return)</option>
                <option value="Aggressive">Aggressive (Maximum growth orientation)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">Simulated Horizon</label>
              <select
                value={simHorizon}
                onChange={(e) => setSimHorizon(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="Short">Short Horizon (&lt; 1 year)</option>
                <option value="Medium">Medium Horizon (1 - 5 years)</option>
                <option value="Long">Long Horizon (5+ years)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">Target Objective</label>
              <select
                value={simGoal}
                onChange={(e) => setSimGoal(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="Wealth creation">Wealth creation</option>
                <option value="Capital preservation">Capital preservation</option>
                <option value="Income">Income & Dividends</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={runSimulation}
              disabled={simulating}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {simulating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              <span>Simulate Scenario Matches</span>
            </button>
          </div>
        </div>
      )}

      {/* Active Profile & Metrics Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">Applied Risk Tier</span>
          <span className="text-sm font-bold text-white flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            {data?.user_risk_tolerance || 'Moderate'}
          </span>
        </div>
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">Applied Time Horizon</span>
          <span className="text-sm font-bold text-slate-200">
            {data?.user_investment_horizon || 'Medium'} Horizon
          </span>
        </div>
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">Matching Candidates</span>
          <span className="text-sm font-bold text-white">{candidates.length} Assets Screened</span>
        </div>
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">Average Match Score</span>
          <span className="text-sm font-bold text-emerald-400">{avgScore} / 100</span>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        {[
          { label: 'All Assets', value: 'All', icon: Layers },
          { label: 'Companies Only', value: 'Company', icon: Building2 },
          { label: 'Mutual Funds Only', value: 'Mutual Fund', icon: CheckCircle },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = assetFilter === tab.value;
          return (
            <button
              key={tab.value}
              onClick={() => setAssetFilter(tab.value)}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Compliance Disclaimer Callout */}
      <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-3">
        <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold">Important Disclaimer:</strong> {data?.disclaimer || "Matches represent algorithmically filtered candidates based on your input parameters. This platform does not provide individualized fiduciary investment advice, nor does it guarantee capital preservation or future yields."}
        </div>
      </div>

      {/* Candidates List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-16 text-center text-slate-500 text-sm">
            Evaluating candidate universe against user risk criteria...
          </div>
        ) : candidates.length > 0 ? (
          candidates.map((candidate) => (
            <RecommendationCard key={candidate.id} candidate={candidate} />
          ))
        ) : (
          <div className="p-16 text-center text-slate-500 text-sm bg-slate-900/40 rounded-2xl border border-slate-800">
            No candidates matched the current profile constraints. Try broadening your investment horizon or risk tolerance in the Simulator above.
          </div>
        )}
      </div>
    </div>
  );
}
