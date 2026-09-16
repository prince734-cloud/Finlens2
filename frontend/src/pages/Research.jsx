import React, { useEffect, useState } from 'react';
import { 
  Building2, 
  Layers, 
  ShieldCheck, 
  Search, 
  Filter, 
  TrendingUp, 
  DollarSign, 
  PieChart, 
  RefreshCw, 
  X, 
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import api from '../services/api';

export default function Research() {
  const [activeTab, setActiveTab] = useState('companies');
  const [companies, setCompanies] = useState([]);
  const [mutualFunds, setMutualFunds] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSector, setSelectedSector] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedRisk, setSelectedRisk] = useState('All');

  // Selected modals
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [selectedFund, setSelectedFund] = useState(null);

  const fetchResearchData = async () => {
    try {
      setLoading(true);
      const [compData, fundData] = await Promise.all([
        api.getCompanies().catch(() => []),
        api.getMutualFunds().catch(() => []),
      ]);
      setCompanies(compData || []);
      setMutualFunds(fundData || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResearchData();
  }, []);

  const formatCurrency = (val) => {
    if (val === null || val === undefined) return '—';
    const abs = Math.abs(val);
    if (abs >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
    if (abs >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
    return `$${val.toLocaleString()}`;
  };

  const formatPercent = (val) => {
    if (val === null || val === undefined) return '—';
    const pct = (val * 100).toFixed(1);
    return `${pct}%`;
  };

  // Filter companies
  const filteredCompanies = companies.filter((c) => {
    const matchesSearch = 
      c.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSector = selectedSector === 'All' || c.sector.toLowerCase().includes(selectedSector.toLowerCase());
    return matchesSearch && matchesSector;
  });

  // Filter mutual funds
  const filteredFunds = mutualFunds.filter((f) => {
    const matchesSearch = f.fund_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || f.category.toLowerCase().includes(selectedCategory.toLowerCase());
    const fundRisk = f.metrics?.[0]?.risk_level || 'Moderate';
    const matchesRisk = selectedRisk === 'All' || fundRisk.toLowerCase() === selectedRisk.toLowerCase();
    return matchesSearch && matchesCategory && matchesRisk;
  });

  const uniqueSectors = ['All', ...new Set(companies.map((c) => c.sector))];
  const uniqueCategories = ['All', ...new Set(mutualFunds.map((f) => f.category))];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Financial Research Data Layer
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Audited fundamental metrics for companies and factsheet performance for mutual funds.
          </p>
        </div>

        {/* Tab Buttons & Refresh */}
        <div className="flex items-center gap-3 self-start sm:self-auto">
          <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-xl">
            <button
              onClick={() => { setActiveTab('companies'); setSearchQuery(''); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'companies'
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Building2 className="w-4 h-4" />
              <span>Companies ({companies.length})</span>
            </button>
            <button
              onClick={() => { setActiveTab('mutualFunds'); setSearchQuery(''); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'mutualFunds'
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Mutual Funds ({mutualFunds.length})</span>
            </button>
          </div>

          <button
            onClick={fetchResearchData}
            className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Refresh Research Data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Grounding Guarantee Notice */}
      <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center gap-3 text-xs text-slate-400">
        <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0" />
        <span>
          <strong>Grounded Data Guarantee:</strong> All financial metrics originate from verified stored database records.
          Generative AI models are strictly prohibited from inventing financial figures, return rates, or balance sheet amounts.
        </span>
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-[#111827] border border-slate-800 p-4 rounded-2xl">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder={activeTab === 'companies' ? "Search company by ticker or name (e.g. AAPL, Apple)..." : "Search fund by name (e.g. Parag Parikh, Large Cap)..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>

        {activeTab === 'companies' ? (
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <select
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 w-full sm:w-auto"
            >
              {uniqueSectors.map((s) => (
                <option key={s} value={s}>{s === 'All' ? 'All Sectors' : s}</option>
              ))}
            </select>
          </div>
        ) : (
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              {uniqueCategories.map((c) => (
                <option key={c} value={c}>{c === 'All' ? 'All Categories' : c}</option>
              ))}
            </select>
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="All">All Risks</option>
              <option value="Low">Low Risk</option>
              <option value="Moderate">Moderate Risk</option>
              <option value="High">High Risk</option>
            </select>
          </div>
        )}
      </div>

      {/* Companies Table */}
      {activeTab === 'companies' && (
        <div className="bg-[#111827] border border-slate-800 rounded-3xl overflow-hidden shadow-md">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-bold text-white">Tracked Equities & Fundamental Metrics</h2>
            </div>
            <span className="text-xs text-slate-400">{filteredCompanies.length} matching equities</span>
          </div>

          {loading ? (
            <div className="p-16 text-center text-slate-500 text-sm">Loading company fundamentals...</div>
          ) : filteredCompanies.length === 0 ? (
            <div className="p-16 text-center text-slate-500 text-sm">No companies found matching search filters.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[11px] font-semibold tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="px-5 py-3.5">Company / Ticker</th>
                    <th className="px-5 py-3.5">Sector</th>
                    <th className="px-5 py-3.5">Market Cap</th>
                    <th className="px-5 py-3.5">Revenue</th>
                    <th className="px-5 py-3.5">YoY Growth</th>
                    <th className="px-5 py-3.5">Net Profit</th>
                    <th className="px-5 py-3.5">ROE</th>
                    <th className="px-5 py-3.5">ROCE</th>
                    <th className="px-5 py-3.5">Debt/Equity</th>
                    <th className="px-5 py-3.5">P/E</th>
                    <th className="px-5 py-3.5 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300">
                  {filteredCompanies.map((c) => {
                    const m = c.metrics?.[0] || {};
                    return (
                      <tr key={c.id} className="hover:bg-slate-900/50 transition-colors">
                        <td className="px-5 py-3.5 font-medium text-white">
                          <div className="font-semibold">{c.name}</div>
                          <div className="text-[11px] font-mono text-emerald-400">{c.symbol}</div>
                        </td>
                        <td className="px-5 py-3.5 text-slate-400">{c.sector}</td>
                        <td className="px-5 py-3.5 font-mono text-slate-200">{formatCurrency(m.market_cap)}</td>
                        <td className="px-5 py-3.5 font-mono text-white">{formatCurrency(m.revenue)}</td>
                        <td className="px-5 py-3.5 font-mono">
                          {m.revenue_growth !== null && m.revenue_growth !== undefined ? (
                            <span className={m.revenue_growth >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {(m.revenue_growth * 100).toFixed(1)}%
                            </span>
                          ) : '—'}
                        </td>
                        <td className="px-5 py-3.5 font-mono text-emerald-400">{formatCurrency(m.net_profit)}</td>
                        <td className="px-5 py-3.5 font-mono text-slate-300">{formatPercent(m.roe)}</td>
                        <td className="px-5 py-3.5 font-mono text-slate-300">{formatPercent(m.roce)}</td>
                        <td className="px-5 py-3.5 font-mono text-slate-300">{m.debt_to_equity ? m.debt_to_equity.toFixed(2) : '—'}</td>
                        <td className="px-5 py-3.5 font-mono text-sky-400 font-semibold">{m.pe_ratio ? m.pe_ratio.toFixed(1) : '—'}</td>
                        <td className="px-5 py-3.5 text-right">
                          <button
                            onClick={() => setSelectedCompany(c)}
                            className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition-colors"
                            title="View Full Fundamentals"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Mutual Funds Table */}
      {activeTab === 'mutualFunds' && (
        <div className="bg-[#111827] border border-slate-800 rounded-3xl overflow-hidden shadow-md">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-bold text-white">Tracked Mutual Funds & Performance Factsheets</h2>
            </div>
            <span className="text-xs text-slate-400">{filteredFunds.length} matching funds</span>
          </div>

          {loading ? (
            <div className="p-16 text-center text-slate-500 text-sm">Loading mutual fund metrics...</div>
          ) : filteredFunds.length === 0 ? (
            <div className="p-16 text-center text-slate-500 text-sm">No mutual funds found matching filters.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[11px] font-semibold tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="px-5 py-3.5">Fund Name</th>
                    <th className="px-5 py-3.5">Category</th>
                    <th className="px-5 py-3.5">Benchmark</th>
                    <th className="px-5 py-3.5">AUM</th>
                    <th className="px-5 py-3.5">Expense Ratio</th>
                    <th className="px-5 py-3.5">Risk Level</th>
                    <th className="px-5 py-3.5">3Y CAGR</th>
                    <th className="px-5 py-3.5">5Y CAGR</th>
                    <th className="px-5 py-3.5">Top Holdings</th>
                    <th className="px-5 py-3.5 text-right">Factsheet</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300">
                  {filteredFunds.map((f) => {
                    const m = f.metrics?.[0] || {};
                    const holdingsCount = m.portfolio_holdings?.length || 0;
                    return (
                      <tr key={f.id} className="hover:bg-slate-900/50 transition-colors">
                        <td className="px-5 py-3.5 font-medium text-white">
                          <div className="font-semibold">{f.fund_name}</div>
                          {f.fund_manager && <div className="text-[11px] text-slate-500">Mgr: {f.fund_manager}</div>}
                        </td>
                        <td className="px-5 py-3.5 text-slate-400">{f.category}</td>
                        <td className="px-5 py-3.5 text-slate-400">{f.benchmark}</td>
                        <td className="px-5 py-3.5 font-mono text-white">
                          {m.aum ? `₹${(m.aum / 1e7).toFixed(0)} Cr` : '—'}
                        </td>
                        <td className="px-5 py-3.5 font-mono text-slate-300">
                          {m.expense_ratio ? `${(m.expense_ratio * 100).toFixed(2)}%` : '—'}
                        </td>
                        <td className="px-5 py-3.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-semibold ${
                            m.risk_level === 'Low' ? 'bg-emerald-500/10 text-emerald-400' :
                            m.risk_level === 'Moderate' ? 'bg-sky-500/10 text-sky-400' :
                            'bg-amber-500/10 text-amber-400'
                          }`}>
                            {m.risk_level || 'Moderate'}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 font-mono text-emerald-400 font-semibold">
                          {m.return_3yr ? `${m.return_3yr.toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-5 py-3.5 font-mono text-emerald-400 font-semibold">
                          {m.return_5yr ? `${m.return_5yr.toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-5 py-3.5">
                          <button
                            onClick={() => setSelectedFund(f)}
                            className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300"
                          >
                            <span>{holdingsCount} stocks</span>
                            <ChevronRight className="w-3 h-3" />
                          </button>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <button
                            onClick={() => setSelectedFund(f)}
                            className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition-colors"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Company Detail Modal */}
      {selectedCompany && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-slate-800 rounded-3xl max-w-2xl w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold text-white">{selectedCompany.name}</h3>
                  <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                    {selectedCompany.symbol}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">{selectedCompany.sector} • {selectedCompany.industry}</p>
              </div>
              <button
                onClick={() => setSelectedCompany(null)}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {selectedCompany.description && (
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
                {selectedCompany.description}
              </p>
            )}

            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Historical Fiscal Metrics</h4>
              <div className="space-y-2">
                {selectedCompany.metrics.map((m) => (
                  <div key={m.fiscal_year} className="bg-slate-900 p-4 rounded-2xl border border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div>
                      <span className="text-[10px] text-slate-500 block">Fiscal Year</span>
                      <span className="font-bold text-white">FY {m.fiscal_year}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Revenue</span>
                      <span className="font-mono text-emerald-400 font-bold">{formatCurrency(m.revenue)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Net Profit</span>
                      <span className="font-mono text-emerald-400 font-bold">{formatCurrency(m.net_profit)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Operating Cash Flow</span>
                      <span className="font-mono text-slate-200">{formatCurrency(m.operating_cash_flow)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">ROE</span>
                      <span className="font-mono text-slate-200">{formatPercent(m.roe)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">ROCE</span>
                      <span className="font-mono text-slate-200">{formatPercent(m.roce)}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Debt to Equity</span>
                      <span className="font-mono text-slate-200">{m.debt_to_equity ? m.debt_to_equity.toFixed(2) : '—'}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">P/E Ratio</span>
                      <span className="font-mono text-sky-400 font-bold">{m.pe_ratio ? m.pe_ratio.toFixed(1) : '—'}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setSelectedCompany(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mutual Fund Detail Modal */}
      {selectedFund && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-slate-800 rounded-3xl max-w-2xl w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedFund.fund_name}</h3>
                <p className="text-xs text-slate-400 mt-1">{selectedFund.category} • Benchmark: {selectedFund.benchmark}</p>
              </div>
              <button
                onClick={() => setSelectedFund(null)}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Fund Facts */}
            {selectedFund.metrics?.[0] && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-900 p-4 rounded-2xl border border-slate-800 text-xs">
                <div>
                  <span className="text-[10px] text-slate-500 block">Total AUM</span>
                  <span className="font-bold text-white font-mono">₹{(selectedFund.metrics[0].aum / 1e7).toFixed(0)} Cr</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Expense Ratio</span>
                  <span className="font-bold text-white font-mono">{(selectedFund.metrics[0].expense_ratio * 100).toFixed(2)}%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">3Y CAGR</span>
                  <span className="font-bold text-emerald-400 font-mono">{selectedFund.metrics[0].return_3yr}%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">5Y CAGR</span>
                  <span className="font-bold text-emerald-400 font-mono">{selectedFund.metrics[0].return_5yr}%</span>
                </div>
              </div>
            )}

            {/* Exit Load */}
            {selectedFund.metrics?.[0]?.exit_load && (
              <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 text-xs text-slate-300">
                <span className="text-slate-500 font-semibold block mb-0.5">Exit Load Structure:</span>
                {selectedFund.metrics[0].exit_load}
              </div>
            )}

            {/* Top Holdings Table */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Top Portfolio Holdings</h4>
              <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 text-[10px] uppercase font-semibold">
                    <tr>
                      <th className="px-4 py-2">Holding Name</th>
                      <th className="px-4 py-2">Sector</th>
                      <th className="px-4 py-2 text-right">Weight</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {selectedFund.metrics?.[0]?.portfolio_holdings?.map((h, i) => (
                      <tr key={i} className="hover:bg-slate-800/40">
                        <td className="px-4 py-2.5 font-medium text-white">{h.name}</td>
                        <td className="px-4 py-2.5 text-slate-400">{h.sector}</td>
                        <td className="px-4 py-2.5 font-mono text-emerald-400 font-bold text-right">{h.weight}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setSelectedFund(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
