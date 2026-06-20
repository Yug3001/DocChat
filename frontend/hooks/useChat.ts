import { useState, useCallback, useRef, useEffect } from "react";
import { Message, Source } from "@/lib/types";
import { v4 as uuidv4 } from "uuid";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useChat(sessionId: string, datasetId?: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Load persisted messages from backend for this session
  useEffect(() => {
    let active = true;
    
    async function fetchMessages() {
      try {
        const res = await fetch(`${BASE}/api/sessions/${sessionId}/messages`);
        if (res.ok) {
          const data = await res.json();
          if (active) {
            // map them to ensure streaming is false
            setMessages(data.map((m: any) => ({ ...m, isStreaming: false })));
          }
        } else {
          if (active) setMessages([]);
        }
      } catch (err) {
        if (active) setMessages([]);
      }
    }
    
    setMessages([]); // clear immediately on session switch
    if (sessionId) {
      fetchMessages();
    }
    
    return () => { active = false; };
  }, [sessionId]);

  const sendMessage = useCallback(
    async (text: string, documentIds?: string[] | null) => {
      if (!text.trim() || isLoading) return;

      const userMsg: Message = {
        id: uuidv4(),
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };
      const assistantId = uuidv4();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        sources: [],
        isStreaming: true,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsLoading(true);

      abortRef.current = new AbortController();

      try {
        const endpoint = datasetId ? `${BASE}/api/dataset/${datasetId}/chat` : `${BASE}/api/chat`;
        const payload = datasetId 
          ? { message: text, session_id: sessionId } 
          : { message: text, session_id: sessionId, document_ids: documentIds };

        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: abortRef.current.signal,
        });

        if (!res.ok) throw new Error("Chat request failed");

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (raw === "[DONE]") break;

            try {
              const chunk = JSON.parse(raw);
              if (chunk.type === "text") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: m.content + chunk.text }
                      : m
                  )
                );
              } else if (chunk.type === "sources") {
                 setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, sources: chunk.sources }
                      : m
                  )
                );
              } else if (chunk.type === "download") {
                // Backend emitted a download event after a successful Excel update
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, download_id: chunk.doc_id }
                      : m
                  )
                );
              } else if (chunk.type === "docx_edit_start") {
                // Backend signals this is a DOCX edit response — render in styled block
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, is_docx_edit: true }
                      : m
                  )
                );
              } else if (chunk.type === "json_payload") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, action: chunk.payload.action, payload: chunk.payload }
                      : m
                  )
                );
              } else if (chunk.type === "action") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, action: chunk.action, payload: chunk.payload }
                      : m
                  )
                );
              }
            } catch {}
          }
        }
      } catch (e: any) {
        if (e.name !== "AbortError") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: "Something went wrong. Please try again.",
                    isStreaming: false,
                  }
                : m
            )
          );
        }
      } finally {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, isStreaming: false } : m
          )
        );
        setIsLoading(false);
      }
    },
    [sessionId, isLoading, datasetId]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const appendAssistantMessage = useCallback(
    (content: string, extras?: Partial<Message>) => {
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          role: "assistant",
          content,
          timestamp: new Date().toISOString(),
          isStreaming: false,
          ...extras,
        },
      ]);
    },
    []
  );

  const clearMessageAction = useCallback((messageId: string) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId ? { ...m, action: undefined, payload: undefined } : m
      )
    );
  }, []);

  return {
    messages,
    isLoading,
    sendMessage,
    clearMessages,
    appendAssistantMessage,
    clearMessageAction,
  };
}