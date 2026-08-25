import { useState, useEffect, useCallback } from 'react';
import type { ModelInfo, ModelsCatalogResponse } from '../types/model';
import { fetchModels } from '../lib/api';

export function useModels() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [activeModel, setActiveModel] = useState<string>('claude-3-5-sonnet');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadModels = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const catalog: ModelsCatalogResponse = await fetchModels();
      setModels(catalog.models);
      
      if (!catalog.models.some(m => m.id === activeModel)) {
        setActiveModel(catalog.default_cloud_model || catalog.models[0]?.id || 'claude-3-5-sonnet');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load model catalog');
    } finally {
      setIsLoading(false);
    }
  }, [activeModel]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const currentModelInfo = models.find(m => m.id === activeModel);
  const isCurrentModelOffline = currentModelInfo ? !currentModelInfo.is_available : false;
  const isCurrentModelLocal = currentModelInfo ? currentModelInfo.is_local : false;

  return {
    models,
    activeModel,
    setActiveModel,
    currentModelInfo,
    isCurrentModelOffline,
    isCurrentModelLocal,
    isLoading,
    error,
    refreshModels: loadModels,
  };
}
