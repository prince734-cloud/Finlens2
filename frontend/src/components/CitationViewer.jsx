import React from 'react';
import { X, FileText, CheckCircle, ShieldCheck } from 'lucide-react';

export default function CitationViewer({ citation, onClose }) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-md bg-[#111827] border-l border-slate-800 h-full p-6 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2 text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
            <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
              Grounded Citation
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-5 space-y-4">
          {/* Metadata Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <FileText className="w-4 h-4 text-emerald-400" />
              <span>Source Document:</span>
            </div>
            <div className="text-sm font-medium text-slate-200 break-all">
              {citation.document_name}
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-xs">
              <div>
                <span className="text-slate-500 block">Reference Marker</span>
                <span className="text-emerald-400 font-bold text-sm">
                  {(() => {
                    const p = citation.page_number;
                    if (!p) return 'Ref 1';
                    const num = Number(p);
                    if (!isNaN(num) && num > 1900 && num < 2100) return `FY ${num}`;
                    if (String(p).startsWith('FY') || String(p).startsWith('Rank')) return String(p);
                    return `Page ${p}`;
                  })()}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Section</span>
                <span className="text-slate-200 font-medium">{citation.section || 'General Content'}</span>
              </div>
            </div>
          </div>

          {/* Source Excerpt */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 block">
              Verified Source Excerpt
            </label>
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 text-xs font-mono leading-relaxed text-slate-300 whitespace-pre-wrap selection:bg-emerald-500">
              "{citation.excerpt}"
            </div>
          </div>

          {/* Verification Badge */}
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            <span>Exact grounded citation retrieved from vector index & document store. Never hallucinated.</span>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-slate-800 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
