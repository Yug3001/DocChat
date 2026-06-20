"use client";
import { useEffect, useState, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatWindow from "@/components/ChatWindow";

const SESSION_KEY = "docchat_session";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    // Load or create the current session ID
    let id = localStorage.getItem(SESSION_KEY);
    if (!id) {
      id = uuidv4();
      localStorage.setItem(SESSION_KEY, id);
    }
    setSessionId(id);
  }, []);

  /**
   * Called by the "New Session" button in ChatWindow.
   * Generates a fresh UUID, stores it, and re-renders with the new session.
   * The old session's docs and chat remain in storage — fully isolated.
   */
  const handleNewSession = useCallback(() => {
    const newId = uuidv4();
    localStorage.setItem(SESSION_KEY, newId);
    setSessionId(newId);
  }, []);

  const handleSwitchSession = useCallback((id: string) => {
    localStorage.setItem(SESSION_KEY, id);
    setSessionId(id);
  }, []);

  if (!sessionId) return null;

  return <ChatWindow sessionId={sessionId} onNewSession={handleNewSession} onSwitchSession={handleSwitchSession} />;
}