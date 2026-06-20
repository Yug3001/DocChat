import ReactMarkdown from "react-markdown";
import { Message } from "@/lib/types";
import { Sparkles, Download } from "lucide-react";
import SourceCitations from "./SourceCitations";
import DocxEditBlock from "./DocxEditBlock";
import { getDownloadUrl } from "@/lib/datasetApi";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatTimestamp(ts?: string): string {
  if (!ts) return "";
  const d = new Date(ts);
  const day = d.getDate();
  const month = d.toLocaleString("en-GB", { month: "long" });
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  return `${day} ${month}, ${year} · ${hours}:${mins}`;
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const timeLabel = formatTimestamp(message.timestamp);

  /* ─── USER BUBBLE ─────────────────────────────── */
  if (isUser) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div style={{ maxWidth: "85%", position: "relative" }}>
          <div
            style={{
              position: "relative",
              background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
              borderRadius: "18px 18px 4px 18px",
              padding: "12px 18px",
              fontSize: 14,
              color: "#fff",
              fontWeight: 500,
              lineHeight: 1.6,
              boxShadow: "0 4px 20px rgba(79,70,229,0.28)",
              wordBreak: "break-word",
              overflowWrap: "break-word",
            }}
          >
            {message.content}
          </div>
          {timeLabel && (
            <div style={{ textAlign: "right", marginTop: 4, fontSize: 10, color: "#9ca3af", letterSpacing: "0.02em" }}>
              {timeLabel}
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ─── AI BUBBLE ───────────────────────────────── */
  return (
    <div style={{ display: "flex", justifyContent: "flex-start" }}>
      <div style={{ width: "100%" }}>

        {/* AI header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <div style={{ position: "relative", flexShrink: 0 }}>
            <div
              style={{
                position: "relative",
                width: 36,
                height: 36,
                borderRadius: 12,
                background: "linear-gradient(135deg, rgba(79,70,229,0.12), rgba(124,58,237,0.08))",
                border: "1.5px solid rgba(79,70,229,0.2)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Sparkles size={16} style={{ color: "#4f46e5" }} strokeWidth={2} />
            </div>
          </div>
          <div>
            <p style={{ fontSize: 13, fontWeight: 700, color: "#1e1b4b" }}>DocChat AI</p>
            <p style={{ fontSize: 11, color: "#9ca3af", fontWeight: 600 }}>Powered by Groq · Llama 3.3</p>
          </div>
        </div>

        {/* Message body — DOCX edit responses get a special styled block */}
        {message.is_docx_edit ? (
          <DocxEditBlock
            content={message.content}
            isStreaming={message.isStreaming}
          />
        ) : (
          <div
            style={{
              background: "#ffffff",
              border: "1.5px solid rgba(79,70,229,0.1)",
              borderRadius: "4px 18px 18px 18px",
              padding: "14px 18px",
              position: "relative",
              overflow: "hidden",
              boxShadow: "0 2px 12px rgba(79,70,229,0.07)",
            }}
          >
            <div style={{ position: "relative" }}>
              {message.isStreaming && !message.content ? (
                <div style={{ display: "flex", gap: 8, alignItems: "center", padding: "8px 0" }}>
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="animate-pulse-dot"
                      style={{
                        width: 9,
                        height: 9,
                        borderRadius: "50%",
                        background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
                        animationDelay: `${i * 0.16}s`,
                        boxShadow: "0 0 6px rgba(79,70,229,0.4)",
                      }}
                    />
                  ))}
                </div>
              ) : (
                <div className="prose-chat max-w-none" style={{ fontSize: 14 }}>
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Download button — shown after successful Excel update or dataset mutation */}
        {message.download_id && !message.isStreaming && (
          <div style={{ marginTop: 10 }}>
            <a
              href={`${BASE}/api/download/${message.download_id}`}
              download
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "9px 18px",
                borderRadius: 12,
                background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                color: "#fff",
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 4px 14px rgba(16,185,129,0.35)",
                transition: "all 0.2s",
                cursor: "pointer",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
                (e.currentTarget as HTMLElement).style.boxShadow = "0 6px 20px rgba(16,185,129,0.45)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 14px rgba(16,185,129,0.35)";
              }}
            >
              <Download size={14} />
              Download Updated File
            </a>
          </div>
        )}

        {message.dataset_download_id && !message.isStreaming && (
          <div style={{ marginTop: 10 }}>
            <a
              href={getDownloadUrl(message.dataset_download_id)}
              download
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "9px 18px",
                borderRadius: 12,
                background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                color: "#fff",
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 4px 14px rgba(16,185,129,0.35)",
                transition: "all 0.2s",
                cursor: "pointer",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
                (e.currentTarget as HTMLElement).style.boxShadow = "0 6px 20px rgba(16,185,129,0.45)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 14px rgba(16,185,129,0.35)";
              }}
            >
              <Download size={14} />
              Download Updated Dataset (CSV)
            </a>
          </div>
        )}

        {/* Sources — only shown for RAG responses (when there are real citations) */}
        {message.sources && message.sources.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <SourceCitations sources={message.sources} />
          </div>
        )}

        {/* Timestamp */}
        {timeLabel && (
          <div style={{ textAlign: "left", marginTop: 4, fontSize: 10, color: "#9ca3af", letterSpacing: "0.02em", paddingLeft: 4 }}>
            {timeLabel}
          </div>
        )}
      </div>
    </div>
  );
}
