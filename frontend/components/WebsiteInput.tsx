"use client";
import { useState } from "react";
import { Globe, Loader2, Link2, ChevronDown, ChevronUp, AlertCircle, CheckCircle } from "lucide-react";

interface Props {
  onScrape: (url: string, crawlLinks: boolean, maxPages: number) => Promise<any>;
  scraping: boolean;
  error: string | null;
}

export default function WebsiteInput({ onScrape, scraping, error }: Props) {
  const [url, setUrl] = useState("");
  const [showOptions, setShowOptions] = useState(false);
  const [crawlLinks, setCrawlLinks] = useState(true);
  const [maxPages, setMaxPages] = useState(5);
  const [success, setSuccess] = useState(false);

  const isValidUrl = (s: string) => {
    try { new URL(s); return true; } catch { return false; }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || scraping) return;
    const fullUrl = url.startsWith("http") ? url.trim() : `https://${url.trim()}`;
    if (!isValidUrl(fullUrl)) return;
    setSuccess(false);
    try {
      await onScrape(fullUrl, crawlLinks, maxPages);
      setSuccess(true);
      setUrl("");
      setTimeout(() => setSuccess(false), 4000);
    } catch {}
  };

  const valid = url.trim().length > 3;

  return (
    <div
      style={{
        borderRadius: 16,
        border: "1.5px dashed rgba(79,70,229,0.25)",
        background: "linear-gradient(135deg, rgba(79,70,229,0.03) 0%, rgba(124,58,237,0.02) 100%)",
        padding: "18px 20px",
        transition: "border-color 0.2s",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
        <div
          style={{
            width: 32, height: 32, borderRadius: 10,
            background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Globe size={16} color="#fff" />
        </div>
        <div>
          <p style={{ fontSize: 13, fontWeight: 700, color: "#1e1b4b", margin: 0 }}>Add Website URL</p>
          <p style={{ fontSize: 11, color: "#6b7280", margin: 0 }}>Scrape and chat with any webpage</p>
        </div>
      </div>

      {/* URL Input form */}
      <form onSubmit={handleSubmit}>
        <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
          {/* Input */}
          <div
            style={{
              flex: 1,
              display: "flex", alignItems: "center",
              background: "#ffffff",
              border: `1.5px solid ${error ? "rgba(239,68,68,0.4)" : "rgba(79,70,229,0.15)"}`,
              borderRadius: 12, padding: "0 12px",
              transition: "border-color 0.2s, box-shadow 0.2s",
            }}
            onFocus={() => {}}
          >
            <Link2 size={13} style={{ color: "#9ca3af", flexShrink: 0, marginRight: 8 }} />
            <input
              type="text"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://example.com"
              disabled={scraping}
              style={{
                flex: 1, border: "none", outline: "none",
                fontSize: 13, color: "#1e1b4b", background: "transparent",
                padding: "10px 0",
                fontFamily: "'Inter', sans-serif",
              }}
            />
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={!valid || scraping}
            style={{
              display: "flex", alignItems: "center", gap: 7,
              padding: "0 18px", borderRadius: 12, border: "none",
              background: (!valid || scraping)
                ? "rgba(79,70,229,0.3)"
                : "linear-gradient(135deg, #4f46e5, #7c3aed)",
              color: "#fff", fontSize: 13, fontWeight: 700,
              cursor: (!valid || scraping) ? "not-allowed" : "pointer",
              transition: "all 0.2s",
              boxShadow: valid && !scraping ? "0 4px 14px rgba(79,70,229,0.35)" : "none",
              whiteSpace: "nowrap",
            }}
          >
            {scraping ? (
              <><Loader2 size={13} style={{ animation: "spin 0.8s linear infinite" }} /> Scraping…</>
            ) : (
              <><Globe size={13} /> Scrape</>  
            )}
          </button>
        </div>

        {/* Advanced options toggle */}
        <button
          type="button"
          onClick={() => setShowOptions(v => !v)}
          style={{
            marginTop: 8, display: "flex", alignItems: "center", gap: 5,
            background: "none", border: "none", padding: 0,
            fontSize: 11, color: "#6b7280", cursor: "pointer", fontWeight: 600,
            letterSpacing: "0.02em",
          }}
        >
          {showOptions ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          Advanced options
        </button>

        {/* Options panel */}
        {showOptions && (
          <div
            style={{
              marginTop: 10, padding: "12px 14px",
              borderRadius: 12,
              background: "rgba(79,70,229,0.04)",
              border: "1px solid rgba(79,70,229,0.1)",
              display: "flex", flexDirection: "column", gap: 10,
            }}
          >
            {/* Crawl toggle */}
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
              <div
                onClick={() => setCrawlLinks(v => !v)}
                style={{
                  width: 34, height: 18, borderRadius: 99,
                  background: crawlLinks ? "linear-gradient(135deg, #4f46e5, #7c3aed)" : "rgba(107,114,128,0.3)",
                  position: "relative", cursor: "pointer", transition: "background 0.2s",
                  flexShrink: 0,
                }}
              >
                <div style={{
                  position: "absolute", top: 2,
                  left: crawlLinks ? 18 : 2,
                  width: 14, height: 14, borderRadius: "50%",
                  background: "#fff",
                  transition: "left 0.2s",
                  boxShadow: "0 1px 4px rgba(0,0,0,0.15)",
                }} />
              </div>
              <span style={{ fontSize: 12, color: "#374151", fontWeight: 600 }}>Crawl internal links</span>
            </label>

            {/* Max pages */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 12, color: "#374151", fontWeight: 600, minWidth: 80 }}>Max pages</span>
              <input
                type="number"
                min={1} max={20} value={maxPages}
                onChange={e => setMaxPages(Math.min(20, Math.max(1, parseInt(e.target.value) || 5)))}
                style={{
                  width: 56, padding: "4px 8px", borderRadius: 8,
                  border: "1px solid rgba(79,70,229,0.2)",
                  fontSize: 12, color: "#1e1b4b", background: "#fff",
                  outline: "none", fontFamily: "inherit",
                }}
              />
              <span style={{ fontSize: 11, color: "#9ca3af" }}>(1–20)</span>
            </div>
          </div>
        )}
      </form>

      {/* Success state */}
      {success && (
        <div style={{
          marginTop: 10, display: "flex", alignItems: "center", gap: 8,
          padding: "8px 12px", borderRadius: 10,
          background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)",
        }}>
          <CheckCircle size={13} style={{ color: "#10b981", flexShrink: 0 }} />
          <span style={{ fontSize: 12, color: "#065f46", fontWeight: 600 }}>Website scraped and ready to chat!</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div style={{
          marginTop: 10, display: "flex", alignItems: "flex-start", gap: 8,
          padding: "8px 12px", borderRadius: 10,
          background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)",
        }}>
          <AlertCircle size={13} style={{ color: "#ef4444", flexShrink: 0, marginTop: 1 }} />
          <span style={{ fontSize: 12, color: "#b91c1c", fontWeight: 500, lineHeight: 1.5 }}>{error}</span>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
