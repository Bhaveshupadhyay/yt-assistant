import type { ModelsCatalogResponse } from '../types/model';
import type { SessionSummary, SessionDetail, SessionDetailDTO, SessionCreateRequest } from '../types/session';

const RAW_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '';
const API_BASE = RAW_BASE ? `${RAW_BASE.replace(/\/$/, '')}/api/v1` : '/api/v1';

export async function fetchHealth(): Promise<{ status: string; components: Record<string, any> }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchModels(): Promise<ModelsCatalogResponse> {
  const res = await fetch(`${API_BASE}/models`);
  if (!res.ok) {
    throw new Error(`Failed to load model catalog: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSessions(limit = 50, offset = 0): Promise<SessionSummary[]> {
  const res = await fetch(`${API_BASE}/sessions?limit=${limit}&offset=${offset}`);
  if (!res.ok) {
    throw new Error(`Failed to load sessions: ${res.statusText}`);
  }
  return res.json();
}

export async function createSession(req: SessionCreateRequest = {}): Promise<SessionSummary> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: req.title || 'New Conversation',
      model_used: req.model_used || 'claude-3-5-sonnet',
    }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create session: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch session: ${res.statusText}`);
  }
  const data: SessionDetailDTO = await res.json();
  
  const artifactsByMsgId = new Map<string, any>();
  if (data.artifacts) {
    for (const art of data.artifacts) {
      const msgId = art.messageId || art.message_id;
      if (msgId) {
        artifactsByMsgId.set(msgId, art);
      }
    }
  }

  return {
    id: data.id,
    title: data.title,
    model_used: data.model_used,
    created_at: data.created_at,
    updated_at: data.updated_at,
    artifacts: data.artifacts,
    messages: (data.messages || []).map(m => {
      const matchedArtifact = artifactsByMsgId.get(m.id);
      return {
        id: m.id,
        sessionId: m.session_id,
        role: m.role,
        content: m.content,
        citations: m.citations || [],
        hasArtifact: m.has_artifact || Boolean(matchedArtifact),
        artifact: matchedArtifact || null,
        createdAt: m.created_at,
      };
    }),
  };
}

export async function updateSession(
  sessionId: string,
  update: { title?: string; model_used?: string }
): Promise<SessionSummary> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  });
  if (!res.ok) {
    throw new Error(`Failed to update session: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Failed to delete session: ${res.statusText}`);
  }
}
