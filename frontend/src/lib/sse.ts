import type { Citation, Artifact } from '../types/chat';

export interface SSECallbacks {
  onStatus?: (data: { stage: string; message: string }) => void;
  onToken?: (delta: string) => void;
  onCitations?: (citations: Citation[]) => void;
  onArtifact?: (artifact: Artifact) => void;
  onDone?: (doneData: any) => void;
  onError?: (err: { error: string; code?: string }) => void;
}

const RAW_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '';
const API_BASE = RAW_BASE ? `${RAW_BASE.replace(/\/$/, '')}/api/v1` : '/api/v1';

export async function streamChatSSE(
  sessionId: string,
  message: string,
  model?: string,
  skill?: string,
  callbacks: SSECallbacks = {},
  abortSignal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      model: model || undefined,
      skill: skill || undefined,
    }),
    signal: abortSignal,
  });

  if (!res.ok) {
    let errorDetail = `Chat request failed (${res.status})`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.message || errJson.detail || errorDetail;
    } catch {
      // ignore json parse error
    }
    const errObj = { error: errorDetail, code: `HTTP_${res.status}` };
    callbacks.onError?.(errObj);
    throw new Error(errorDetail);
  }

  if (!res.body) {
    throw new Error('Response body is null');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = 'message';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          currentEvent = 'message';
          continue;
        }

        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.slice(6).trim();
          continue;
        }

        if (trimmed.startsWith('data:')) {
          const dataStr = trimmed.slice(5).trim();
          let dataJson: any;
          try {
            dataJson = JSON.parse(dataStr);
          } catch {
            dataJson = dataStr;
          }

          if (currentEvent === 'status') {
            callbacks.onStatus?.(dataJson);
          } else if (currentEvent === 'token') {
            const delta = typeof dataJson === 'object' && dataJson !== null ? dataJson.delta : dataJson;
            callbacks.onToken?.(delta || '');
          } else if (currentEvent === 'citations') {
            callbacks.onCitations?.(Array.isArray(dataJson) ? dataJson : []);
          } else if (currentEvent === 'artifact') {
            callbacks.onArtifact?.({
              id: dataJson.id,
              sessionId: dataJson.session_id,
              messageId: dataJson.message_id,
              artifactType: dataJson.artifact_type || 'html',
              title: dataJson.title || 'Generated Artifact',
              content: dataJson.content || '',
            });
          } else if (currentEvent === 'done') {
            callbacks.onDone?.(dataJson);
          } else if (currentEvent === 'error') {
            callbacks.onError?.(typeof dataJson === 'object' ? dataJson : { error: String(dataJson) });
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
