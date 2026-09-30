/**
 * API client for AI Command Center.
 * Production: set VITE_API_URL to https://api.YOURDOMAIN.com at build time.
 * Development: empty string uses Vite proxy → localhost:8000
 */
const API_BASE = (import.meta.env.VITE_API_URL as string) || '';

function getToken(): string | null {
  return localStorage.getItem('acc_token');
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('acc_token', token);
  else localStorage.removeItem('acc_token');
}

export function getApiBase(): string {
  return API_BASE || window.location.origin;
}

let connectionListeners: Array<(online: boolean) => void> = [];
let lastOnline = true;

export function onConnectionChange(cb: (online: boolean) => void) {
  connectionListeners.push(cb);
  return () => {
    connectionListeners = connectionListeners.filter(c => c !== cb);
  };
}

function notifyConnection(online: boolean) {
  if (online !== lastOnline) {
    lastOnline = online;
    connectionListeners.forEach(cb => cb(online));
  }
}

export async function checkConnection(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/status`, { method: 'GET', signal: AbortSignal.timeout(5000) });
    const ok = res.ok;
    notifyConnection(ok);
    return ok;
  } catch {
    notifyConnection(false);
    return false;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    notifyConnection(true);
  } catch (err) {
    notifyConnection(false);
    throw new Error('CONNECTION_LOST');
  }

  if (res.status === 401) {
    setToken(null);
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = typeof err.detail === 'string' ? err.detail : (Array.isArray(err.detail) ? err.detail.map((d: any) => d.msg).join(', ') : JSON.stringify(err.detail) || 'Request failed');
    throw new Error(msg);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  checkConnection,

  register: (username: string, password: string) =>
    request<{ access_token: string; user: User }>('/api/auth/register', {
      method: 'POST', body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    request<{ access_token: string; user: User }>('/api/auth/login', {
      method: 'POST', body: JSON.stringify({ username, password }),
    }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request<User>('/api/auth/me'),
  onboarding: (data: { display_name: string; use_case?: string; preferred_style?: string }) =>
    request<User>('/api/auth/onboarding', { method: 'POST', body: JSON.stringify(data) }),

  listAgents: () => request<Agent[]>('/api/agents'),
  createAgent: (data: object) => request<Agent>('/api/agents', { method: 'POST', body: JSON.stringify(data) }),
  createAgentFromPrompt: (prompt: string) =>
    request<Agent>('/api/agents/from-prompt', { method: 'POST', body: JSON.stringify({ prompt }) }),
  getAgent: (id: number) => request<Agent>(`/api/agents/${id}`),
  updateAgent: (id: number, data: object) =>
    request<Agent>(`/api/agents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteAgent: (id: number) => request(`/api/agents/${id}`, { method: 'DELETE' }),
  listAgentRuns: (id: number) => request<AgentRun[]>(`/api/agents/${id}/runs`),
  runAgentNow: (id: number) => request<AgentRun>(`/api/agents/${id}/run-now`, { method: 'POST' }),

  listConversations: () => request<ConversationListItem[]>('/api/chat/conversations'),
  createConversation: (model = 'auto') =>
    request<Conversation>(`/api/chat/conversations?model=${model}`, { method: 'POST' }),
  getConversation: (id: number) => request<Conversation>(`/api/chat/conversations/${id}`),
  deleteConversation: (id: number) => request(`/api/chat/conversations/${id}`, { method: 'DELETE' }),
  sendMessage: (convId: number, content: string, model = 'auto') =>
    request<Message>(`/api/chat/conversations/${convId}/messages`, {
      method: 'POST', body: JSON.stringify({ content, model }),
    }),

  listProviders: () => request<ProviderStatus[]>('/api/providers'),
  connectProvider: (provider: string, api_key: string) =>
    request('/api/providers/connect', { method: 'POST', body: JSON.stringify({ provider, api_key }) }),
  disconnectProvider: (provider: string) =>
    request(`/api/providers/disconnect/${provider}`, { method: 'POST' }),

  listIntegrations: () => request<IntegrationStatus[]>('/api/integrations'),
  googleAuthUrl: () => request<{ auth_url: string }>('/api/integrations/google/auth-url'),
  disconnectGoogle: () => request('/api/integrations/google/disconnect', { method: 'POST' }),

  listNotifications: (unreadOnly = false) =>
    request<NotificationItem[]>(`/api/notifications?unread_only=${unreadOnly}`),
  markRead: (id: number) => request(`/api/notifications/${id}/read`, { method: 'POST' }),

  listAudit: () => request<AuditLog[]>('/api/audit'),

  testProvider: (provider: string) =>
    request<{ provider: string; ok: boolean; status: string; message: string; model?: string }>(
      `/api/providers/test/${provider}`, { method: 'POST' }
    ),

  gmailInbox: (classify = false) =>
    request<EmailItem[]>(`/api/integrations/gmail/inbox?classify=${classify}`),
  gmailAnalyze: (messageId: string) =>
    request<EmailAnalysis>(`/api/integrations/gmail/analyze/${messageId}`, { method: 'POST' }),
  gmailCreateDraft: (data: { to: string; subject: string; body: string; thread_id?: string }) =>
    request<{ draft_id: string; message: string }>('/api/integrations/gmail/drafts', {
      method: 'POST', body: JSON.stringify(data),
    }),
  gmailSendDraft: (draft_id: string) =>
    request('/api/integrations/gmail/drafts/send', {
      method: 'POST', body: JSON.stringify({ draft_id, confirm: true }),
    }),
  getSettings: () => request<UserSettings>('/api/settings'),
  updateSettings: (data: object) =>
    request<UserSettings>('/api/settings', { method: 'PATCH', body: JSON.stringify(data) }),
};

export interface User {
  id: number; username: string; display_name?: string | null;
  preferred_style?: string | null; use_case?: string | null;
  onboarding_completed: boolean; created_at?: string;
}
export interface Agent {
  id: number; name: string; description?: string | null; instructions: string;
  model: string; schedule_interval_minutes: number; status: string;
  notification_enabled: boolean; last_run_at?: string | null; next_run_at?: string | null;
  created_at?: string;
  sources: { id: number; source_type: string; url: string; name?: string; is_active: boolean }[];
}
export interface AgentRun {
  id: number; status: string; started_at?: string; completed_at?: string;
  duration_ms?: number; sources_checked: number; changes_detected: number;
  model_used?: string; provider_used?: string; summary?: string; ai_result?: string;
  notification_sent: boolean; error_message?: string;
}
export interface ConversationListItem {
  id: number; title: string; model: string; created_at?: string; updated_at?: string;
}
export interface Message {
  id: number; role: string; content: string; model_used?: string; provider_used?: string; created_at?: string;
}
export interface Conversation {
  id: number; title: string; model: string; messages: Message[];
}
export interface ProviderStatus {
  provider: string; name: string; connected: boolean; status: string; models: string[];
}
export interface IntegrationStatus {
  provider: string; name: string; connected: boolean; email?: string;
}
export interface NotificationItem {
  id: number; title: string; body?: string; is_read: boolean; agent_id?: number; created_at?: string;
}
export interface AuditLog {
  id: number; action: string; resource_type?: string; resource_id?: number; created_at?: string;
}
export interface UserSettings {
  default_model: string; auto_routing: boolean; auto_fallback: boolean;
  response_style: string; notifications_enabled: boolean; notification_sound: boolean; theme: string;
}


export interface EmailItem {
  id: string; thread_id?: string; from_addr: string; subject: string; snippet: string;
  date: string; classification?: string; summary?: string; needs_response?: boolean;
  why_matters?: string; suggested_reply?: string;
}
export interface EmailAnalysis {
  id: string; from: string; subject: string; classification?: string; summary?: string;
  why_matters?: string; needs_response?: boolean; suggested_reply?: string;
  provider_used?: string; model_used?: string;
}
