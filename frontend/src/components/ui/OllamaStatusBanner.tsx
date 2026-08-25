import React from 'react';
import { AlertTriangle, CloudLightning, RefreshCw } from 'lucide-react';

interface OllamaStatusBannerProps {
  onSwitchToCloud: () => void;
  onRefresh: () => void;
  modelName: string;
}

export const OllamaStatusBanner: React.FC<OllamaStatusBannerProps> = ({
  onSwitchToCloud,
  onRefresh,
  modelName,
}) => {
  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 text-amber-900 dark:text-amber-200 px-4 py-2.5 flex items-center justify-between gap-3 text-xs sm:text-sm">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
        <span>
          <strong>Local Ollama Offline:</strong> Model <code className="bg-amber-500/20 px-1 py-0.5 rounded font-mono">{modelName}</code> is selected, but Ollama daemon is not reachable on <span className="font-mono">http://localhost:11434</span>.
        </span>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={onRefresh}
          className="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-800 dark:text-amber-100 font-medium transition-colors"
          title="Retry Ollama Connection"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
        <button
          onClick={onSwitchToCloud}
          className="cursor-pointer inline-flex items-center gap-1 px-3 py-1 rounded bg-primary text-white font-medium hover:bg-primary-hover transition-colors shadow-sm"
        >
          <CloudLightning className="w-3.5 h-3.5" />
          <span>Switch to Cloud Claude 3.5</span>
        </button>
      </div>
    </div>
  );
};
