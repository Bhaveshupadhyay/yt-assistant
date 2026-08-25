import type { ChatMessage, Artifact, Citation } from './chat';

export interface MessageResponseDTO {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  has_artifact?: boolean;
  created_at: string;
}

export interface SessionSummary {
  id: string;
  title: string;
  model_used: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionDetail {
  id: string;
  title: string;
  model_used: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
  artifacts?: Artifact[];
}

export interface SessionDetailDTO {
  id: string;
  title: string;
  model_used: string;
  created_at: string;
  updated_at: string;
  messages: MessageResponseDTO[];
  artifacts?: Artifact[];
}

export interface SessionCreateRequest {
  title?: string;
  model_used?: string;
}
