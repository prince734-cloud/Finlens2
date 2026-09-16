import React from 'react';
import { Sparkles, FileText } from 'lucide-react';
import ChatBox from '../components/ChatBox';

export default function Chat({ selectedDoc, onClearSelectedDoc, onSelectDoc }) {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Fact-Grounded RAG Intelligence</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Ask Questions from Reports
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Query corporate annual reports, earnings disclosures, and 10-Ks with strict fact-grounding and verifiable page citations.
          </p>
        </div>

        {selectedDoc && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <FileText className="w-4 h-4" />
            <span>Target: <strong>{selectedDoc.company_name || selectedDoc.filename}</strong></span>
          </div>
        )}
      </div>

      {/* Main Chat Interface */}
      <ChatBox
        selectedDoc={selectedDoc}
        onClearSelectedDoc={onClearSelectedDoc}
        onSelectDoc={onSelectDoc}
      />
    </div>
  );
}
