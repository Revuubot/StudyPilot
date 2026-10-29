/**
 * StudyPilot API Client
 *
 * Centralised HTTP + WebSocket client for all backend communication.
 * Stores JWT token in localStorage and attaches it to every request.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

class StudyPilotAPI {
  constructor() {
    this.baseUrl = API_BASE;
    this.wsBase = WS_BASE;
  }

  // ── Token helpers ─────────────────────────────────────────────────────────
  getToken() {
    return localStorage.getItem('studypilot_token');
  }

  setToken(token) {
    localStorage.setItem('studypilot_token', token);
  }

  setUserId(id) {
    localStorage.setItem('studypilot_user_id', id);
  }

  getUserId() {
    return localStorage.getItem('studypilot_user_id');
  }

  clearAuth() {
    localStorage.removeItem('studypilot_token');
    localStorage.removeItem('studypilot_user_id');
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  // ── Internal fetch wrapper ────────────────────────────────────────────────
  async _fetch(path, options = {}) {
    const headers = { ...options.headers };
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${this.baseUrl}${path}`, { ...options, headers });

    if (res.status === 401) {
      this.clearAuth();
      throw new Error('Session expired. Please log in again.');
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }

    return res.json();
  }

  // ── Auth ──────────────────────────────────────────────────────────────────
  async register(email, password) {
    const data = await this._fetch('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    this.setUserId(data.user_id);
    return data;
  }

  async login(email, password) {
    const data = await this._fetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    this.setUserId(data.user_id);
    return data;
  }

  logout() {
    this.clearAuth();
  }

  // ── Summarise ─────────────────────────────────────────────────────────────
  async summarizeYouTube(url) {
    return this._fetch('/api/summarise/youtube', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  async summarizePDF(file) {
    const formData = new FormData();
    formData.append('file', file);
    return this._fetch('/api/summarise/pdf', {
      method: 'POST',
      body: formData,
    });
  }

  // ── Ask (REST) ────────────────────────────────────────────────────────────
  async askQuestion(query) {
    return this._fetch('/api/ask', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  // ── Search ────────────────────────────────────────────────────────────────
  async searchNotes(q, topK = 10) {
    return this._fetch(`/api/search?q=${encodeURIComponent(q)}&top_k=${topK}`);
  }

  // ── Analytics ─────────────────────────────────────────────────────────────
  async getAnalytics(days = 7) {
    return this._fetch(`/api/analytics/dashboard?days=${days}`);
  }

  async getMetrics() {
    return this._fetch('/api/metrics/evaluation');
  }

  // ── Tasks ─────────────────────────────────────────────────────────────────
  async getTaskStatus(taskId) {
    return this._fetch(`/api/tasks/${taskId}`);
  }

  // ── WebSocket ─────────────────────────────────────────────────────────────
  connectWebSocket(query, { onChunk, onCitations, onStatus, onDone, onError }) {
    const ws = new WebSocket(`${this.wsBase}/ws/ask`);

    ws.onopen = () => {
      ws.send(JSON.stringify({ token: this.getToken(), query }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case 'chunk':
            onChunk?.(msg.content);
            break;
          case 'citations':
            onCitations?.(msg.data);
            break;
          case 'status':
            onStatus?.(msg.content);
            break;
          case 'done':
            onDone?.(msg.latency_ms);
            break;
          case 'error':
            onError?.(msg.detail);
            break;
          default:
            break;
        }
      } catch {
        onError?.('Failed to parse server message');
      }
    };

    ws.onerror = () => {
      onError?.('WebSocket connection failed');
    };

    ws.onclose = () => {
      // Connection closed
    };

    return ws;
  }
}

const api = new StudyPilotAPI();
export default api;
