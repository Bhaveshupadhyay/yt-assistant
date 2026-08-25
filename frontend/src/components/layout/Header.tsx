import React from 'react';
import { Radio, Moon, Sun, Plus, ChevronDown, PanelRight, AlertCircle } from 'lucide-react';
import type { ModelInfo } from '../../types/model';

interface HeaderProps {
  models: ModelInfo[];
  activeModel: string;
  onSelectModel: (modelId: string) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  onNewChat: () => void;
  hasArtifact: boolean;
  isArtifactOpen: boolean;
  onToggleArtifact: () => void;
  sessionTitle?: string;
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  models,
  activeModel,
  onSelectModel,
  isDark,
  onToggleTheme,
  onNewChat,
  hasArtifact,
  isArtifactOpen,
  onToggleArtifact,
  sessionTitle,
  onToggleSidebar,
}) => {
  const currentModel = models.find(m => m.id === activeModel);
  const isLocal = currentModel?.is_local ?? false;
  const isAvailable = currentModel?.is_available ?? true;

  return (
    <header className="h-14 border-b border-border bg-surface px-4 flex items-center justify-between gap-3 select-none flex-shrink-0">
      {/* Left: Mobile sidebar toggle + Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onToggleSidebar}
          className="cursor-pointer md:hidden p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-secondary"
          title="Toggle Navigation Sidebar"
        >
          <Radio className="w-5 h-5 text-primary" />
        </button>

        <div className="flex items-center gap-2 min-w-0">
          <div className="hidden sm:flex items-center justify-center w-7 h-7 rounded-lg bg-primary/10 text-primary border border-primary/20">
            <Radio className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h1 className="font-bold text-xs sm:text-sm text-foreground truncate">
              {sessionTitle || "Lenny Growth Assistant"}
            </h1>
            <p className="text-[10px] text-muted hidden sm:block font-medium">
              Grounded Operator Intelligence
            </p>
          </div>
        </div>
      </div>

      {/* Center: Model Selector */}
      <div className="relative flex items-center">
        <div className="relative inline-block">
          <select
            value={activeModel}
            onChange={(e) => onSelectModel(e.target.value)}
            className="cursor-pointer appearance-none bg-surface-secondary hover:bg-surface-secondary/80 border border-border rounded-xl pl-8 pr-8 py-1.5 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary transition-all"
          >
            {models.length > 0 ? (
              models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} {m.is_local ? '(Local Ollama)' : '(Cloud)'} {!m.is_available ? '[Offline]' : ''}
                </option>
              ))
            ) : (
              <option value="claude-3-5-sonnet">Claude 3.5 Sonnet (Cloud)</option>
            )}
          </select>

          {/* Model Status Dot */}
          <div className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
            {isAvailable ? (
              <span className={`w-2 h-2 rounded-full block ${isLocal ? 'bg-emerald-500' : 'bg-primary'}`} />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
            )}
          </div>

          {/* Chevron */}
          <ChevronDown className="w-3.5 h-3.5 text-muted absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Artifact Split View Toggle (if available) */}
        {hasArtifact && (
          <button
            onClick={onToggleArtifact}
            className={`cursor-pointer inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-all ${
              isArtifactOpen
                ? 'bg-secondary/15 text-secondary border-secondary/30'
                : 'text-muted hover:text-foreground border-border hover:bg-surface-secondary'
            }`}
            title="Toggle Split-Screen Artifact Viewer"
          >
            <PanelRight className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Artifact</span>
          </button>
        )}

        {/* New Chat CTA */}
        <button
          onClick={onNewChat}
          className="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-primary text-white text-xs font-semibold hover:bg-primary-hover transition-colors shadow-xs"
          title="Start New Conversation"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden md:inline">New Chat</span>
        </button>

        {/* Theme Switcher */}
        <button
          onClick={onToggleTheme}
          className="cursor-pointer p-2 rounded-xl text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
          title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
        </button>
      </div>
    </header>
  );
};
