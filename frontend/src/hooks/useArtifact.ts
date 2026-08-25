import { useState, useCallback } from 'react';
import type { Artifact, ArtifactViewMode } from '../types/chat';

export function useArtifact() {
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<ArtifactViewMode>('preview');

  const openArtifact = useCallback((artifact: Artifact, mode: ArtifactViewMode = 'preview') => {
    setActiveArtifact(artifact);
    setViewMode(mode);
    setIsOpen(true);
  }, []);

  const closeArtifact = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggleViewMode = useCallback(() => {
    setViewMode((prev: ArtifactViewMode) => (prev === 'preview' ? 'code' : 'preview'));
  }, []);

  return {
    activeArtifact,
    isOpen,
    viewMode,
    setViewMode,
    openArtifact,
    closeArtifact,
    toggleViewMode,
  };
}
