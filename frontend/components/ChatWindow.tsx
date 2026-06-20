"use client";
import { useEffect, useRef, useState } from "react";
import {
  Send, RotateCcw, Menu, X, Zap,
  BookOpen, MessageSquare, ListChecks, BarChart3,
  ChevronRight, ArrowUpRight, Bot, FileText, Hash, Layers, Clock, PlusCircle, Globe, Database
} from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";
import MessageBubble from "./MessageBubble";
import FileUpload from "./FileUpload";
import WebsiteInput from "./WebsiteInput";
import DocumentList from "./DocumentList";
import { DatasetLinker } from "./dataset/DatasetLinker";
import { useDataset } from "@/hooks/useDataset";
import { useDatasetsList } from "@/hooks/useDatasetsList";
import { DatasetCard } from "./dataset/DatasetCard";
import { DatasetPreviewPanel } from "./dataset/DatasetPreviewPanel";
import { MutationHistoryPanel } from "./dataset/MutationHistoryPanel";
import { ChatConfirmDialog } from "./dataset/ChatConfirmDialog";

/* ─── Quick Actions ──────────────────────────────────── */
const QUICK_ACTIONS = [
  {
    icon: BookOpen, label: "Summarize", sub: "Get a concise overview",
    prompt: "Please provide a comprehensive summary of the uploaded documents.",
    color: "#4f46e5",
  },
  {
    icon: MessageSquare, label: "Ask Questions", sub: "Interactive Q&A mode",
    prompt: "What are the main topics covered in these documents?",
    color: "#7c3aed",
  },
  {
    icon: ListChecks, label: "Key Points", sub: "Extract critical insights",
    prompt: "Extract the most important key points and findings from these documents.",
    color: "#0891b2",
  },
  {
    icon: BarChart3, label: "Generate Report", sub: "Full structured report",
    prompt: "Generate a detailed structured report with sections for overview, key findings, analysis, and recommendations.",
    color: "#059669",
  },
];

/* ─── Light Theme Styles ─────────────────────────────── */
const S = {
  bg:          "#f4f6ff",          // page background — soft lavender-white
  sidebar:     "#eceffe",          // sidebar background
  border:      "rgba(79,70,229,0.1)",
  primary:     "#4f46e5",          // vivid indigo
  secondary:   "#7c3aed",          // violet
  card:        "#ffffff",          // white card surfaces
  cardHover:   "#f8f8ff",          // hover card
  text:        "#1e1b4b",          // deep indigo-black
  muted:       "#6b7280",          // cool grey
  faint:       "#9ca3af",          // lightest text
  surface:     "#ffffff",
  topbar:      "rgba(255,255,255,0.85)",
  inputBg:     "#ffffff",
};

/* ─── Responsive hooks ───────────────────────────────── */
function useIsMobile() {
  const [v, setV] = useState(false);
  useEffect(() => {
    const fn = () => setV(window.innerWidth < 768);
    fn(); window.addEventListener("resize", fn);
    return () => window.removeEventListener("resize", fn);
  }, []);
  return v;
}
function useIsTablet() {
  const [v, setV] = useState(false);
  useEffect(() => {
    const fn = () => setV(window.innerWidth >= 768 && window.innerWidth < 1024);
    fn(); window.addEventListener("resize", fn);
    return () => window.removeEventListener("resize", fn);
  }, []);
  return v;
}

export default function ChatWindow({
  sessionId,
  onNewSession,
  onSwitchSession,
}: {
  sessionId: string;
  onNewSession?: () => void;
  onSwitchSession?: (id: string) => void;
}) {
  const [input, setInput] = useState("");
  const [view, setView] = useState<"dashboard" | "chat">("dashboard");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isMobile = useIsMobile();
  const isTablet = useIsTablet();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mode, setMode] = useState<"chat" | "docs" | "medical" | "web" | "database">("chat");
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && sessionId) {
      setActiveDatasetId(localStorage.getItem(`activeDatasetId_${sessionId}`) || null);
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId) {
      if (activeDatasetId) {
        localStorage.setItem(`activeDatasetId_${sessionId}`, activeDatasetId);
      } else {
        localStorage.removeItem(`activeDatasetId_${sessionId}`);
      }
    }
  }, [activeDatasetId, sessionId]);

  useEffect(() => {
    if (mode !== "database") {
      setActiveDatasetId(null);
    }
  }, [mode]);

  useEffect(() => { setSidebarOpen(!isMobile); }, [isMobile]);

  const { messages, isLoading, sendMessage, clearMessages, appendAssistantMessage, clearMessageAction } = useChat(sessionId, activeDatasetId);
  const { documents, uploading, uploadError, scraping, scrapeError, loadDocuments, upload, uploadMedical, scrapeUrl, remove } = useDocuments(sessionId);
  const { datasetMeta, schema, rowCount, previewData, history, loading: datasetLoading, confirmMutation, undoMutation, syncSchema } = useDataset(activeDatasetId);
  const { datasets } = useDatasetsList();

  const [sessions, setSessions] = useState<{id: string, title: string, updated_at: string, session_type?: string}[]>([]);
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sessions?session_type=${mode}`)
      .then(res => res.json())
      .then(data => {
         if (Array.isArray(data)) setSessions(data);
      })
      .catch(() => {});
  }, [sessionId, messages.length, documents.length, mode]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sessions`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          const current = data.find(s => s.id === sessionId);
          if (current && current.session_type) {
            setMode(current.session_type);
          }
        }
      })
      .catch(() => {});
  }, [sessionId]);

  useEffect(() => { loadDocuments(); }, [loadDocuments]);
  useEffect(() => { if (messages.length > 0) setView("chat"); }, [sessionId]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => { if (messages.length > 0 && view !== "chat") setView("chat"); }, [messages.length]);

  // Load preview data when dataset changes or view switches to chat
  useEffect(() => {
    if (activeDatasetId && view === "chat") {
      // Data is loaded by useDataset hooks internally when activeDatasetId is set,
      // but if we need a trigger, we can just rely on the hook's own effects.
    }
  }, [activeDatasetId, view]);

  const handleNewSession = () => {
    setView(mode === "chat" ? "chat" : "dashboard"); setInput("");
    if (isMobile) setSidebarOpen(false);
    onNewSession?.();
  };
  const handleSwitchMode = async (newMode: typeof mode) => {
    setMode(newMode);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sessions?session_type=${newMode}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          onSwitchSession?.(data[0].id);
          setView("chat");
        } else {
          onNewSession?.();
          setView(newMode === "chat" ? "chat" : "dashboard");
        }
      }
    } catch {
      onNewSession?.();
      setView(newMode === "chat" ? "chat" : "dashboard");
    }
    if (isMobile) setSidebarOpen(false);
  };
  const handleSend = (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || isLoading) return;
    setView("chat");
    if (isMobile) setSidebarOpen(false);
    const docIds = readyDocs.map((d) => d.id);
    sendMessage(msg, docIds.length > 0 ? docIds : null);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px";
  };

  const readyDocs = documents.filter((d) => d.status?.toLowerCase() === "ready");
  const qaColumns = isMobile ? "1fr 1fr" : isTablet ? "1fr 1fr" : "repeat(4,1fr)";
  const inputPadding = isMobile ? "0 12px 16px" : "0 24px 24px";
  const contentPadding = isMobile ? "16px 12px 180px" : isTablet ? "24px 20px 190px" : "32px 28px 200px";
  const bannerPadding = isMobile ? "20px 20px" : "28px 32px";

  return (
    <div style={{
      display: "flex", height: "100dvh", width: "100vw",
      background: S.bg, overflow: "hidden", position: "relative",
      fontFamily: "'Inter', sans-serif",
    }}>

      {/* ── Ambient light decorations ─────────────────── */}
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden" }}>
        <div style={{ position: "absolute", width: 600, height: 600, top: -200, right: -100, borderRadius: "50%", background: "radial-gradient(circle, rgba(79,70,229,0.07) 0%, transparent 65%)", filter: "blur(60px)" }} />
        <div style={{ position: "absolute", width: 500, height: 500, bottom: -150, left: -80, borderRadius: "50%", background: "radial-gradient(circle, rgba(124,58,237,0.06) 0%, transparent 65%)", filter: "blur(60px)" }} />
      </div>

      {/* ── Mobile tap-to-close overlay ────────────────── */}
      {isMobile && sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{ position: "fixed", inset: 0, background: "rgba(30,27,75,0.25)", backdropFilter: "blur(3px)", zIndex: 40 }}
        />
      )}

      {/* ══════════════════════════════════════════════
          SIDEBAR
      ══════════════════════════════════════════════ */}
      <aside style={{
        ...(isMobile ? {
          position: "fixed", top: 0, left: 0,
          height: "100dvh", zIndex: 50,
          transform: sidebarOpen ? "translateX(0)" : "translateX(-100%)",
          transition: "transform 0.3s ease", width: 264,
        } : {
          position: "relative",
          width: sidebarOpen ? 264 : 0,
          minWidth: sidebarOpen ? 264 : 0,
          height: "100dvh", flexShrink: 0,
          transition: "width 0.3s ease, min-width 0.3s ease", zIndex: 20,
        }),
        display: "flex", flexDirection: "column",
        background: S.sidebar,
        borderRight: `1px solid ${S.border}`,
        overflow: "hidden",
        boxShadow: isMobile && sidebarOpen ? "4px 0 24px rgba(79,70,229,0.1)" : "none",
      }}>
        <div style={{ width: 264, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>

          {/* Logo row */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "20px 20px 16px", borderBottom: `1px solid ${S.border}`, flexShrink: 0 }}>
            <div style={{ position: "relative", flexShrink: 0 }}>
              <div style={{ position: "absolute", inset: -2, borderRadius: 14, background: "linear-gradient(135deg,#4f46e5,#7c3aed)", filter: "blur(8px)", opacity: 0.3 }} />
              <div style={{ position: "relative", width: 36, height: 36, borderRadius: 12, overflow: "hidden", border: "2px solid rgba(79,70,229,0.25)", background: "#fff" }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/icon.png" alt="DocChat" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: S.text, letterSpacing: "-0.02em" }}>
                Doc<span style={{ color: "#d946ef" }}>Chat</span>
              </div>
              <div style={{ fontSize: 10, color: S.primary, fontWeight: 700, letterSpacing: "0.1em" }}>RAG Assistant ✦</div>
            </div>
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(false)}
                style={{ padding: 6, borderRadius: 8, background: "rgba(79,70,229,0.08)", border: "none", color: S.muted, cursor: "pointer", display: "flex" }}
              >
                <X size={16} />
              </button>
            )}
          </div>

          {/* Nav */}
          <nav style={{ padding: "12px 12px 0", flexShrink: 0 }}>
            {([
              { value: "chat", label: "Chat", icon: MessageSquare },
              { value: "docs", label: "Docs", icon: FileText },
              { value: "medical", label: "Medical", icon: PlusCircle },
              { value: "web", label: "Web", icon: Globe },
              { value: "database", label: "Database", icon: Database }
            ] as const).map((item) => {
              const Icon = item.icon;
              const active = mode === item.value;
              return (
                <button
                  key={item.value}
                  onClick={() => handleSwitchMode(item.value)}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", gap: 10,
                    padding: "10px 12px", borderRadius: 12, marginBottom: 4,
                    background: active ? "rgba(79,70,229,0.1)" : "transparent",
                    border: `1px solid ${active ? "rgba(79,70,229,0.2)" : "transparent"}`,
                    color: active ? S.primary : S.muted,
                    fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "all 0.15s",
                  }}
                  onMouseEnter={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = "rgba(79,70,229,0.06)"; (e.currentTarget as HTMLElement).style.color = S.primary; } }}
                  onMouseLeave={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = S.muted; } }}
                >
                  <Icon size={16} />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Datasets List */}
          {datasets.length > 0 && (
            <div style={{ padding: "12px 12px 0", flexShrink: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                <Database size={11} color={S.faint} />
                <span style={{ fontSize: 10, color: S.faint, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" }}>My Datasets</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {datasets.map(ds => {
                  const isActive = activeDatasetId === ds.dataset_id;
                  return (
                    <button
                      key={ds.dataset_id}
                      onClick={() => {
                        setActiveDatasetId(ds.dataset_id);
                        setView("chat");
                        if (isMobile) setSidebarOpen(false);
                      }}
                      style={{
                        display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 10,
                        background: isActive ? "rgba(5, 150, 105, 0.08)" : "transparent",
                        border: `1px solid ${isActive ? "rgba(5, 150, 105, 0.2)" : "transparent"}`,
                        color: isActive ? "#064e3b" : S.muted,
                        cursor: "pointer", textAlign: "left", transition: "all 0.15s"
                      }}
                      onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "rgba(79,70,229,0.04)" }}
                      onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = "transparent" }}
                    >
                      <Database size={14} color={isActive ? "#059669" : S.faint} />
                      <div style={{ flex: 1, fontSize: 12, fontWeight: isActive ? 600 : 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {ds.display_name}
                      </div>
                      <div style={{ fontSize: 9, padding: "2px 4px", borderRadius: 4, background: isActive ? "#05966920" : S.border, color: isActive ? "#064e3b" : S.faint, fontWeight: 700 }}>
                        {ds.source_type}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Recent sessions */}
          <div style={{ padding: "16px 12px 8px", flex: 1, overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
              <Clock size={11} color={S.faint} />
              <span style={{ fontSize: 10, color: S.faint, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" }}>Recent Sessions</span>
            </div>
            <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
              {sessions.map(s => (
                <button
                  key={s.id}
                  onClick={() => { onSwitchSession?.(s.id); if (isMobile) setSidebarOpen(false); }}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", gap: 8,
                    padding: "10px", borderRadius: 12, marginBottom: 4,
                    background: sessionId === s.id ? "rgba(79,70,229,0.1)" : "transparent",
                    border: "1px solid transparent",
                    color: sessionId === s.id ? S.primary : S.text,
                    fontSize: 12, fontWeight: 600, cursor: "pointer", transition: "all 0.15s",
                    textAlign: "left"
                  }}
                  onMouseEnter={e => { if (sessionId !== s.id) { (e.currentTarget as HTMLElement).style.background = "rgba(79,70,229,0.04)"; } }}
                  onMouseLeave={e => { if (sessionId !== s.id) { (e.currentTarget as HTMLElement).style.background = "transparent"; } }}
                >
                  <MessageSquare size={13} style={{ color: sessionId === s.id ? S.primary : S.faint, flexShrink: 0 }} />
                  <div style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</div>
                </button>
              ))}
              {sessions.length === 0 && (
                 <div style={{ fontSize: 11, color: S.faint, textAlign: "center", marginTop: 20 }}>No past sessions</div>
              )}
            </div>
          </div>

          {/* Stats */}
          <div style={{ padding: "0 12px 16px", flexShrink: 0 }}>
            <div style={{ fontSize: 10, color: S.faint, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10, paddingLeft: 4 }}>Overview</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {[
                { icon: FileText, label: "Docs", value: documents.length, color: S.primary },
                { icon: Hash, label: "Ready", value: readyDocs.length, color: S.secondary },
              ].map(({ icon: Icon, label, value, color }) => (
                <div
                  key={label}
                  style={{ padding: "10px 12px", borderRadius: 12, background: S.card, border: `1px solid ${S.border}`, display: "flex", alignItems: "center", gap: 10, transition: "all 0.2s", boxShadow: "0 1px 4px rgba(79,70,229,0.06)" }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 2px 12px rgba(79,70,229,0.12)"; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 1px 4px rgba(79,70,229,0.06)"; }}
                >
                  <div style={{ width: 30, height: 30, borderRadius: 9, background: `${color}12`, border: `1px solid ${color}22`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Icon size={14} color={color} />
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: S.faint }}>{label}</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: S.text, lineHeight: 1 }}>{value}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </aside>

      {/* ══════════════════════════════════════════════
          MAIN AREA
      ══════════════════════════════════════════════ */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, position: "relative", zIndex: 10, height: "100dvh", overflow: "hidden" }}>

        {/* Topbar */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: isMobile ? "10px 14px" : "12px 24px", flexShrink: 0,
          background: S.topbar, backdropFilter: "blur(20px)",
          borderBottom: `1px solid ${S.border}`,
          boxShadow: "0 1px 0 rgba(79,70,229,0.06)",
          gap: 8,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: isMobile ? 10 : 14, minWidth: 0 }}>
            <button
              onClick={() => setSidebarOpen(v => !v)}
              style={{ padding: 8, borderRadius: 10, background: "rgba(79,70,229,0.06)", border: `1px solid ${S.border}`, color: S.muted, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.15s", flexShrink: 0 }}
              onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.color = S.primary; el.style.background = "rgba(79,70,229,0.1)"; }}
              onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.color = S.muted; el.style.background = "rgba(79,70,229,0.06)"; }}
            >
              <Menu size={18} />
            </button>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: isMobile ? 14 : 17, fontWeight: 800, color: S.text, letterSpacing: "-0.02em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {view === "dashboard" ? "Dashboard" : readyDocs.length > 0 ? `Chatting with ${readyDocs.length} file${readyDocs.length > 1 ? "s" : ""}` : "Ready to assist"}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: isMobile ? 6 : 8, flexShrink: 0 }}>
            {isLoading && (
              <div style={{ display: "flex", alignItems: "center", gap: 7, padding: "5px 10px", borderRadius: 10, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)" }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#f59e0b", animation: "pulse-dot 1.4s ease-in-out infinite" }} />
                {!isMobile && <span style={{ fontSize: 12, color: "#d97706", fontWeight: 600 }}>Processing…</span>}
              </div>
            )}
            <button
              onClick={handleNewSession}
              title="New session"
              style={{ display: "flex", alignItems: "center", gap: 5, padding: isMobile ? "6px 10px" : "6px 12px", borderRadius: 10, background: "rgba(79,70,229,0.07)", border: `1px solid ${S.border}`, fontSize: 12, fontWeight: 600, color: S.muted, cursor: "pointer", transition: "all 0.15s" }}
              onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.color = S.primary; el.style.background = "rgba(79,70,229,0.12)"; el.style.borderColor = "rgba(79,70,229,0.25)"; }}
              onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.color = S.muted; el.style.background = "rgba(79,70,229,0.07)"; el.style.borderColor = S.border; }}
            >
              <PlusCircle size={13} />
              {!isMobile && " New Session"}
            </button>
            {messages.length > 0 && view === "chat" && (
              <button
                onClick={clearMessages}
                style={{ display: "flex", alignItems: "center", gap: 5, padding: isMobile ? "6px 10px" : "6px 12px", borderRadius: 10, background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.12)", fontSize: 12, fontWeight: 600, color: S.muted, cursor: "pointer", transition: "all 0.15s" }}
                onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.color = "#dc2626"; el.style.background = "rgba(239,68,68,0.1)"; }}
                onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.color = S.muted; el.style.background = "rgba(239,68,68,0.05)"; }}
              >
                <RotateCcw size={13} />
                {!isMobile && " Clear Chat"}
              </button>
            )}
          </div>
        </div>

        {/* ── Scrollable content ─────────────────────── */}
        <div style={{ flex: 1, overflowY: "auto", overflowX: "hidden", position: "relative" }}>

          {/* ════ DASHBOARD ════════════════════════════ */}
          {view === "dashboard" && (
            <div style={{ maxWidth: 1100, margin: "0 auto", padding: contentPadding }}>

              {/* Welcome banner */}
              <div style={{
                position: "relative", overflow: "hidden",
                borderRadius: isMobile ? 16 : 22,
                padding: bannerPadding, marginBottom: isMobile ? 20 : 24,
                background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
                boxShadow: "0 8px 32px rgba(79,70,229,0.25)",
              }}>
                {/* decorative circles */}
                <div style={{ position: "absolute", width: 300, height: 300, top: -120, right: -60, borderRadius: "50%", background: "rgba(255,255,255,0.06)", pointerEvents: "none" }} />
                <div style={{ position: "absolute", width: 200, height: 200, bottom: -80, right: 80, borderRadius: "50%", background: "rgba(255,255,255,0.04)", pointerEvents: "none" }} />
                <div style={{ position: "relative" }}>
                  <h2 style={{ fontSize: isMobile ? 20 : 26, fontWeight: 900, color: "#fff", margin: "0 0 10px", letterSpacing: "-0.03em" }}>
                    Welcome to DocChat ✦
                  </h2>
                  <p style={{ fontSize: isMobile ? 13 : 14, color: "rgba(255,255,255,0.75)", lineHeight: 1.65, margin: 0, maxWidth: 480 }}>
                    Upload your documents and instantly get AI-powered summaries, answers, and insights with full source citations.
                  </p>
                </div>
              </div>

              {/* Upload or Web Scrape based on active mode */}
              <div style={{ marginBottom: isMobile ? 20 : 24 }}>
                {mode === "docs" && (
                  <>
                    <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
                      <SectionLabel icon={ArrowUpRight} label="Upload Documents" color={S.primary} />
                    </div>
                    <FileUpload onUpload={upload} uploading={uploading} error={uploadError} />
                  </>
                )}
                {mode === "web" && (
                  <>
                    <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
                      <SectionLabel icon={Globe} label="Scrape Website" color={S.primary} />
                    </div>
                    <WebsiteInput onScrape={scrapeUrl} scraping={scraping} error={scrapeError} />
                  </>
                )}
                {mode === "medical" && (
                  <>
                    <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
                      <SectionLabel icon={PlusCircle} label="Upload Medical Image" color="#dc2626" />
                    </div>
                    <FileUpload onUpload={uploadMedical} uploading={uploading} error={uploadError} />
                  </>
                )}
                {mode === "database" && (
                  <>
                    <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
                      <SectionLabel icon={Database} label="Connect Dataset" color="#059669" />
                    </div>
                    <DatasetLinker onDatasetLinked={(id) => { 
                      setActiveDatasetId(id); 
                      setView("chat"); 
                    }} />
                  </>
                )}
                {mode === "chat" && (
                  <div style={{ textAlign: "center", padding: "40px 20px", background: "rgba(79,70,229,0.03)", borderRadius: 16, border: `1px dashed ${S.border}` }}>
                    <MessageSquare size={32} color={S.primary} style={{ display: "block", margin: "0 auto 12px" }} />
                    <p style={{ fontSize: 14, fontWeight: 600, color: S.text, margin: "0 0 4px" }}>General Chat Mode</p>
                    <p style={{ fontSize: 12, color: S.muted, margin: 0 }}>Start typing below to chat with the assistant directly.</p>
                  </div>
                )}
              </div>

              {/* Active Dataset Overview in Dashboard */}
              {activeDatasetId && datasetMeta && view === "dashboard" && (
                <div style={{ marginBottom: 24 }}>
                  <DatasetCard dataset={datasetMeta} onSync={syncSchema} syncing={datasetLoading} />
                </div>
              )}

              {/* Uploaded Files */}
              {documents.length > 0 && (
                <div style={{ marginBottom: isMobile ? 20 : 24 }}>
                  <SectionLabel icon={Layers} label="Your Files" color={S.primary} />
                  <DocumentList documents={documents} onDelete={remove} />
                </div>
              )}

              {/* Quick Actions */}
              <div>
                <div style={{ marginBottom: readyDocs.length === 0 ? 10 : 16 }}>
                  <SectionLabel icon={Zap} label="Quick Actions" color="#d97706" />
                </div>
                {readyDocs.length === 0 && (
                  <div style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "10px 16px", marginBottom: 16, borderRadius: 12,
                    background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)",
                  }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#f59e0b", flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: "#d97706", fontWeight: 600 }}>
                      Please upload a document above to enable Quick Actions.
                    </span>
                  </div>
                )}
                <div style={{ display: "grid", gridTemplateColumns: qaColumns, gap: isMobile ? 10 : 14 }}>
                  {QUICK_ACTIONS.map(({ icon: Icon, label, sub, prompt, color }) => (
                    <button
                      key={label}
                      disabled={readyDocs.length === 0}
                      onClick={() => handleSend(prompt)}
                      style={{
                        position: "relative", overflow: "hidden",
                        borderRadius: isMobile ? 14 : 18,
                        padding: isMobile ? 14 : 18, textAlign: "left",
                        background: "#fff",
                        border: `1.5px solid rgba(79,70,229,0.1)`,
                        cursor: readyDocs.length === 0 ? "not-allowed" : "pointer",
                        transition: "all 0.2s",
                        boxShadow: "0 1px 6px rgba(79,70,229,0.06)",
                        opacity: readyDocs.length === 0 ? 0.85 : 1,
                      }}
                      onMouseEnter={e => {
                        if (readyDocs.length > 0) {
                          const el = e.currentTarget as HTMLElement;
                          el.style.transform = "translateY(-3px)";
                          el.style.boxShadow = `0 8px 28px ${color}22`;
                          el.style.borderColor = `${color}35`;
                        }
                      }}
                      onMouseLeave={e => {
                        const el = e.currentTarget as HTMLElement;
                        el.style.transform = "translateY(0)";
                        el.style.boxShadow = "0 1px 6px rgba(79,70,229,0.06)";
                        el.style.borderColor = "rgba(79,70,229,0.1)";
                      }}
                    >
                      {/* Colored top accent strip */}
                      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg, ${color}, ${color}88)`, borderRadius: "18px 18px 0 0" }} />
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: isMobile ? 10 : 14, marginTop: 6 }}>
                        <div style={{ width: isMobile ? 32 : 38, height: isMobile ? 32 : 38, borderRadius: 10, background: `${color}12`, border: `1px solid ${color}22`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Icon size={isMobile ? 15 : 18} color={color} />
                        </div>
                        <ChevronRight size={13} color={S.faint} />
                      </div>
                      <div style={{ fontSize: isMobile ? 13 : 14, fontWeight: 700, color: S.text, marginBottom: 3 }}>{label}</div>
                      <div style={{ fontSize: isMobile ? 10 : 11, color: "#475569", lineHeight: 1.4 }}>{sub}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ════ CHAT ════════════════════════════════ */}
          {view === "chat" && (
            <div style={{ maxWidth: 780, margin: "0 auto", padding: contentPadding }}>
              
              {activeDatasetId && datasetMeta && schema && (
                <div style={{ 
                  display: "grid", 
                  gridTemplateColumns: isMobile ? "1fr" : "260px 1fr", 
                  gap: "16px", 
                  marginBottom: 20, 
                  alignItems: "start" 
                }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <DatasetCard dataset={datasetMeta} onSync={syncSchema} syncing={datasetLoading} />
                    {history.length > 0 && (
                      <MutationHistoryPanel history={history} onUndo={undoMutation} undoing={datasetLoading} />
                    )}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", overflow: "hidden" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: S.faint, letterSpacing: "0.05em", textTransform: "uppercase" }}>Dataset Preview (First 50 Rows)</div>
                    <DatasetPreviewPanel data={previewData} columns={schema.columns || []} />
                  </div>
                </div>
              )}

              {messages.length === 0 ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: 400, textAlign: "center", padding: "0 16px" }}>
                  <div className="animate-float" style={{ width: isMobile ? 64 : 76, height: isMobile ? 64 : 76, borderRadius: 22, background: "linear-gradient(135deg,rgba(79,70,229,0.1),rgba(124,58,237,0.08))", border: "1.5px solid rgba(79,70,229,0.15)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 20 }}>
                    <Bot size={isMobile ? 28 : 34} color={S.primary} strokeWidth={1.5} />
                  </div>
                  <h3 style={{ fontSize: isMobile ? 18 : 22, fontWeight: 800, color: S.text, marginBottom: 10, letterSpacing: "-0.02em" }}>Start a conversation</h3>
                  <p style={{ fontSize: isMobile ? 13 : 14, color: S.muted, lineHeight: 1.7, maxWidth: 360, marginBottom: 20 }}>
                    {activeDatasetId ? "Ask anything about your active dataset below." : readyDocs.length > 0 ? "Ask anything about your uploaded documents below." : "Upload documents first, then come back to chat with them."}
                  </p>
                  {readyDocs.length === 0 && !activeDatasetId && (
                    <button
                      onClick={() => setView("dashboard")}
                      style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "10px 20px", borderRadius: 12, fontSize: 13, fontWeight: 600, color: S.primary, background: "rgba(79,70,229,0.08)", border: "1.5px solid rgba(79,70,229,0.2)", cursor: "pointer", transition: "all 0.15s" }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(79,70,229,0.14)"; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "rgba(79,70,229,0.08)"; }}
                    >
                      <ArrowUpRight size={15} /> Go to Dashboard
                    </button>
                  )}
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: isMobile ? 14 : 20 }}>
                  {messages.map((msg, i) => (
                    <div key={msg.id} className="animate-fade-up" style={{ animationDelay: `${Math.min(i * 0.04, 0.2)}s` }}>
                      <MessageBubble message={msg} />
                      
                      {msg.action === "REQUIRE_CONFIRMATION" && msg.payload && (
                        <ChatConfirmDialog
                          payload={msg.payload}
                          confirming={datasetLoading}
                          onConfirm={async (req) => {
                            try {
                              const result = await confirmMutation(req);
                              clearMessageAction(msg.id);
                              const rowsAffected = result?.rows_affected ?? 0;
                              const version = result?.version ?? datasetMeta?.version;
                              let successText = `✅ **Changes applied successfully!**\n\n`;
                              successText += `- Rows affected: ${rowsAffected}\n`;
                              if (version != null) successText += `- Dataset version: v${version}\n`;
                              successText += `\nYour dataset has been updated.`;
                              appendAssistantMessage(successText, {
                                dataset_download_id:
                                  result?.source_type === "CSV" ? activeDatasetId ?? undefined : undefined,
                              });
                            } catch (e: any) {
                              appendAssistantMessage(
                                `❌ **Execution failed:** ${e?.message || "Could not apply the changes. Please try again."}`
                              );
                            }
                          }}
                          onCancel={() => {
                            clearMessageAction(msg.id);
                            appendAssistantMessage("Operation cancelled. No changes were made to the dataset.");
                          }}
                        />
                      )}
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Floating input ──────────────────────────── */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          padding: inputPadding,
          background: `linear-gradient(to top, ${S.bg} 60%, transparent)`,
        }}>
          <div style={{ maxWidth: 780, margin: "0 auto" }}>
            {/* Quick chips */}
            {!isMobile && view === "dashboard" && readyDocs.length > 0 && (
              <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
                {QUICK_ACTIONS.map(({ label, prompt, color }) => (
                  <button
                    key={label}
                    onClick={() => handleSend(prompt)}
                    style={{ display: "flex", alignItems: "center", gap: 5, padding: "5px 12px", borderRadius: 10, fontSize: 12, fontWeight: 600, color, background: `${color}0d`, border: `1px solid ${color}25`, cursor: "pointer", transition: "all 0.15s" }}
                    onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = `${color}18`; el.style.borderColor = `${color}45`; }}
                    onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = `${color}0d`; el.style.borderColor = `${color}25`; }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            {/* Input box */}
            <div
              id="input-box"
              style={{
                background: S.inputBg,
                border: `1.5px solid rgba(79,70,229,0.15)`,
                borderRadius: isMobile ? 14 : 18,
                backdropFilter: "blur(20px)",
                padding: isMobile ? "10px 12px" : "12px 14px",
                transition: "border-color 0.2s, box-shadow 0.2s",
                boxShadow: "0 2px 12px rgba(79,70,229,0.08)",
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={handleChange}
                  onKeyDown={handleKey}
                  onFocus={() => {
                    const el = document.getElementById("input-box");
                    if (el) { el.style.borderColor = "rgba(79,70,229,0.45)"; el.style.boxShadow = "0 0 0 3px rgba(79,70,229,0.08), 0 2px 12px rgba(79,70,229,0.1)"; }
                  }}
                  onBlur={() => {
                    const el = document.getElementById("input-box");
                    if (el) { el.style.borderColor = "rgba(79,70,229,0.15)"; el.style.boxShadow = "0 2px 12px rgba(79,70,229,0.08)"; }
                  }}
                  placeholder={activeDatasetId ? "Ask anything about your dataset..." : readyDocs.length > 0 ? "Ask anything about your documents…" : ""}
                  disabled={(readyDocs.length === 0 && !activeDatasetId) || isLoading}
                  rows={1}
                  style={{
                    flex: 1, background: "transparent", color: S.text,
                    resize: "none", outline: "none",
                    fontSize: isMobile ? 16 : 14, lineHeight: 1.6,
                    minHeight: 40, maxHeight: 120,
                    fontFamily: "inherit", caretColor: S.primary,
                    border: "none",
                  }}
                  className="placeholder:text-gray-400 disabled:opacity-40 disabled:cursor-not-allowed"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || isLoading || (readyDocs.length === 0 && !activeDatasetId)}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    width: isMobile ? 40 : 44, height: isMobile ? 40 : 44, flexShrink: 0,
                    borderRadius: isMobile ? 10 : 12,
                    background: "linear-gradient(135deg,#4f46e5,#7c3aed)",
                    color: "#fff", border: "none",
                    opacity: !input.trim() || isLoading || (readyDocs.length === 0 && !activeDatasetId) ? 0.35 : 1,
                    cursor: !input.trim() || isLoading || (readyDocs.length === 0 && !activeDatasetId) ? "not-allowed" : "pointer",
                    transition: "all 0.2s",
                    boxShadow: "0 2px 8px rgba(79,70,229,0.3)",
                  }}
                  onMouseEnter={e => {
                    if (input.trim() && !isLoading && (readyDocs.length > 0 || activeDatasetId)) {
                      const el = e.currentTarget as HTMLElement;
                      el.style.transform = "translateY(-1px) scale(1.05)";
                      el.style.boxShadow = "0 6px 20px rgba(79,70,229,0.45)";
                    }
                  }}
                  onMouseLeave={e => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.transform = "translateY(0) scale(1)";
                    el.style.boxShadow = "0 2px 8px rgba(79,70,229,0.3)";
                  }}
                >
                  {isLoading
                    ? <div className="animate-spin" style={{ width: 16, height: 16, border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "#fff", borderRadius: "50%" }} />
                    : <Send size={isMobile ? 14 : 16} strokeWidth={2.5} />
                  }
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

/* ── Section Label Helper ──────────────────────────── */
function SectionLabel({ icon: Icon, label, color }: { icon: any; label: string; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
      <div style={{ width: 22, height: 22, borderRadius: 7, background: `${color}12`, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Icon size={12} color={color} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 700, color: "#6b7280" }}>{label}</span>
    </div>
  );
}
