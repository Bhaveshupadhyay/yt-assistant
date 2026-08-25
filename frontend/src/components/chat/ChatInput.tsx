import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Square, FileText, Sparkles } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string, skill?: string) => void;
  onCancelStream: () => void;
  isStreaming: boolean;
  activeModel: string;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onCancelStream,
  isStreaming,
  activeModel,
  disabled = false,
}) => {
  const [text, setText] = useState('');
  const [isShip30Active, setIsShip30Active] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [text]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || disabled || isStreaming) return;

    onSendMessage(text.trim(), isShip30Active ? 'ship30' : undefined);
    setText('');
    setIsShip30Active(false);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="p-3 sm:p-4 bg-background border-t border-border">
      <div className="max-w-3xl mx-auto">
        <div className="relative rounded-2xl bg-surface border border-border shadow-sm focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all">
          {/* Skill Selector Toolbar */}
          <div className="flex items-center justify-between px-3 pt-2.5 pb-1 border-b border-border/40 text-xs">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setIsShip30Active(!isShip30Active)}
                className={`cursor-pointer inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium transition-all ${
                  isShip30Active
                    ? 'bg-violet-500/20 text-violet-600 dark:text-violet-300 border border-violet-500/40 font-semibold'
                    : 'text-muted hover:text-foreground hover:bg-surface-secondary'
                }`}
                title="Format output as a 1,250-word Ship 30 for 30 essay"
              >
                <FileText className="w-3 h-3" />
                <span>Ship 30 for 30 Essay</span>
              </button>
            </div>

            <div className="flex items-center gap-1.5 text-muted font-mono text-[11px]">
              <Sparkles className="w-3 h-3 text-primary" />
              <span>{activeModel}</span>
            </div>
          </div>

          {/* Text Area */}
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isShip30Active
                ? "Enter topic for a ~1,250-word Ship 30 essay (e.g. 'B2B pricing metrics')..."
                : "Ask about product strategy, PLG, pricing, retention loops..."
            }
            disabled={disabled}
            rows={1}
            className="w-full bg-transparent px-4 py-3 text-xs sm:text-sm text-foreground placeholder:text-muted focus:outline-none resize-none max-h-[180px]"
          />

          {/* Action Row */}
          <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
            <span className="text-[11px] text-muted hidden sm:inline">
              Press <kbd className="px-1 py-0.5 bg-surface-secondary border border-border rounded font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1 py-0.5 bg-surface-secondary border border-border rounded font-mono text-[10px]">Shift+Enter</kbd> for new line
            </span>

            <div className="ml-auto flex items-center gap-2">
              {isStreaming ? (
                <button
                  type="button"
                  onClick={onCancelStream}
                  className="cursor-pointer inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-destructive/10 hover:bg-destructive/20 text-destructive text-xs font-semibold transition-colors"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => handleSubmit()}
                  disabled={!text.trim() || disabled}
                  className="cursor-pointer p-2 rounded-xl bg-primary text-white hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
                  title="Send prompt"
                >
                  <ArrowUp className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
