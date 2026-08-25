export interface ModelInfo {
  id: string;
  name: string;
  provider: 'anthropic' | 'openai' | 'gemini' | 'ollama' | string;
  is_local: boolean;
  is_cloud: boolean;
  description: string;
  is_available: boolean;
}

export interface ModelItemDTO {
  id: string;
  name: string;
  provider: string;
  is_cloud: boolean;
  is_available: boolean;
  description: string;
}

export interface ModelsCatalogResponse {
  active_model?: string;
  active_provider?: string;
  available_models: ModelItemDTO[];
  providers?: Record<string, any>;
}
