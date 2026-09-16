import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles } from 'lucide-react';
import api from '../services/api';

export default function DocumentUpload({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [companyName, setCompanyName] = useState('');
  const [fiscalYear, setFiscalYear] = useState(2024);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      if (!selected.name.toLowerCase().endsWith('.pdf')) {
        setError('Please upload an annual report or 10-K PDF file.');
        setFile(null);
        return;
      }
      setFile(selected);
      setError(null);
      setSuccessMsg(null);

      // Auto-populate company name if empty
      if (!companyName) {
        const guessed = selected.name
          .replace(/\.pdf$/i, '')
          .replace(/[-_]/g, ' ')
          .replace(/annual\s*report/i, '')
          .replace(/10-?k/i, '')
          .replace(/fy\d{2,4}/i, '')
          .trim();
        if (guessed) setCompanyName(guessed);
      }
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select an annual report PDF to upload.');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', 'annual_report');
    if (companyName) formData.append('company_name', companyName);
    if (fiscalYear) formData.append('financial_year', fiscalYear);

    try {
      const result = await api.uploadDocument(formData);
      setSuccessMsg(`"${file.name}" uploaded, parsed & KPIs extracted successfully!`);
      setFile(null);
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      let errorMsg = 'Failed to upload document. Ensure backend is running.';
      if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (Array.isArray(detail)) {
        errorMsg = detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
      } else if (err.code === 'ECONNABORTED' || err.code === 'ETIMEDOUT') {
        errorMsg = 'The upload is still processing. Please wait and try again only if it does not finish within 5 minutes.';
      } else if (err.message && !err.response) {
        errorMsg = `Connection error (${err.message}). Ensure backend server is running on http://localhost:8000.`;
      }
      setError(errorMsg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Upload Annual Report</h2>
            <p className="text-xs text-slate-400">PDF documents, 10-K filings, or company earnings reports</p>
          </div>
        </div>
        <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hidden sm:inline-flex items-center gap-1">
          <Sparkles className="w-3 h-3" />
          Auto-Extract KPIs
        </span>
      </div>

      <form onSubmit={handleUpload} className="space-y-4">
        {/* Dropzone */}
        <label className="border-2 border-dashed border-slate-700 hover:border-emerald-500/60 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-900/40 group">
          <FileText className="w-9 h-9 text-slate-500 group-hover:text-emerald-400 transition-colors mb-2" />
          <span className="text-sm font-medium text-slate-200 text-center">
            {file ? (
              <span className="text-emerald-300 font-semibold">{file.name}</span>
            ) : (
              'Click to choose PDF or drag & drop here'
            )}
          </span>
          <span className="text-xs text-slate-500 mt-1">Supports corporate annual reports up to 50MB</span>
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />
        </label>

        {/* Optional Metadata Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Company Name</label>
            <input
              type="text"
              placeholder="e.g. Apple Inc. (Auto-detected if blank)"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 placeholder-slate-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Fiscal Year</label>
            <input
              type="number"
              value={fiscalYear}
              onChange={(e) => setFiscalYear(parseInt(e.target.value, 10))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={!file || uploading}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 text-white font-medium text-sm transition-all shadow-lg shadow-emerald-600/20 cursor-pointer"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              <span>Indexing Chunks & Auto-Extracting Financial KPIs...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Upload & Extract Financial KPIs</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
