import React from 'react';
import { Sparkles, Database } from 'lucide-react';

interface StatusPillProps {
  stage: string | null;
  message: string | null;
}

export const StatusPill: React.FC<StatusPillProps> = ({ stage, message }) => {
  if (!message) return null;

  const isRetrieval = stage === 'retrieval';

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-medium animate-pulse my-2">
      {isRetrieval ? (
        <Database className="w-3.5 h-3.5 text-secondary animate-bounce" />
      ) : (
        <Sparkles className="w-3.5 h-3.5 text-primary animate-spin" />
      )}
      <span>{message}</span>
    </div>
  );
};
