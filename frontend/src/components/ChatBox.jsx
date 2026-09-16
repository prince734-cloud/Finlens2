import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  FileText,
  Loader2,
  Sparkles,
  History,
  PlusCircle,
  Trash2,
  ChevronDown,
  X,
  ShieldCheck,
} from 'lucide-react';
import api from '../services/api';
import CitationViewer from './CitationViewer';

const INTENT_CONFIG = {
  document_rag: {
    label: 'Annual Report RAG',
    badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    icon: FileText,
  },
  company_research: {
    label: 'Corporate Fundamentals',
    badgeClass: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    icon: FileText,
  },
  general_financial: {
    label: 'Financial Intelligence',
    badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    icon: Bot,
  },
  system: {
    label: 'AI Analyst',
    badgeClass: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    icon: Bot,
  },
};

export default function ChatBox({ selectedDoc, onClearSelectedDoc, onSelectDoc }) {
  const [sessionId, setSessionId] = useState(() => `session-${Date.now()}`);
  const [sessions, setSessions] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [showSessionsDropdown, setShowSessionsDropdown] = useState(false);
  const [showDocDropdown, setShowDocDropdown] = useState(false);

  const initialWelcome = selectedDoc
    ? `Hello! I am ready to analyze the annual report for **${selectedDoc.company_name || selectedDoc.filename}**. Every answer will be grounded directly in this report with exact page citations.\n\nAsk me about revenue, net income, operating cash flow, balance sheet metrics, or disclosed risk factors.`
    : 'Hello! I am FinAdvisor, your institutional AI Financial Intelligence Analyst. Upload an annual report or select one below to ask targeted questions with verifiable source page citations.';

  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: initialWelcome,
      queryType: 'system',
      citations: [],
    },
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Load document list for selector
  useEffect(() => {
    async function loadDocs() {
      try {
        const docList = await api.getDocuments();
        setDocuments(docList || []);
      } catch (err) {
        console.warn('Could not load documents for chat selector:', err);
      }
    }
    loadDocs();
  }, []);

  // Update welcome message if active report changes
  useEffect(() => {
    if (selectedDoc && messages.length <= 1) {
      setMessages([
        {
          id: `welcome-${selectedDoc.id}`,
          role: 'assistant',
          content: `Target Report Active: **${selectedDoc.company_name || selectedDoc.filename}** (FY${selectedDoc.financial_year || 2024}). All assertions will cite exact pages from this document.`,
          queryType: 'document_rag',
          citations: [],
        },
      ]);
    }
  }, [selectedDoc]);

  // Load chat session list
  const loadSessions = async () => {
    try {
      const data = await api.getChatSessions();
      setSessions(data || []);
    } catch (err) {
      console.warn('Could not load chat sessions:', err);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [sessionId]);

  const handleNewChat = () => {
    const newId = `session-${Date.now()}`;
    setSessionId(newId);
    setMessages([
      {
        id: `welcome-${newId}`,
        role: 'assistant',
        content: selectedDoc
          ? `New session started for **${selectedDoc.company_name || selectedDoc.filename}**. What would you like to know from this report?`
          : 'New session started. Ask any question about your uploaded annual reports.',
        queryType: 'system',
        citations: [],
      },
    ]);
    setShowSessionsDropdown(false);
  };

  const handleSelectSession = async (sessId) => {
    if (sessId === sessionId) {
      setShowSessionsDropdown(false);
      return;
    }
    setLoading(true);
    setSessionId(sessId);
    setShowSessionsDropdown(false);

    try {
      const history = await api.getSessionMessages(sessId);
      if (history && history.length > 0) {
        setMessages(
          history.map((h) => ({
            id: h.id,
            role: h.role,
            content: h.message,
            queryType: h.query_type,
            citations: h.citations || [],
          }))
        );
      }
    } catch (err) {
      console.error('Error switching session:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (e, sessId) => {
    e.stopPropagation();
    try {
      await api.deleteChatSession(sessId);
      if (sessId === sessionId) {
        handleNewChat();
      }
      loadSessions();
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleSend = async (queryText = null) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textToSend,
      citations: [],
    };

    const assistantPlaceholderId = `asst-${Date.now()}`;
    const initialAssistantMessage = {
      id: assistantPlaceholderId,
      role: 'assistant',
      content: '',
      queryType: selectedDoc ? 'document_rag' : 'processing',
      citations: [],
    };

    setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
    if (!queryText) setInput('');
    setLoading(true);

    let accumulatedText = '';

    await api.streamMessage(
      {
        message: textToSend,
        session_id: sessionId,
        document_id: selectedDoc?.id || null,
        company_name: selectedDoc?.company_name || null,
      },
      // onIntent
      (intentData) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantPlaceholderId
              ? { ...msg, queryType: intentData.intent }
              : msg
          )
        );
      },
      // onToken
      (token) => {
        accumulatedText += token;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantPlaceholderId
              ? { ...msg, content: accumulatedText }
              : msg
          )
        );
      },
      // onCitations
      (citations) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantPlaceholderId
              ? { ...msg, citations: citations || [] }
              : msg
          )
        );
      },
      // onDone
      () => {
        setLoading(false);
        loadSessions();
      },
      // onError: Fallback to non-streaming endpoint
      async (err) => {
        console.warn('Streaming error, falling back to standard API:', err);
        try {
          const fallback = await api.sendMessage(
            textToSend,
            sessionId,
            selectedDoc?.id || null,
            selectedDoc?.company_name || null
          );
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantPlaceholderId
                ? {
                    ...msg,
                    content: fallback.answer,
                    queryType: fallback.query_type,
                    citations: fallback.citations || [],
                  }
                : msg
            )
          );
        } catch (fbErr) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantPlaceholderId
                ? {
                    ...msg,
                    content:
                      'Unable to complete analysis. Please verify that the FinAdvisor backend server is running.',
                    queryType: 'system',
                  }
                : msg
            )
          );
        } finally {
          setLoading(false);
          loadSessions();
        }
      }
    );
  };

  // Report-specific starter prompts
  const docPrompts = selectedDoc
    ? [
        `What was the total revenue and net income for ${selectedDoc.company_name || 'the company'} in FY${selectedDoc.financial_year || 2024}?`,
        'What are the primary risk factors disclosed in Item 1A of this report?',
        'Summarize the operating cash flows and balance sheet strength.',
        'What were the key drivers behind revenue and business segment performance?',
      ]
    : [
        'What was Apple 2024 revenue and net profit in the annual filing?',
        'What are the primary risks disclosed in the 10-K report?',
        'Summarize the operating cash flows and balance sheet highlights.',
      ];

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-[#111827] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
      {/* Active Citation Modal Drawer */}
      <CitationViewer citation={activeCitation} onClose={() => setActiveCitation(null)} />

      {/* Top Session & Document Filter Bar */}
      <div className="px-4 sm:px-6 py-2.5 bg-slate-900/90 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          {/* Saved Sessions Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowSessionsDropdown(!showSessionsDropdown)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors font-medium cursor-pointer"
            >
              <History className="w-3.5 h-3.5 text-emerald-400" />
              <span>History ({sessions.length})</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {showSessionsDropdown && (
              <div className="absolute left-0 top-full mt-1.5 w-72 sm:w-80 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-40 p-2 space-y-1 animate-in fade-in duration-150">
                <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>Saved Chats</span>
                  <span className="text-[10px] text-slate-500">{sessions.length} threads</span>
                </div>
                <div className="max-h-56 overflow-y-auto space-y-1">
                  {sessions.length === 0 ? (
                    <div className="p-3 text-center text-slate-500 text-xs">
                      No previous sessions found.
                    </div>
                  ) : (
                    sessions.map((s) => (
                      <div
                        key={s.session_id}
                        onClick={() => handleSelectSession(s.session_id)}
                        className={`p-2 rounded-lg cursor-pointer flex items-center justify-between text-xs transition-colors ${
                          s.session_id === sessionId
                            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
                            : 'hover:bg-slate-800 text-slate-300'
                        }`}
                      >
                        <div className="truncate flex-1 pr-2">
                          <p className="truncate font-medium">{s.last_message || 'Empty Session'}</p>
                          <span className="text-[10px] text-slate-500">
                            {s.message_count} msgs
                          </span>
                        </div>
                        <button
                          onClick={(e) => handleDeleteSession(e, s.session_id)}
                          className="p-1 rounded hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                          title="Delete thread"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Active Target Document Indicator / Selector */}
          {selectedDoc ? (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-medium">
              <FileText className="w-3.5 h-3.5 text-emerald-400" />
              <span className="truncate max-w-xs font-semibold">
                Report: {selectedDoc.company_name || selectedDoc.filename}
              </span>
              <button
                onClick={() => onClearSelectedDoc && onClearSelectedDoc()}
                className="p-0.5 rounded hover:bg-emerald-500/20 text-emerald-400 hover:text-white transition-colors ml-1 cursor-pointer"
                title="Clear filter to query all documents"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="relative">
              <button
                onClick={() => setShowDocDropdown(!showDocDropdown)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                <span>Target a Report ({documents.length})</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {showDocDropdown && (
                <div className="absolute left-0 top-full mt-1.5 w-72 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-40 p-2 space-y-1">
                  <div className="px-2 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Select Report to Query
                  </div>
                  <div className="max-h-56 overflow-y-auto space-y-1">
                    {documents.length === 0 ? (
                      <div className="p-3 text-center text-slate-500 text-xs">
                        No reports uploaded yet.
                      </div>
                    ) : (
                      documents.map((d) => (
                        <div
                          key={d.id}
                          onClick={() => {
                            if (onSelectDoc) onSelectDoc(d);
                            setShowDocDropdown(false);
                          }}
                          className="p-2 rounded-lg cursor-pointer hover:bg-slate-800 text-slate-300 text-xs truncate"
                        >
                          <p className="font-semibold text-white truncate">{d.company_name || d.filename}</p>
                          <p className="text-[10px] text-slate-500 truncate">{d.filename}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <button
          onClick={handleNewChat}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 font-medium transition-colors cursor-pointer"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          const intentMeta = INTENT_CONFIG[msg.queryType] || {
            label: 'Report Analysis',
            badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
            icon: FileText,
          };
          const IntentIcon = intentMeta.icon;

          return (
            <div key={msg.id} className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
              {!isUser && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white flex-shrink-0 shadow-md">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-2xl px-5 py-4 ${
                  isUser
                    ? 'bg-emerald-600 text-white shadow-md'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 shadow-sm'
                }`}
              >
                {/* Intent Category Badge */}
                {!isUser && msg.queryType && (
                  <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-800/80">
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded border ${intentMeta.badgeClass}`}
                    >
                      <IntentIcon className="w-3 h-3" />
                      <span>{intentMeta.label}</span>
                    </span>
                    <span className="text-[10px] text-slate-500 flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3 text-emerald-500" />
                      <span>Fact-Grounded</span>
                    </span>
                  </div>
                )}

                {/* Message Content */}
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                {/* Verified Citations List */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800 space-y-2">
                    <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 block">
                      Verifiable Source Citations:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((cite, i) => (
                        <button
                          key={i}
                          onClick={() => setActiveCitation(cite)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-400 hover:text-emerald-300 border border-slate-700 text-xs font-mono transition-colors cursor-pointer"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>
                            {cite.document_name} •{' '}
                            {Number(cite.page_number) > 1900
                              ? `FY${cite.page_number}`
                              : `Page ${cite.page_number}`}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 flex-shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-3 items-center text-slate-400 text-xs pl-2">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
            <span>Analyzing annual report text & verifying page citations...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts */}
      {messages.length <= 2 && (
        <div className="px-4 sm:px-6 py-2.5 border-t border-slate-800/80 bg-slate-900/40">
          <div className="text-[11px] text-slate-400 font-semibold mb-2">
            {selectedDoc ? `Suggested questions for ${selectedDoc.company_name || selectedDoc.filename}:` : 'Suggested questions:'}
          </div>
          <div className="flex flex-wrap gap-2">
            {docPrompts.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(q)}
                className="text-xs px-3 py-1.5 rounded-full bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 hover:border-emerald-500/40 transition-colors cursor-pointer text-left"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Bar */}
      <div className="p-4 bg-[#0d131f] border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-3"
        >
          <input
            type="text"
            placeholder={
              selectedDoc
                ? `Ask anything about ${selectedDoc.company_name || selectedDoc.filename} (e.g. revenue, net profit, risk factors)...`
                : 'Ask anything about uploaded annual reports, revenue, profits, balance sheet, or risks...'
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 text-white transition-colors shadow-lg shadow-emerald-600/20 cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
