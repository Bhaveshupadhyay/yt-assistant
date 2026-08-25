import { useState, useRef, useCallback } from 'react';
import type { ChatMessage, Citation, Artifact } from '../types/chat';
import { streamChatSSE } from '../lib/sse';

export function useChat(
  sessionId: string | null,
  activeModel: string,
  onArtifactGenerated?: (artifact: Artifact) => void
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusStage, setStatusStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (prompt: string, skill?: string) => {
      const cleanPrompt = prompt.trim();
      if (!cleanPrompt || !sessionId || isStreaming) return;

      setError(null);
      setIsStreaming(true);
      setStatusMessage('Initializing grounded search...');
      setStatusStage('retrieval');

      const userMsgId = `user-${Date.now()}`;
      const assistantMsgId = `asst-${Date.now()}`;

      const userMessage: ChatMessage = {
        id: userMsgId,
        sessionId,
        role: 'user',
        content: cleanPrompt,
        createdAt: new Date().toISOString(),
      };

      const assistantPlaceholder: ChatMessage = {
        id: assistantMsgId,
        sessionId,
        role: 'assistant',
        content: '',
        citations: [],
        hasArtifact: false,
        isStreaming: true,
        createdAt: new Date().toISOString(),
      };

      setMessages(prev => [...prev, userMessage, assistantPlaceholder]);

      abortControllerRef.current = new AbortController();

      let accumulatedContent = '';
      let accumulatedCitations: Citation[] = [];
      let latestArtifact: Artifact | null = null;

      try {
        await streamChatSSE(
          sessionId,
          cleanPrompt,
          activeModel,
          skill,
          {
            onStatus: (statusData) => {
              setStatusStage(statusData.stage);
              setStatusMessage(statusData.message);
            },
            onToken: (delta) => {
              accumulatedContent += delta;
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, content: accumulatedContent }
                    : m
                )
              );
            },
            onCitations: (citations) => {
              accumulatedCitations = citations;
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, citations: accumulatedCitations }
                    : m
                )
              );
            },
            onArtifact: (artifact) => {
              latestArtifact = artifact;
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, hasArtifact: true, artifact }
                    : m
                )
              );
              onArtifactGenerated?.(artifact);
            },
            onDone: (_donePayload) => {
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        content: accumulatedContent,
                        citations: accumulatedCitations,
                        hasArtifact: Boolean(latestArtifact),
                        artifact: latestArtifact,
                        isStreaming: false,
                      }
                    : m
                )
              );
              setIsStreaming(false);
              setStatusMessage(null);
              setStatusStage(null);
            },
            onError: (errPayload) => {
              setError(errPayload.error);
              setIsStreaming(false);
              setStatusMessage(null);
              setStatusStage(null);
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, isStreaming: false }
                    : m
                )
              );
            },
          },
          abortControllerRef.current.signal
        );
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'An error occurred during communication');
        }
        setIsStreaming(false);
        setStatusMessage(null);
        setStatusStage(null);
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMsgId
              ? { ...m, isStreaming: false }
              : m
          )
        );
      }
    },
    [sessionId, activeModel, isStreaming, onArtifactGenerated]
  );

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setStatusMessage(null);
      setStatusStage(null);
      setMessages(prev =>
        prev.map(m => (m.isStreaming ? { ...m, isStreaming: false } : m))
      );
    }
  }, []);

  const loadExistingMessages = useCallback((loaded: any[]) => {
    const formatted: ChatMessage[] = loaded.map((m: any) => ({
      id: m.id,
      sessionId: m.session_id || sessionId,
      role: m.role,
      content: m.content,
      citations: m.citations || [],
      hasArtifact: m.has_artifact || false,
      createdAt: m.created_at,
    }));
    setMessages(formatted);
  }, [sessionId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isStreaming,
    statusMessage,
    statusStage,
    error,
    sendMessage,
    cancelStream,
    loadExistingMessages,
    clearMessages,
  };
}
