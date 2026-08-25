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
      const rawList = catalog.available_models || [];
      const formattedList: ModelInfo[] = rawList.map(m => ({
        id: m.id,
        name: m.name,
        provider: m.provider,
        is_cloud: m.is_cloud,
        is_local: !m.is_cloud || m.provider === 'ollama',
        description: m.description,
        is_available: m.is_available,
      }));

      setModels(formattedList);
      
      if (catalog.active_model && formattedList.some(m => m.id === catalog.active_model)) {
        setActiveModel(catalog.active_model);
      } else if (formattedList.length > 0 && !formattedList.some(m => m.id === activeModel)) {
        const firstAvailable = formattedList.find(m => m.is_available) || formattedList[0];
        setActiveModel(firstAvailable.id);
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
