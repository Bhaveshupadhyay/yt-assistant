import type { ChatMessage, Artifact } from './chat';

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

export interface SessionCreateRequest {
  title?: string;
  model_used?: string;
}
