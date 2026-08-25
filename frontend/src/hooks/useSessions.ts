import { useState, useEffect, useCallback, useRef } from 'react';
import type { SessionSummary, SessionDetail } from '../types/session';
import { fetchSessions, createSession, fetchSession, deleteSession as apiDeleteSession, updateSession as apiUpdateSession } from '../lib/api';

export function useSessions(initialModel = 'claude-3-5-sonnet') {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentSessionDetail, setCurrentSessionDetail] = useState<SessionDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const selectionRequestIdRef = useRef<number>(0);

  const loadSessionsList = useCallback(async () => {
    try {
      setIsLoading(true);
      const list = await fetchSessions();
      setSessions(list);
      return list;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch sessions');
      return [];
    } finally {
      setIsLoading(false);
    }
  }, []);

  const selectSession = useCallback(async (sessionId: string) => {
    const requestId = ++selectionRequestIdRef.current;
    setCurrentSessionId(sessionId);
    setCurrentSessionDetail(null); // Clear immediately to avoid stale state

    try {
      setIsLoading(true);
      const detail = await fetchSession(sessionId);
      if (selectionRequestIdRef.current === requestId) {
        setCurrentSessionDetail(detail);
      }
    } catch (err: any) {
      if (selectionRequestIdRef.current === requestId) {
        setError(err.message || 'Failed to load session details');
      }
    } finally {
      if (selectionRequestIdRef.current === requestId) {
        setIsLoading(false);
      }
    }
  }, []);

  const createNewSession = useCallback(async (model = initialModel, title = 'New Conversation') => {
    try {
      setIsLoading(true);
      const newSession = await createSession({ title, model_used: model });
      setSessions(prev => [newSession, ...prev]);
      ++selectionRequestIdRef.current;
      setCurrentSessionId(newSession.id);
      setCurrentSessionDetail({
        id: newSession.id,
        title: newSession.title,
        model_used: newSession.model_used,
        created_at: newSession.created_at,
        updated_at: newSession.updated_at,
        messages: [],
      });
      return newSession;
    } catch (err: any) {
      setError(err.message || 'Failed to create session');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [initialModel]);

  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await apiDeleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setCurrentSessionDetail(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete session');
      throw err;
    }
  }, [currentSessionId]);

  const updateSessionTitle = useCallback(async (sessionId: string, newTitle: string) => {
    try {
      const updated = await apiUpdateSession(sessionId, { title: newTitle });
      setSessions(prev => prev.map(s => (s.id === sessionId ? updated : s)));
      if (currentSessionDetail && currentSessionDetail.id === sessionId) {
        setCurrentSessionDetail(prev => prev ? { ...prev, title: updated.title } : null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update title');
    }
  }, [currentSessionDetail]);

  useEffect(() => {
    loadSessionsList();
  }, [loadSessionsList]);

  return {
    sessions,
    currentSessionId,
    currentSessionDetail,
    isLoading,
    error,
    selectSession,
    createNewSession,
    deleteSession,
    updateSessionTitle,
    refreshSessions: loadSessionsList,
  };
}
