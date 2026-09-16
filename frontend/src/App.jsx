import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Documents from './pages/Documents';
import Chat from './pages/Chat';
import api from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('documents');
  const [selectedDocForChat, setSelectedDocForChat] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);

  useEffect(() => {
    async function checkHealth() {
      try {
        const health = await api.getHealth();
        setSystemHealth(health);
      } catch (err) {
        console.warn('Backend not responding to health probe:', err);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleAskQuestionFromDoc = (doc) => {
    setSelectedDocForChat(doc);
    setActiveTab('chat');
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] flex flex-col text-slate-100 font-sans">
      {/* Header & Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemHealth={systemHealth}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {activeTab === 'documents' && (
          <Documents onAskQuestion={handleAskQuestionFromDoc} />
        )}
        {activeTab === 'chat' && (
          <Chat
            selectedDoc={selectedDocForChat}
            onClearSelectedDoc={() => setSelectedDocForChat(null)}
            onSelectDoc={(doc) => setSelectedDocForChat(doc)}
          />
        )}
      </main>

      {/* Minimal Clean Footer */}
      <footer className="border-t border-slate-800/80 bg-[#0a0e17] py-5 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4">
          <p className="text-slate-400 font-medium">
            FinLens — Financial Intelligence & Annual Report RAG Platform
          </p>
          <p className="mt-1 text-[11px] text-slate-600">
            Automated KPI Extraction & Fact-Grounded Document Q&A with Verifiable Page Citations.
          </p>
        </div>
      </footer>
    </div>
  );
}
