import React from 'react';
import { ExternalLink, Radio } from 'lucide-react';
import type { Citation } from '../../types/chat';

interface CitationPillProps {
  citation: Citation;
  onClick: () => void;
}

export const CitationPill: React.FC<CitationPillProps> = ({ citation, onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className="cursor-pointer inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-accent/10 border border-accent/30 hover:border-accent hover:bg-accent/20 text-accent text-xs font-medium transition-all duration-150 max-w-full truncate group"
      title={`Click to view transcript excerpt: ${citation.guest_name} [${citation.timestamp}]`}
    >
      <Radio className="w-3 h-3 text-accent flex-shrink-0" />
      <span className="font-medium text-foreground truncate">{citation.guest_name}</span>
      <span className="text-accent/80 font-mono text-[10px]">[{citation.timestamp}]</span>
      <ExternalLink className="w-2.5 h-2.5 opacity-60 group-hover:opacity-100 transition-opacity flex-shrink-0" />
    </button>
  );
};
