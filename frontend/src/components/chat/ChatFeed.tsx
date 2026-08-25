import React, { useRef, useEffect } from 'react';
import type { ChatMessage, Citation, Artifact } from '../../types/chat';
import { MessageItem } from './MessageItem';
import { StarterChips } from './StarterChips';
import { StatusPill } from './StatusPill';
import { AlertCircle } from 'lucide-react';

interface ChatFeedProps {
  messages: ChatMessage[];
  statusStage: string | null;
  statusMessage: string | null;
  error: string | null;
  onCitationClick: (citation: Citation) => void;
  onOpenArtifact: (artifact: Artifact) => void;
  onSelectPrompt: (prompt: string, skill?: string) => void;
}

export const ChatFeed: React.FC<ChatFeedProps> = ({
  messages,
  statusStage,
  statusMessage,
  error,
  onCitationClick,
  onOpenArtifact,
  onSelectPrompt,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, statusMessage]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center overflow-y-auto">
        <StarterChips onSelectPrompt={onSelectPrompt} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="divide-y divide-border/30">
        {messages.map((msg) => (
          <MessageItem
            key={msg.id}
            message={msg}
            onCitationClick={onCitationClick}
            onOpenArtifact={onOpenArtifact}
          />
        ))}
      </div>

      {statusMessage && (
        <div className="px-6 py-2 max-w-3xl mx-auto">
          <StatusPill stage={statusStage} message={statusMessage} />
        </div>
      )}

      {error && (
        <div className="px-6 py-3 max-w-3xl mx-auto">
          <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        </div>
      )}

      <div ref={bottomRef} className="h-4" />
    </div>
  );
};
