export type ArtifactViewMode = 'preview' | 'code';

export interface Citation {
  episode_title: string;
  guest_name: string;
  guest_role?: string | null;
  timestamp: string;
  youtube_url?: string | null;
  snippet: string;
}

export interface Artifact {
  id?: string;
  sessionId?: string;
  session_id?: string;
  messageId?: string | null;
  message_id?: string | null;
  artifactType?: 'html' | 'markdown' | 'svg';
  artifact_type?: 'html' | 'markdown' | 'svg';
  title: string;
  content: string;
  createdAt?: string;
  created_at?: string;
}

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  hasArtifact?: boolean;
  artifact?: Artifact | null;
  isStreaming?: boolean;
  createdAt: string;
}

export interface ChatStatusEvent {
  stage: string;
  message: string;
}

export interface ChatTokenEvent {
  token: string;
}

export interface ChatDoneEvent {
  full_text: string;
  citations: Citation[];
  has_artifact: boolean;
  model_used: string;
}

export interface ChatErrorEvent {
  error: string;
  code?: string;
}
