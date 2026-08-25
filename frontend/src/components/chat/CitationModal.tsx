import React from 'react';
import { X, ExternalLink, User, Clock, Radio } from 'lucide-react';
import type { Citation } from '../../types/chat';

interface CitationModalProps {
  citation: Citation | null;
  isOpen: boolean;
  onClose: () => void;
}

export const CitationModal: React.FC<CitationModalProps> = ({ citation, isOpen, onClose }) => {
  if (!isOpen || !citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div 
        className="bg-surface border border-border rounded-2xl max-w-lg w-full p-5 shadow-2xl overflow-hidden relative animate-scale-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border pb-3 mb-4">
          <div className="flex items-center gap-2 text-accent">
            <Radio className="w-5 h-5 text-accent flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-foreground text-sm leading-tight">
                {citation.episode_title}
              </h3>
              <p className="text-xs text-muted mt-0.5">Lenny's Podcast Transcript Attribution</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="cursor-pointer text-muted hover:text-foreground p-1 rounded-lg hover:bg-surface-secondary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
            <div className="flex items-center gap-1 bg-surface-secondary px-2.5 py-1 rounded-md border border-border">
              <User className="w-3.5 h-3.5 text-primary" />
              <span className="font-medium text-foreground">{citation.guest_name}</span>
              {citation.guest_role && <span className="text-muted">({citation.guest_role})</span>}
            </div>

            <div className="flex items-center gap-1 bg-surface-secondary px-2.5 py-1 rounded-md border border-border">
              <Clock className="w-3.5 h-3.5 text-accent" />
              <span className="font-mono text-foreground">{citation.timestamp}</span>
            </div>
          </div>

          <div className="bg-surface-secondary p-3.5 rounded-xl border border-border">
            <div className="text-xs font-semibold text-muted mb-1.5 uppercase tracking-wider">
              Exact Transcript Excerpt
            </div>
            <p className="text-xs sm:text-sm text-foreground leading-relaxed italic">
              "{citation.snippet}"
            </p>
          </div>

          {citation.youtube_url && (
            <div className="pt-2 flex justify-end">
              <a
                href={citation.youtube_url}
                target="_blank"
                rel="noopener noreferrer"
                className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent/10 hover:bg-accent/20 text-accent font-medium text-xs transition-colors border border-accent/20"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Open Episode on YouTube</span>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
