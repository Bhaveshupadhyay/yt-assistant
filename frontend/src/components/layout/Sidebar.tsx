import React, { useState } from 'react';
import { Plus, MessageSquare, Trash2, Search, Zap, Radio, Shield, Cpu } from 'lucide-react';
import type { SessionSummary } from '../../types/session';
import { formatRelativeTime } from '../../lib/utils';

interface SidebarProps {
  sessions: SessionSummary[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  activeModel: string;
  onSelectModel: (modelId: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  activeModel,
  onSelectModel,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredSessions = sessions.filter(s =>
    s.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <aside className="w-64 h-full bg-surface border-r border-border flex flex-col select-none flex-shrink-0">
      {/* Brand Header & New Chat */}
      <div className="p-3 border-b border-border space-y-2">
        <div className="flex items-center gap-2 px-1">
          <div className="w-6 h-6 rounded-lg bg-primary/20 text-primary flex items-center justify-center">
            <Radio className="w-3.5 h-3.5" />
          </div>
          <span className="font-bold text-xs tracking-tight text-foreground">
            The Lenny Assistant
          </span>
        </div>

        <button
          type="button"
          onClick={onNewChat}
          className="cursor-pointer w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 text-xs font-semibold transition-all duration-150 shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>New Conversation</span>
        </button>
      </div>

      {/* Search Filter */}
      <div className="px-3 py-2">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search conversations..."
            className="w-full bg-surface-secondary text-foreground text-xs rounded-lg pl-8 pr-3 py-1.5 border border-border placeholder:text-muted focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      {/* Session History List */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
        <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted">
          Recent Sessions ({filteredSessions.length})
        </div>

        {filteredSessions.length === 0 ? (
          <div className="p-4 text-center text-xs text-muted">
            {searchTerm ? 'No matching chats' : 'No prior conversations'}
          </div>
        ) : (
          filteredSessions.map((session) => {
            const isActive = session.id === currentSessionId;
            return (
              <div
                key={session.id}
                className={`group relative flex items-center justify-between rounded-xl transition-all duration-150 ${
                  isActive
                    ? 'bg-primary/15 font-semibold border border-primary/30'
                    : 'hover:bg-surface-secondary border border-transparent'
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelectSession(session.id)}
                  className={`cursor-pointer w-full flex items-center gap-2 text-left px-2.5 py-2 rounded-xl text-xs min-w-0 pr-8 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                    isActive ? 'text-foreground' : 'text-muted hover:text-foreground'
                  }`}
                >
                  <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted'}`} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs leading-tight">{session.title}</p>
                    <span className="text-[10px] text-muted font-normal block">
                      {formatRelativeTime(session.updated_at || session.created_at)}
                    </span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Delete this conversation session?')) {
                      onDeleteSession(session.id);
                    }
                  }}
                  className="cursor-pointer absolute right-2 opacity-0 group-hover:opacity-100 p-1 text-muted hover:text-destructive rounded hover:bg-surface transition-all focus:opacity-100"
                  title="Delete session"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer: Fast Model Switcher & Status */}
      <div className="p-3 border-t border-border bg-surface-secondary/30 space-y-2 text-xs">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
          Fast Model Switch
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <button
            type="button"
            onClick={() => onSelectModel('claude-3-5-sonnet')}
            className={`cursor-pointer flex items-center gap-1.5 p-1.5 rounded-lg border text-[11px] font-medium transition-all ${
              activeModel === 'claude-3-5-sonnet'
                ? 'bg-primary/10 border-primary text-primary font-semibold'
                : 'border-border text-muted hover:text-foreground'
            }`}
          >
            <Zap className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">Claude 3.5</span>
          </button>

          <button
            type="button"
            onClick={() => onSelectModel('llama3.2:1b')}
            className={`cursor-pointer flex items-center gap-1.5 p-1.5 rounded-lg border text-[11px] font-medium transition-all ${
              activeModel === 'llama3.2:1b' || activeModel === 'llama3.2'
                ? 'bg-emerald-500/10 border-emerald-500 text-emerald-600 dark:text-emerald-400 font-semibold'
                : 'border-border text-muted hover:text-foreground'
            }`}
          >
            <Cpu className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">Ollama 1B</span>
          </button>
        </div>

        <div className="pt-1 flex items-center justify-between text-[10px] text-muted">
          <span className="inline-flex items-center gap-1">
            <Shield className="w-3 h-3 text-primary" />
            <span>Strict Attribution</span>
          </span>
          <span className="font-mono">v1.1.0</span>
        </div>
      </div>
    </aside>
  );
};
