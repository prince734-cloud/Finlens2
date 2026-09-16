import React, { useEffect, useState } from 'react';
import { UserCheck, Shield, Target, Clock, DollarSign, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import api from '../services/api';

export default function Profile() {
  const [investmentAmount, setInvestmentAmount] = useState(500000);
  const [monthlyAmount, setMonthlyAmount] = useState(25000);
  const [riskTolerance, setRiskTolerance] = useState('Moderate');
  const [investmentHorizon, setInvestmentHorizon] = useState('Medium');
  const [goal, setGoal] = useState('Wealth creation');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    async function loadProfile() {
      try {
        setLoading(true);
        const data = await api.getProfile();
        if (data) {
          setInvestmentAmount(data.investment_amount || 500000);
          setMonthlyAmount(data.monthly_investment_amount || 0);
          setRiskTolerance(data.risk_tolerance || 'Moderate');
          setInvestmentHorizon(data.investment_horizon || 'Medium');
          setGoal(data.goal || 'Wealth creation');
        }
      } catch (err) {
        console.warn('Could not load profile from server:', err);
      } finally {
        setLoading(false);
      }
    }
    loadProfile();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg('');
    setErrorMsg('');

    const payload = {
      investment_amount: parseFloat(investmentAmount),
      monthly_investment_amount: parseFloat(monthlyAmount) || 0,
      risk_tolerance: riskTolerance,
      investment_horizon: investmentHorizon,
      goal: goal,
    };

    try {
      await api.saveProfile(payload);
      setSuccessMsg('Investment profile saved successfully! Candidate ranking updated.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to save profile. Please check server status.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Investor Profile & Suitability Parameters
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Configure capital constraints, risk tolerance, and investment horizon for deterministic candidate matching.
        </p>
      </div>

      {loading ? (
        <div className="p-16 text-center text-slate-500 text-sm">Loading investor profile...</div>
      ) : (
        <form onSubmit={handleSubmit} className="bg-[#111827] border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-8 shadow-xl">
          {/* Capital Amounts */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                <span>Total Investment Capital (₹)</span>
              </label>
              <input
                type="number"
                min="1000"
                step="1000"
                value={investmentAmount}
                onChange={(e) => setInvestmentAmount(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white font-mono text-base focus:outline-none focus:border-emerald-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">Lump sum allocation</span>
            </div>

            <div>
              <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                <span>Monthly Recurring Investment (₹)</span>
              </label>
              <input
                type="number"
                min="0"
                step="500"
                value={monthlyAmount}
                onChange={(e) => setMonthlyAmount(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white font-mono text-base focus:outline-none focus:border-emerald-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">Optional SIP / recurring capital</span>
            </div>
          </div>

          {/* Risk Tolerance */}
          <div>
            <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3">
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>Risk Tolerance</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: 'Low', desc: 'Focus on capital preservation, debt instruments, and stable cash flows.' },
                { id: 'Moderate', desc: 'Balanced risk appetite across large-caps and established flexi-cap funds.' },
                { id: 'High', desc: 'Growth orientation, tolerance for sector volatility and mid-cap equity swings.' },
              ].map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setRiskTolerance(item.id)}
                  className={`p-4 rounded-2xl border text-left transition-all ${
                    riskTolerance === item.id
                      ? 'border-emerald-500 bg-emerald-500/10 shadow-sm'
                      : 'border-slate-800 bg-slate-900 hover:border-slate-700'
                  }`}
                >
                  <div className="font-bold text-sm text-white mb-1">{item.id} Risk</div>
                  <p className="text-xs text-slate-400 leading-relaxed">{item.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Investment Horizon */}
          <div>
            <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3">
              <Clock className="w-4 h-4 text-emerald-400" />
              <span>Investment Horizon</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: 'Short', label: 'Short Term (1 - 3 Years)' },
                { id: 'Medium', label: 'Medium Term (3 - 5 Years)' },
                { id: 'Long', label: 'Long Term (5+ Years)' },
              ].map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setInvestmentHorizon(item.id)}
                  className={`p-3.5 rounded-xl border text-center transition-all ${
                    investmentHorizon === item.id
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400 font-semibold shadow-sm'
                      : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <span className="text-xs">{item.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Investment Goal */}
          <div>
            <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3">
              <Target className="w-4 h-4 text-emerald-400" />
              <span>Primary Goal</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {['Wealth creation', 'Capital preservation', 'Income', 'Other'].map((g) => (
                <button
                  type="button"
                  key={g}
                  onClick={() => setGoal(g)}
                  className={`p-3 rounded-xl border text-center transition-all text-xs ${
                    goal === g
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400 font-semibold shadow-sm'
                      : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>

          {/* Feedback alerts */}
          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Submit Button */}
          <div className="pt-4 border-t border-slate-800 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition-all shadow-lg shadow-emerald-600/20 disabled:opacity-50"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Saving Profile...</span>
                </>
              ) : (
                <>
                  <UserCheck className="w-4 h-4" />
                  <span>Save Investment Profile</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
