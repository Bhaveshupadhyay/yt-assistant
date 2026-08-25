export interface ModelInfo {
  id: string;
  name: string;
  provider: 'anthropic' | 'openai' | 'gemini' | 'ollama';
  is_local: boolean;
  description: string;
  is_available: boolean;
}

export interface ModelsCatalogResponse {
  models: ModelInfo[];
  default_cloud_model: string;
  default_local_model: string;
}
