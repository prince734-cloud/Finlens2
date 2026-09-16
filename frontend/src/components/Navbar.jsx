import React from 'react';
import { FileText, Bot, TrendingUp, Sparkles, CheckCircle2 } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, systemHealth }) {
  const navItems = [
    { id: 'documents', label: 'Annual Reports & KPIs', icon: FileText },
    { id: 'chat', label: 'Ask Questions', icon: Bot },
  ];

  return (
    <header className="border-b border-slate-800 bg-[#0c121e]/95 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => setActiveTab('documents')}
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-sky-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-transform">
              <TrendingUp className="w-5 h-5 text-white stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold tracking-tight text-white">FinAdvisor</span>
                <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  RAG Intelligence
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Links (Only Core Features: Reports & Chat) */}
          <nav className="flex items-center space-x-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/10'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}

            {/* Subtle Online Status Pill */}
            <div className="hidden sm:flex items-center gap-1.5 pl-3 border-l border-slate-800 text-xs text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] text-slate-300 font-medium">Online</span>
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
