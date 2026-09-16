import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const api = {
  // System Health
  getHealth: async () => {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (error) {
      console.warn('Backend offline or degraded:', error);
      return {
        status: 'degraded',
        database_connected: false,
        active_llm_provider: 'unavailable',
        active_llm_model: 'offline',
      };
    }
  },

  // Documents
  getDocuments: async () => {
    const response = await apiClient.get('/documents');
    return response.data;
  },

  uploadDocument: async (formData) => {
    const response = await apiClient.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      // PDF parsing, vector indexing, and KPI extraction happen synchronously.
      timeout: 300000,
    });
    return response.data;
  },

  deleteDocument: async (documentId) => {
    const response = await apiClient.delete(`/documents/${documentId}`);
    return response.data;
  },

  // Investment Profile
  getProfile: async () => {
    const response = await apiClient.get('/profile');
    return response.data;
  },

  saveProfile: async (profileData) => {
    const response = await apiClient.post('/profile', profileData);
    return response.data;
  },

  updateProfile: async (profileData) => {
    const response = await apiClient.put('/profile', profileData);
    return response.data;
  },

  // Financial Research
  getCompanies: async (params = {}) => {
    const response = await apiClient.get('/research/companies', { params });
    return response.data;
  },

  getMutualFunds: async (params = {}) => {
    const response = await apiClient.get('/research/mutual-funds', { params });
    return response.data;
  },

  seedResearchData: async () => {
    const response = await apiClient.post('/research/seed');
    return response.data;
  },

  // Recommendations
  getRecommendations: async (params = {}) => {
    const response = await apiClient.get('/recommendations', { params });
    return response.data;
  },

  evaluateRecommendations: async (profileData) => {
    const response = await apiClient.post('/recommendations/evaluate', profileData);
    return response.data;
  },

  // AI Analyst Chat
  sendMessage: async (message, sessionId = null, documentId = null, companyName = null) => {
    const response = await apiClient.post('/chat', {
      message,
      session_id: sessionId,
      document_id: documentId,
      company_name: companyName,
    });
    return response.data;
  },

  getChatSessions: async () => {
    const response = await apiClient.get('/chat/sessions');
    return response.data;
  },

  getSessionMessages: async (sessionId) => {
    const response = await apiClient.get(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  deleteChatSession: async (sessionId) => {
    const response = await apiClient.delete(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  streamMessage: async (payload, onIntent, onToken, onCitations, onDone, onError) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Stream request failed with HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // keep remaining partial line

        let currentEvent = null;
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.replace('event: ', '').trim();
          } else if (line.startsWith('data: ')) {
            const rawData = line.replace('data: ', '').trim();
            try {
              const data = JSON.parse(rawData);
              if (currentEvent === 'intent' && onIntent) onIntent(data);
              else if (currentEvent === 'token' && onToken) onToken(data.token);
              else if (currentEvent === 'citations' && onCitations) onCitations(data.citations);
              else if (currentEvent === 'done' && onDone) onDone(data);
            } catch (e) {
              // Non-JSON line or partial
            }
          }
        }
      }
    } catch (err) {
      console.error('SSE streaming error:', err);
      if (onError) onError(err);
    }
  },

  // Financial KPI Extraction
  extractKPIs: async (documentId) => {
    const response = await apiClient.post(`/kpis/extract/${documentId}`);
    return response.data;
  },

  getKPIs: async (documentId) => {
    const response = await apiClient.get(`/kpis/${documentId}`);
    return response.data;
  },

  getAllKPIs: async () => {
    const response = await apiClient.get('/kpis');
    return response.data;
  },
};

export default api;
