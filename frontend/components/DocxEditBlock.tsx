"use client";
import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { Copy, Check, FileEdit } from "lucide-react";

interface Props {
  content: string;
  isStreaming?: boolean;
}

export default function DocxEditBlock({ content, isStreaming }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    // Strip markdown syntax for clean paste into Word
    const plain = content
      .replace(/\*\*(.*?)\*\*/g, "$1")      // bold → plain
      .replace(/~~(.*?)~~/g, "$1")           // strikethrough → plain
      .replace(/^#+\s+/gm, "")              // headings → plain
      .replace(/^\s*[-*]\s+/gm, "• ")       // bullets → •
      .trim();

    navigator.clipboard.writeText(plain).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  }, [content]);

  return (
    <div
      style={{
        marginTop: 12,
        borderRadius: 16,
        border: "1.5px solid rgba(79,70,229,0.18)",
        background: "linear-gradient(135deg, #f8f7ff 0%, #f0f0ff 100%)",
        overflow: "hidden",
        boxShadow: "0 4px 20px rgba(79,70,229,0.08)",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 16px",
          background: "linear-gradient(135deg, rgba(79,70,229,0.1) 0%, rgba(124,58,237,0.07) 100%)",
          borderBottom: "1px solid rgba(79,70,229,0.12)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 8,
              background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <FileEdit size={14} color="#fff" />
          </div>
          <div>
            <p style={{ fontSize: 12, fontWeight: 700, color: "#3730a3", margin: 0 }}>
              Updated Document Content
            </p>
            <p style={{ fontSize: 10, color: "#6b7280", margin: 0 }}>
              {isStreaming ? "AI is editing…" : "Copy and paste into your Word document"}
            </p>
          </div>
        </div>

        {/* Copy button */}
        {!isStreaming && content && (
          <button
            onClick={handleCopy}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 14px",
              borderRadius: 10,
              border: "none",
              background: copied
                ? "linear-gradient(135deg, #10b981, #059669)"
                : "linear-gradient(135deg, #4f46e5, #7c3aed)",
              color: "#fff",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              transition: "all 0.25s",
              boxShadow: copied
                ? "0 2px 10px rgba(16,185,129,0.35)"
                : "0 2px 10px rgba(79,70,229,0.3)",
            }}
            onMouseEnter={e => {
              if (!copied) (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
            }}
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
            {copied ? "Copied!" : "Copy Text"}
          </button>
        )}
      </div>

      {/* Content body */}
      <div
        style={{
          padding: "16px 20px",
          fontSize: 14,
          lineHeight: 1.8,
          color: "#1e1b4b",
          fontFamily: "'Georgia', 'Times New Roman', serif",
          minHeight: 60,
        }}
      >
        {isStreaming && !content ? (
          <div style={{ display: "flex", gap: 6, alignItems: "center", padding: "6px 0" }}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="animate-pulse-dot"
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
                  animationDelay: `${i * 0.16}s`,
                }}
              />
            ))}
          </div>
        ) : (
          <div
            className="prose-docx max-w-none"
            style={{
              // Bold = highlight changed/added text
              /* strikethrough = removed text */
            }}
          >
            <ReactMarkdown
              components={{
                // Render bold with a highlight tint to show additions
                strong: ({ children }) => (
                  <strong
                    style={{
                      background: "rgba(16,185,129,0.15)",
                      borderRadius: 3,
                      padding: "0 2px",
                      color: "#065f46",
                      fontWeight: 700,
                    }}
                  >
                    {children}
                  </strong>
                ),
                // Render strikethrough with a red tint to show deletions
                del: ({ children }) => (
                  <del
                    style={{
                      color: "#dc2626",
                      background: "rgba(239,68,68,0.1)",
                      borderRadius: 3,
                      padding: "0 2px",
                      textDecorationColor: "#dc2626",
                    }}
                  >
                    {children}
                  </del>
                ),
                // Clean paragraph spacing
                p: ({ children }) => (
                  <p style={{ marginBottom: "0.8em", marginTop: 0 }}>{children}</p>
                ),
                // Bullet style
                li: ({ children }) => (
                  <li style={{ marginBottom: "0.3em" }}>{children}</li>
                ),
                // Horizontal rule as a subtle divider
                hr: () => (
                  <hr style={{ border: "none", borderTop: "1px solid rgba(79,70,229,0.15)", margin: "12px 0" }} />
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {/* Legend footer */}
      {!isStreaming && content && (
        <div
          style={{
            padding: "8px 20px",
            borderTop: "1px solid rgba(79,70,229,0.08)",
            display: "flex",
            gap: 16,
            alignItems: "center",
            background: "rgba(255,255,255,0.6)",
          }}
        >
          <span style={{ fontSize: 10, color: "#6b7280", display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ background: "rgba(16,185,129,0.2)", borderRadius: 3, padding: "1px 5px", fontSize: 10, fontWeight: 700, color: "#065f46" }}>Added / Changed</span>
          </span>
          <span style={{ fontSize: 10, color: "#6b7280", display: "flex", alignItems: "center", gap: 4 }}>
            <del style={{ color: "#dc2626", fontSize: 10 }}>Removed</del>
          </span>
          <span style={{ fontSize: 10, color: "#9ca3af", marginLeft: "auto" }}>Click "Copy Text" to paste into Word</span>
        </div>
      )}
    </div>
  );
}
