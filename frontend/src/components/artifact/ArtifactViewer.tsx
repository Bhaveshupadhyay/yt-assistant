import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { X, Eye, Code2, Download, Copy, Check, Maximize2, Minimize2 } from 'lucide-react';
import type { Artifact, ArtifactViewMode } from '../../types/chat';
import { SandboxedIframe } from './SandboxedIframe';
import { CodeView } from './CodeView';
import { copyToClipboard } from '../../lib/utils';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  isOpen: boolean;
  viewMode: ArtifactViewMode;
  isDark: boolean;
  onClose: () => void;
  onToggleViewMode: () => void;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({
  artifact,
  isOpen,
  viewMode,
  isDark,
  onClose,
  onToggleViewMode,
}) => {
  const [copied, setCopied] = React.useState(false);
  const [isFullscreen, setIsFullscreen] = React.useState(false);

  if (!isOpen || !artifact) return null;

  const handleCopy = async () => {
    const success = await copyToClipboard(artifact.content);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const artifactType = artifact.artifactType || artifact.artifact_type || 'html';
  const isMarkdown = artifactType === 'markdown';

  const handleDownload = () => {
    const ext = artifactType === 'html' ? 'html' : artifactType === 'svg' ? 'svg' : 'md';
    const blob = new Blob([artifact.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className={`flex flex-col bg-surface border-l border-border transition-all duration-300 ${
        isFullscreen ? 'fixed inset-0 z-50 border-l-0' : 'h-full w-full'
      }`}
    >
      {/* Top Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-secondary/40">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-secondary/10 text-secondary border border-secondary/20">
            {artifactType}
          </span>
          <h3 className="font-semibold text-xs sm:text-sm text-foreground truncate" title={artifact.title}>
            {artifact.title}
          </h3>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* Tab Switcher */}
          <div className="flex items-center bg-surface-secondary rounded-lg p-0.5 border border-border mr-2">
            <button
              type="button"
              onClick={() => viewMode !== 'preview' && onToggleViewMode()}
              className={`cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                viewMode === 'preview'
                  ? 'bg-surface text-foreground shadow-xs font-semibold'
                  : 'text-muted hover:text-foreground'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Preview</span>
            </button>
            <button
              type="button"
              onClick={() => viewMode !== 'code' && onToggleViewMode()}
              className={`cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                viewMode === 'code'
                  ? 'bg-surface text-foreground shadow-xs font-semibold'
                  : 'text-muted hover:text-foreground'
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>Code</span>
            </button>
          </div>

          {/* Copy Button */}
          <button
            type="button"
            onClick={handleCopy}
            className="cursor-pointer p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
            title="Copy Artifact Content"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
          </button>

          {/* Download Button */}
          <button
            type="button"
            onClick={handleDownload}
            className="cursor-pointer p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
            title="Download Artifact File"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* Fullscreen Toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="cursor-pointer p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {/* Close Panel */}
          <button
            type="button"
            onClick={onClose}
            className="cursor-pointer p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
            title="Close Panel (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative">
        {viewMode === 'preview' ? (
          isMarkdown ? (
            <div className="w-full h-full p-6 overflow-y-auto bg-surface prose text-xs sm:text-sm leading-relaxed text-foreground">
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
                      <pre className="p-3 rounded-lg bg-slate-950 text-slate-100 font-mono text-xs overflow-x-auto border border-border">
                        <code className={className} {...props}>
                          {children}
                        </code>
                      </pre>
                    );
                  },
                }}
              >
                {artifact.content}
              </ReactMarkdown>
            </div>
          ) : (
            <SandboxedIframe
              content={artifact.content}
              title={artifact.title}
              isDark={isDark}
            />
          )
        ) : (
          <CodeView
            code={artifact.content}
            language={artifactType}
          />
        )}
      </div>
    </div>
  );
};
