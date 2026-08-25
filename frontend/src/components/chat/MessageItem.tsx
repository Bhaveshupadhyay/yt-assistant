import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Sparkles, User, Layout, ArrowRight } from 'lucide-react';
import type { ChatMessage, Citation, Artifact } from '../../types/chat';
import { CitationPill } from './CitationPill';
import { copyToClipboard } from '../../lib/utils';

interface MessageItemProps {
  message: ChatMessage;
  onCitationClick: (citation: Citation) => void;
  onOpenArtifact?: (artifact: Artifact) => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onCitationClick,
  onOpenArtifact,
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copyToClipboard(message.content);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const artifactType = message.artifact?.artifactType || message.artifact?.artifact_type || 'Tool';

  return (
    <div
      className={`py-5 px-4 sm:px-6 transition-colors ${
        isUser
          ? 'bg-transparent'
          : 'bg-surface/50 border-y border-border/40'
      }`}
    >
      <div className="max-w-3xl mx-auto flex gap-3 sm:gap-4">
        {/* Avatar */}
        <div className="flex-shrink-0">
          {isUser ? (
            <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 text-primary flex items-center justify-center font-medium text-xs">
              <User className="w-4 h-4" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-secondary/20 border border-secondary/30 text-secondary flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
          )}
        </div>

        {/* Message Content */}
        <div className="flex-1 min-w-0 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground">
              {isUser ? 'You' : 'The Lenny Growth Assistant'}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="cursor-pointer text-muted hover:text-foreground p-1 rounded-md hover:bg-surface-secondary transition-colors"
                title="Copy message content"
              >
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </div>

          {/* Markdown Content */}
          <div className="prose text-xs sm:text-sm leading-relaxed text-foreground break-words">
            {message.content ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    const isInline = !match && !String(children).includes('\n');
                    return isInline ? (
                      <code className="bg-surface-secondary px-1.5 py-0.5 rounded font-mono text-[0.85em] text-primary" {...props}>
                        {children}
                      </code>
                    ) : (
                      <div className="relative group my-2">
                        <pre className="p-3 rounded-lg bg-slate-950 text-slate-100 font-mono text-xs overflow-x-auto border border-border">
                          <code className={className} {...props}>
                            {children}
                          </code>
                        </pre>
                      </div>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            ) : message.isStreaming ? (
              <div className="flex items-center gap-1.5 text-muted text-xs py-1">
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse-dot" />
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse-dot [animation-delay:200ms]" />
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse-dot [animation-delay:400ms]" />
              </div>
            ) : null}
          </div>

          {/* Artifact Attached CTA */}
          {(message.hasArtifact || message.artifact) && (
            <div className="mt-3 p-3 rounded-xl bg-secondary/10 border border-secondary/30 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-xs">
                <Layout className="w-4 h-4 text-secondary flex-shrink-0" />
                <div>
                  <span className="font-medium text-foreground">
                    {message.artifact?.title || 'Interactive Artifact Generated'}
                  </span>
                  <span className="text-muted ml-2 text-[11px] uppercase font-mono">
                    [{artifactType}]
                  </span>
                </div>
              </div>
              <button
                onClick={() => message.artifact && onOpenArtifact?.(message.artifact)}
                className="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-secondary text-white text-xs font-semibold hover:bg-secondary-hover transition-colors shadow-sm"
              >
                <span>View Panel</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Citations Footer */}
          {message.citations && message.citations.length > 0 && (
            <div className="pt-2 border-t border-border/50">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">
                Transcript Grounding & Citations ({message.citations.length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {message.citations.map((c, i) => (
                  <CitationPill
                    key={i}
                    citation={c}
                    onClick={() => onCitationClick(c)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
