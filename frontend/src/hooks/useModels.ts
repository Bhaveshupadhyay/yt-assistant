import { useState, useEffect, useCallback, useRef } from 'react';
import type { ModelInfo, ModelsCatalogResponse } from '../types/model';
import { fetchModels } from '../lib/api';

const STORAGE_KEY = 'lenny_active_model';

export function useModels() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [activeModel, setActiveModelState] = useState<string>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'llama3.2:1b';
    } catch {
      return 'llama3.2:1b';
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Keep a ref to the latest activeModel so loadModels doesn't re-trigger when activeModel changes
  const activeModelRef = useRef<string>(activeModel);
  activeModelRef.current = activeModel;

  const setActiveModel = useCallback((modelId: string) => {
    setActiveModelState(modelId);
    try {
      localStorage.setItem(STORAGE_KEY, modelId);
    } catch {
      // ignore storage errors
    }
  }, []);

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

      const currentSelection = activeModelRef.current;
      const isCurrentInCatalog = formattedList.some(m => m.id === currentSelection);

      // Only auto-assign if current selection is not registered in the catalog
      if (!isCurrentInCatalog && formattedList.length > 0) {
        const fallback =
          (catalog.active_model && formattedList.some(m => m.id === catalog.active_model && m.is_available)
            ? catalog.active_model
            : null) ||
          formattedList.find(m => m.is_available)?.id ||
          formattedList[0]?.id;

        if (fallback) {
          setActiveModel(fallback);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load model catalog');
    } finally {
      setIsLoading(false);
    }
  }, [setActiveModel]);

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

