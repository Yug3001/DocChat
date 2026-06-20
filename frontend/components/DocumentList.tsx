"use client";
import { Document } from "@/lib/types";
import { FileText, Trash2, CheckCircle, Loader2, AlertCircle, Download, Globe } from "lucide-react";

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const day = d.getDate();
  const month = d.toLocaleString("en-GB", { month: "long" });
  const year = d.getFullYear();
  return `${day} ${month}, ${year}`;
}

const TYPE_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  pdf:     { text: "#ef4444", bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.2)" },
  docx:    { text: "#3b82f6", bg: "rgba(59,130,246,0.08)",  border: "rgba(59,130,246,0.2)" },
  xlsx:    { text: "#10b981", bg: "rgba(16,185,129,0.08)",  border: "rgba(16,185,129,0.2)" },
  xls:     { text: "#10b981", bg: "rgba(16,185,129,0.08)",  border: "rgba(16,185,129,0.2)" },
  png:     { text: "#8b5cf6", bg: "rgba(139,92,246,0.08)",  border: "rgba(139,92,246,0.2)" },
  jpg:     { text: "#f97316", bg: "rgba(249,115,22,0.08)",  border: "rgba(249,115,22,0.2)" },
  jpeg:    { text: "#f97316", bg: "rgba(249,115,22,0.08)",  border: "rgba(249,115,22,0.2)" },
  website: { text: "#0891b2", bg: "rgba(8,145,178,0.08)",   border: "rgba(8,145,178,0.2)" },
};
const DEFAULT_COLOR = { text: "#6b7280", bg: "rgba(107,114,128,0.08)", border: "rgba(107,114,128,0.2)" };

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function DocIcon({ fileType, size, color }: { fileType: string; size: number; color: string }) {
  if (fileType === "website") return <Globe size={size} style={{ color }} />;
  return <FileText size={size} style={{ color }} />;
}

interface Props {
  documents: Document[];
  onDelete: (id: string) => void;
  compact?: boolean;
  onSelect?: () => void;
}

export default function DocumentList({ documents, onDelete, compact = false, onSelect }: Props) {
  if (!documents.length) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-3 text-center"
        style={{ padding: compact ? "20px 12px" : "32px 16px" }}
      >
        <div
          className="flex items-center justify-center rounded-xl"
          style={{ width: compact ? 36 : 48, height: compact ? 36 : 48, background: "rgba(79,70,229,0.05)", border: "1px solid rgba(79,70,229,0.1)" }}
        >
          <FileText size={compact ? 16 : 22} style={{ color: "#4f46e5" }} />
        </div>
        <div>
          <p style={{ fontSize: compact ? 12 : 13, fontWeight: 600, color: "#6b7280", marginBottom: 3 }}>No documents yet</p>
          {!compact && <p style={{ fontSize: 11, color: "#9ca3af", lineHeight: 1.5 }}>Upload files or add a website URL to enable AI-powered Q&amp;A</p>}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: compact ? 4 : 8 }}>
      {documents.map((doc) => {
        const ext = (doc.file_type ?? doc.filename.split(".").pop() ?? "").toLowerCase();
        const colors = TYPE_COLORS[ext] ?? DEFAULT_COLOR;
        const isReady = doc.status?.toLowerCase() === "ready";
        const isProcessing = doc.status?.toLowerCase() === "processing";
        const isError = !isReady && !isProcessing;
        const isWebsite = ext === "website";

        /* ─── COMPACT ROW (sidebar) ─── */
        if (compact) {
          return (
            <div
              key={doc.id}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "8px 10px", borderRadius: 12,
                border: "1px solid transparent",
                cursor: onSelect ? "pointer" : "default",
                transition: "all 0.2s",
              }}
              onClick={() => onSelect?.()}
              onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(79,70,229,0.06)"; el.style.borderColor = "rgba(79,70,229,0.12)"; }}
              onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = "transparent"; el.style.borderColor = "transparent"; }}
            >
              <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", width: 28, height: 28, borderRadius: 8, background: colors.bg, border: `1px solid ${colors.border}` }}>
                <DocIcon fileType={ext} size={12} color={colors.text} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 11, fontWeight: 600, color: "#1e1b4b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: 2 }}>{doc.filename}</p>
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  {isReady && <CheckCircle size={9} style={{ color: "#10b981" }} />}
                  {isProcessing && <Loader2 size={9} style={{ color: "#f59e0b", animation: "spin 0.8s linear infinite" }} />}
                  {isError && <AlertCircle size={9} style={{ color: "#ef4444" }} />}
                  <span style={{ fontSize: 9, color: isReady ? "#10b981" : isProcessing ? "#f59e0b" : "#ef4444", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    {isReady ? "Ready" : isProcessing ? "Processing" : "Error"}
                  </span>
                  {isWebsite && (
                    <span style={{ fontSize: 9, color: "#0891b2", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginLeft: 2 }}>WEB</span>
                  )}
                </div>
              </div>
              <button
                onClick={e => { e.stopPropagation(); onDelete(doc.id); }}
                title="Delete document"
                style={{
                  flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
                  width: 26, height: 26, borderRadius: 8,
                  background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
                  cursor: "pointer", transition: "all 0.15s",
                }}
                onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(239,68,68,0.15)"; el.style.borderColor = "rgba(239,68,68,0.3)"; el.style.transform = "scale(1.1)"; }}
                onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(239,68,68,0.08)"; el.style.borderColor = "rgba(239,68,68,0.2)"; el.style.transform = "scale(1)"; }}
              >
                <Trash2 size={11} style={{ color: "#ef4444" }} />
              </button>
            </div>
          );
        }

        /* ─── FULL CARD (dashboard) ─── */
        return (
          <div
            key={doc.id}
            style={{
              display: "flex", alignItems: "center", gap: 12,
              padding: "12px 14px", borderRadius: 14,
              background: "#ffffff", border: "1px solid rgba(79,70,229,0.1)",
              boxShadow: "0 1px 4px rgba(79,70,229,0.05)",
              transition: "all 0.2s",
            }}
            onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = "#f8f8ff"; el.style.borderColor = "rgba(79,70,229,0.2)"; el.style.transform = "translateY(-1px)"; }}
            onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = "#ffffff"; el.style.borderColor = "rgba(79,70,229,0.1)"; el.style.transform = "translateY(0)"; }}
          >
            {/* Icon */}
            <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", width: 36, height: 36, borderRadius: 10, background: colors.bg, border: `1px solid ${colors.border}` }}>
              <DocIcon fileType={ext} size={16} color={colors.text} />
            </div>

            {/* Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: "#1e1b4b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", margin: 0, flex: 1 }}>
                  {doc.filename}
                </p>
                {isWebsite && (
                  <span style={{
                    fontSize: 9, fontWeight: 800, letterSpacing: "0.1em",
                    textTransform: "uppercase", padding: "2px 7px",
                    borderRadius: 6, flexShrink: 0,
                    background: "rgba(8,145,178,0.1)",
                    border: "1px solid rgba(8,145,178,0.2)",
                    color: "#0891b2",
                  }}>WEB</span>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                {/* Status badge */}
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  {isReady && <CheckCircle size={10} style={{ color: "#10b981" }} />}
                  {isProcessing && <Loader2 size={10} style={{ color: "#f59e0b", animation: "spin 0.8s linear infinite" }} />}
                  {isError && <AlertCircle size={10} style={{ color: "#ef4444" }} />}
                  <span style={{ fontSize: 10, color: isReady ? "#10b981" : isProcessing ? "#f59e0b" : "#ef4444", fontWeight: 700 }}>
                    {isReady ? "Ready" : isProcessing ? "Processing" : "Error"}
                  </span>
                </div>
                {doc.chunk_count > 0 && (
                  <span style={{ fontSize: 10, color: "#6b7280", background: "rgba(79,70,229,0.04)", border: "1px solid rgba(79,70,229,0.1)", borderRadius: 6, padding: "1px 6px" }}>
                    {doc.chunk_count} chunks
                  </span>
                )}
                {!isWebsite && (
                  <span style={{ fontSize: 10, color: "#9ca3af" }}>{formatSize(doc.file_size)}</span>
                )}
                {doc.uploaded_at && (
                  <span style={{ fontSize: 10, color: "#9ca3af" }}>{formatDate(doc.uploaded_at)}</span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
              {isReady && !isWebsite && (
                <button
                  onClick={() => {
                     window.open(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/download/${doc.id}`);
                  }}
                  title="Download document"
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    width: 30, height: 30, borderRadius: 9,
                    background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)",
                    cursor: "pointer", transition: "all 0.15s",
                  }}
                  onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(16,185,129,0.15)"; el.style.borderColor = "rgba(16,185,129,0.3)"; el.style.transform = "scale(1.1)"; }}
                  onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(16,185,129,0.08)"; el.style.borderColor = "rgba(16,185,129,0.2)"; el.style.transform = "scale(1)"; }}
                >
                  <Download size={13} style={{ color: "#10b981" }} />
                </button>
              )}
              {isWebsite && isReady && (
                <a
                  href={doc.original_filename || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Open website"
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    width: 30, height: 30, borderRadius: 9,
                    background: "rgba(8,145,178,0.08)", border: "1px solid rgba(8,145,178,0.2)",
                    cursor: "pointer", transition: "all 0.15s", textDecoration: "none",
                  }}
                  onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(8,145,178,0.15)"; el.style.borderColor = "rgba(8,145,178,0.3)"; el.style.transform = "scale(1.1)"; }}
                  onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(8,145,178,0.08)"; el.style.borderColor = "rgba(8,145,178,0.2)"; el.style.transform = "scale(1)"; }}
                >
                  <Globe size={13} style={{ color: "#0891b2" }} />
                </a>
              )}
              <button
                onClick={() => onDelete(doc.id)}
                title="Delete document"
                style={{
                  display: "flex", alignItems: "center", justifyContent: "center",
                  width: 30, height: 30, borderRadius: 9,
                  background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
                  cursor: "pointer", transition: "all 0.15s",
                }}
                onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(239,68,68,0.15)"; el.style.borderColor = "rgba(239,68,68,0.3)"; el.style.transform = "scale(1.1)"; }}
                onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.background = "rgba(239,68,68,0.08)"; el.style.borderColor = "rgba(239,68,68,0.2)"; el.style.transform = "scale(1)"; }}
              >
                <Trash2 size={13} style={{ color: "#ef4444" }} />
              </button>
            </div>
          </div>
        );
      })}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}