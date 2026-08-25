import { useState, useEffect, useCallback } from 'react';
import { useTheme } from './hooks/useTheme';
import { useModels } from './hooks/useModels';
import { useSessions } from './hooks/useSessions';
import { useArtifact } from './hooks/useArtifact';
import { useChat } from './hooks/useChat';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { ChatFeed } from './components/chat/ChatFeed';
import { ChatInput } from './components/chat/ChatInput';
import { ArtifactViewer } from './components/artifact/ArtifactViewer';
import { CitationModal } from './components/chat/CitationModal';
import { OllamaStatusBanner } from './components/ui/OllamaStatusBanner';
import type { Citation, Artifact } from './types/chat';

export function App() {
  const { toggleTheme, isDark } = useTheme();
  const {
    models,
    activeModel,
    setActiveModel,
    isCurrentModelOffline,
    currentModelInfo,
    refreshModels,
  } = useModels();

  const {
    sessions,
    currentSessionId,
    currentSessionDetail,
    isLoading: isSessionsLoading,
    selectSession,
    createNewSession,
    deleteSession,
  } = useSessions(activeModel);

  const {
    activeArtifact,
    isOpen: isArtifactOpen,
    viewMode,
    openArtifact,
    closeArtifact,
    toggleViewMode,
  } = useArtifact();

  const handleArtifactGenerated = useCallback((artifact: Artifact) => {
    openArtifact(artifact, 'preview');
  }, [openArtifact]);

  const {
    messages,
    isStreaming,
    statusMessage,
    statusStage,
    error: chatError,
    sendMessage,
    cancelStream,
    loadExistingMessages,
    clearMessages,
  } = useChat(currentSessionId, activeModel, handleArtifactGenerated);

  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Initialize or synchronize session
  useEffect(() => {
    if (sessions.length > 0 && !currentSessionId && !isSessionsLoading) {
      selectSession(sessions[0].id);
    }
  }, [sessions, currentSessionId, isSessionsLoading, selectSession]);

  // Load messages when currentSessionDetail changes
  useEffect(() => {
    if (currentSessionDetail && currentSessionDetail.messages) {
      loadExistingMessages(currentSessionDetail.messages);
      // If session had an artifact, pre-populate active artifact
      if (currentSessionDetail.artifacts && currentSessionDetail.artifacts.length > 0) {
        const lastArt = currentSessionDetail.artifacts[currentSessionDetail.artifacts.length - 1];
        openArtifact({
          id: lastArt.id,
          sessionId: lastArt.session_id || lastArt.sessionId,
          artifactType: lastArt.artifact_type || lastArt.artifactType || 'html',
          title: lastArt.title,
          content: lastArt.content,
        });
      }
    } else if (!currentSessionId) {
      clearMessages();
    }
  }, [currentSessionDetail, currentSessionId, loadExistingMessages, clearMessages, openArtifact]);

  const handleNewChat = async () => {
    try {
      const created = await createNewSession(activeModel);
      selectSession(created.id);
      clearMessages();
      closeArtifact();
    } catch {
      // handled in hook
    }
  };

  const handlePromptSubmit = async (prompt: string, skill?: string) => {
    if (!currentSessionId) {
      try {
        const created = await createNewSession(activeModel);
        await selectSession(created.id);
        sendMessage(prompt, skill);
      } catch (err) {
        console.error('Failed to create session on prompt:', err);
      }
    } else {
      sendMessage(prompt, skill);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-background text-foreground overflow-hidden font-sans">
      {/* Top Warning Banner if Local Ollama is Offline */}
      {isCurrentModelOffline && (
        <OllamaStatusBanner
          modelName={currentModelInfo?.name || activeModel}
          onSwitchToCloud={() => setActiveModel('claude-3-5-sonnet')}
          onRefresh={refreshModels}
        />
      )}

      {/* Main Header */}
      <Header
        models={models}
        activeModel={activeModel}
        onSelectModel={setActiveModel}
        isDark={isDark}
        onToggleTheme={toggleTheme}
        onNewChat={handleNewChat}
        hasArtifact={Boolean(activeArtifact)}
        isArtifactOpen={isArtifactOpen}
        onToggleArtifact={() => isArtifactOpen ? closeArtifact() : activeArtifact && openArtifact(activeArtifact)}
        sessionTitle={currentSessionDetail?.title}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      {/* App Body: Sidebar + Chat Feed + Split Artifact Viewer */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Sidebar */}
        <div className={`${isSidebarOpen ? 'block' : 'hidden'} md:block h-full z-20`}>
          <Sidebar
            sessions={sessions}
            currentSessionId={currentSessionId}
            onSelectSession={(id) => {
              selectSession(id);
              if (window.innerWidth < 768) setIsSidebarOpen(false);
            }}
            onNewChat={handleNewChat}
            onDeleteSession={deleteSession}
            activeModel={activeModel}
            onSelectModel={setActiveModel}
          />
        </div>

        {/* Central Chat Feed + Input */}
        <main className="flex-1 flex flex-col h-full min-w-0 bg-background overflow-hidden relative">
          <ChatFeed
            messages={messages}
            statusStage={statusStage}
            statusMessage={statusMessage}
            error={chatError}
            onCitationClick={(citation) => setSelectedCitation(citation)}
            onOpenArtifact={(artifact) => openArtifact(artifact, 'preview')}
            onSelectPrompt={handlePromptSubmit}
          />

          <ChatInput
            onSendMessage={handlePromptSubmit}
            onCancelStream={cancelStream}
            isStreaming={isStreaming}
            activeModel={activeModel}
          />
        </main>

        {/* Right Split: Sandboxed Artifact Viewer */}
        {isArtifactOpen && (
          <aside className="w-full md:w-[48%] lg:w-[50%] h-full flex-shrink-0 z-10 animate-slide-in-right">
            <ArtifactViewer
              artifact={activeArtifact}
              isOpen={isArtifactOpen}
              viewMode={viewMode}
              isDark={isDark}
              onClose={closeArtifact}
              onToggleViewMode={toggleViewMode}
            />
          </aside>
        )}
      </div>

      {/* Verifiable Citation Modal */}
      <CitationModal
        citation={selectedCitation}
        isOpen={Boolean(selectedCitation)}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  );
}

export default App;
