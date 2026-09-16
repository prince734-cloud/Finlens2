import React, { useEffect, useState } from 'react';
import { 
  FileText, 
  Trash2, 
  CheckCircle2, 
  Layers, 
  Sparkles, 
  Eye, 
  Loader2, 
  AlertCircle,
  MessageSquare,
  DollarSign,
  TrendingUp,
  Building,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import DocumentUpload from '../components/DocumentUpload';
import api from '../services/api';

export default function Documents({ onAskQuestion }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [activeKPI, setActiveKPI] = useState(null);
  const [loadingKPI, setLoadingKPI] = useState(false);
  const [extractingId, setExtractingId] = useState(null);
  const [actionError, setActionError] = useState(null);

  const fetchDocuments = async (autoSelectNewDocId = null) => {
    try {
      setLoading(true);
      const data = await api.getDocuments();
      const docList = data || [];
      setDocuments(docList);

      const targetId = autoSelectNewDocId || selectedDocId || (docList.length > 0 ? docList[0].id : null);
      if (targetId) {
        setSelectedDocId(targetId);
        loadKPIForDoc(targetId);
      } else {
        setActiveKPI(null);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadKPIForDoc = async (docId) => {
    if (!docId) return;
    setLoadingKPI(true);
    try {
      const kpiData = await api.getKPIs(docId);
      setActiveKPI(kpiData);
    } catch (err) {
      // Document might not have extracted KPIs yet
      setActiveKPI(null);
    } finally {
      setLoadingKPI(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleSelectDoc = (docId) => {
    setSelectedDocId(docId);
    loadKPIForDoc(docId);
  };

  const handleUploadComplete = async (uploadedResult) => {
    const newDocId = uploadedResult?.id;
    if (uploadedResult?.kpi) {
      setActiveKPI({
        ...uploadedResult.kpi,
        company_name: uploadedResult.kpi.company || uploadedResult.company_name,
        document_id: newDocId
      });
      setSelectedDocId(newDocId);
    }
    await fetchDocuments(newDocId);
  };

  const handleExtractKPIs = async (docId) => {
    setExtractingId(docId);
    setActionError(null);
    try {
      const result = await api.extractKPIs(docId);
      if (result && result.kpi) {
        setActiveKPI({
          ...result.kpi,
          company_name: result.kpi.company || 'Unknown',
          document_id: docId
        });
        setSelectedDocId(docId);
      }
      await fetchDocuments(docId);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to extract KPIs. Ensure backend is running.';
      setActionError(msg);
    } finally {
      setExtractingId(null);
    }
  };

  const handleDelete = async (docId) => {
    if (window.confirm('Are you sure you want to delete this report and its vector index?')) {
      try {
        await api.deleteDocument(docId);
        if (selectedDocId === docId) {
          setSelectedDocId(null);
          setActiveKPI(null);
        }
        await fetchDocuments();
      } catch (err) {
        alert('Failed to delete document.');
      }
    }
  };

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

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const activeDoc = documents.find((d) => d.id === selectedDocId);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Title */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Annual Reports & Financial KPIs
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Upload corporate annual reports, view automatically extracted financial KPIs directly on the screen, and ask grounded questions.
        </p>
      </div>

      {actionError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Upload Component */}
      <DocumentUpload onUploadSuccess={handleUploadComplete} />

      {/* Prominent Extracted KPIs Section (Rendered directly on screen) */}
      {activeDoc && (
        <div className="bg-[#111827] border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
          {/* Header of Extracted KPI Card */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
                <Building className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    {activeKPI?.company_name || activeDoc.company_name || activeDoc.filename}
                  </h2>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-emerald-400 font-mono font-medium border border-slate-700">
                    FY {activeKPI?.financial_year || activeDoc.financial_year || 2024}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-500" />
                  <span className="truncate max-w-sm">{activeDoc.filename}</span>
                  <span>•</span>
                  <span>{activeDoc.chunk_count} indexed chunks</span>
                </p>
              </div>
            </div>

            {/* Direct Option to Ask Questions from this Report */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => onAskQuestion && onAskQuestion(activeDoc)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-sm transition-all shadow-lg shadow-emerald-600/25 cursor-pointer hover:scale-[1.02]"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Ask Questions from this Report</span>
              </button>
            </div>
          </div>

          {/* Extracted KPI Metrics Grid */}
          {loadingKPI ? (
            <div className="py-12 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Loading extracted financial metrics...</span>
            </div>
          ) : activeKPI ? (
            <div className="space-y-6">
              {/* 6 Metric Cards Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Revenue */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Consolidated Revenue</span>
                    <DollarSign className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-white tracking-tight">
                      {formatCurrency(activeKPI.revenue, activeKPI.currency)}
                    </span>
                    {activeKPI.revenue_growth !== null && activeKPI.revenue_growth !== undefined && (
                      <span className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-md ${
                        activeKPI.revenue_growth >= 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {activeKPI.revenue_growth >= 0 ? <ArrowUpRight className="w-3 h-3 mr-0.5" /> : <ArrowDownRight className="w-3 h-3 mr-0.5" />}
                        {formatGrowth(activeKPI.revenue_growth)}
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Total Net Sales & Operating Turnover</p>
                </div>

                {/* Net Income */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Net Income (Profit)</span>
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-white tracking-tight">
                      {formatCurrency(activeKPI.net_income, activeKPI.currency)}
                    </span>
                    {activeKPI.net_income_growth !== null && activeKPI.net_income_growth !== undefined && (
                      <span className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-md ${
                        activeKPI.net_income_growth >= 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {activeKPI.net_income_growth >= 0 ? <ArrowUpRight className="w-3 h-3 mr-0.5" /> : <ArrowDownRight className="w-3 h-3 mr-0.5" />}
                        {formatGrowth(activeKPI.net_income_growth)}
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Net Profit After Tax</p>
                </div>

                {/* Operating Income / EBIT */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Operating Profit (EBIT)</span>
                    <DollarSign className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-white tracking-tight">
                      {formatCurrency(activeKPI.operating_income, activeKPI.currency)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Core Operating Profitability</p>
                </div>

                {/* Operating Cash Flow */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Operating Cash Flow</span>
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-white tracking-tight">
                      {formatCurrency(activeKPI.operating_cash_flow, activeKPI.currency)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Cash Provided by Operating Activities</p>
                </div>

                {/* Total Assets */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Total Assets</span>
                    <Building className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-white tracking-tight">
                      {formatCurrency(activeKPI.total_assets, activeKPI.currency)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Consolidated Balance Sheet Assets</p>
                </div>

                {/* Total Liabilities */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 hover:border-slate-700 transition-colors">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Total Liabilities</span>
                    <Building className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-white tracking-tight">
                      {formatCurrency(activeKPI.total_liabilities, activeKPI.currency)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Total Obligations & Debt</p>
                </div>
              </div>

              {/* Growth Drivers & Risk Factors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                {/* Growth Drivers */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
                  <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-3">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Extracted Strategic Growth Drivers</span>
                  </div>
                  {activeKPI.growth_drivers && activeKPI.growth_drivers.length > 0 ? (
                    <ul className="space-y-2">
                      {activeKPI.growth_drivers.map((driver, idx) => (
                        <li key={idx} className="text-xs text-slate-300 flex items-start gap-2 leading-relaxed">
                          <span className="text-emerald-400 font-bold mt-0.5">✓</span>
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
                    <span>Disclosed Risk Factors (Item 1A)</span>
                  </div>
                  {activeKPI.risk_factors && activeKPI.risk_factors.length > 0 ? (
                    <ul className="space-y-2">
                      {activeKPI.risk_factors.map((risk, idx) => (
                        <li key={idx} className="text-xs text-slate-300 flex items-start gap-2 leading-relaxed">
                          <span className="text-amber-400 font-bold mt-0.5">⚠</span>
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
            /* Document has not had KPIs extracted yet */
            <div className="bg-slate-900/50 border border-dashed border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <Sparkles className="w-8 h-8 text-emerald-400 mx-auto" />
              <h3 className="text-base font-bold text-white">KPIs Not Extracted Yet for this Document</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Extract Revenue, Net Income, Operating Cash Flow, Assets, Liabilities, Growth Drivers, and Risk Factors with CFA-level AI accuracy.
              </p>
              <button
                onClick={() => handleExtractKPIs(activeDoc.id)}
                disabled={extractingId === activeDoc.id}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all disabled:opacity-50 cursor-pointer shadow-lg shadow-emerald-600/20"
              >
                {extractingId === activeDoc.id ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Extracting Financial KPIs...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Extract Financial KPIs</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Document Repository Table */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2 text-white font-semibold text-sm">
            <Layers className="w-4 h-4 text-emerald-400" />
            <span>Uploaded Reports Repository ({documents.length})</span>
          </div>
          <button
            onClick={() => fetchDocuments()}
            className="text-xs text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 text-sm">Loading reports repository...</div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No annual reports uploaded yet. Upload a PDF above to begin automatic extraction and Q&A.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[11px] font-semibold tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3">Report Name</th>
                  <th className="px-5 py-3">Fiscal Year</th>
                  <th className="px-5 py-3">Size</th>
                  <th className="px-5 py-3">Chunks</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                {documents.map((doc) => {
                  const isSelected = doc.id === selectedDocId;
                  return (
                    <tr
                      key={doc.id}
                      onClick={() => handleSelectDoc(doc.id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? 'bg-emerald-500/10' : 'hover:bg-slate-900/40'
                      }`}
                    >
                      <td className="px-5 py-3.5 font-medium text-white flex items-center gap-2">
                        <FileText className={`w-4 h-4 flex-shrink-0 ${isSelected ? 'text-emerald-400' : 'text-slate-400'}`} />
                        <div>
                          <div className="truncate max-w-xs font-semibold">{doc.company_name || doc.filename}</div>
                          <div className="text-[11px] text-slate-500 truncate max-w-xs">{doc.filename}</div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-slate-300">
                        {doc.financial_year ? `FY${doc.financial_year}` : '—'}
                      </td>
                      <td className="px-5 py-3.5 text-slate-400">{formatBytes(doc.file_size_bytes)}</td>
                      <td className="px-5 py-3.5 font-mono text-emerald-400 font-medium">
                        {doc.chunk_count}
                      </td>
                      <td className="px-5 py-3.5">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-3 h-3" />
                          <span className="capitalize">{doc.status}</span>
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-2">
                          {/* Ask Questions directly from this report */}
                          <button
                            onClick={() => onAskQuestion && onAskQuestion(doc)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all shadow-sm cursor-pointer"
                            title="Ask questions grounded in this report"
                          >
                            <MessageSquare className="w-3.5 h-3.5" />
                            <span>Ask Questions</span>
                          </button>

                          {/* View Extracted KPIs */}
                          <button
                            onClick={() => handleSelectDoc(doc.id)}
                            className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                              isSelected
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                            }`}
                            title="View Extracted KPIs on Screen"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>{isSelected ? 'Viewing' : 'View KPIs'}</span>
                          </button>

                          {/* Delete Document */}
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors cursor-pointer"
                            title="Delete document"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
