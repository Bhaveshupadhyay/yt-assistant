import type { Artifact, ArtifactViewMode } from './chat';

export interface ActiveArtifactState {
  artifact: Artifact | null;
  isOpen: boolean;
  viewMode: ArtifactViewMode;
}
