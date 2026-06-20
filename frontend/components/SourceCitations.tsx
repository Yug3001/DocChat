"use client";
import { useState } from "react";
import { FileText, ChevronDown, ExternalLink } from "lucide-react";
import { Source } from "@/lib/types";

const TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  pdf:  { bg: 'rgba(239,68,68,0.08)',   text: '#ef4444', border: 'rgba(239,68,68,0.2)' },
  docx: { bg: 'rgba(59,130,246,0.08)',  text: '#3b82f6', border: 'rgba(59,130,246,0.2)' },
  xlsx: { bg: 'rgba(16,185,129,0.08)',  text: '#10b981', border: 'rgba(16,185,129,0.2)' },
  xls:  { bg: 'rgba(16,185,129,0.08)',  text: '#10b981', border: 'rgba(16,185,129,0.2)' },
  png:  { bg: 'rgba(139,92,246,0.08)',  text: '#8b5cf6', border: 'rgba(139,92,246,0.2)' },
  jpg:  { bg: 'rgba(249,115,22,0.08)',  text: '#f97316', border: 'rgba(249,115,22,0.2)' },
};
const DEFAULT_COLOR = { bg: 'rgba(107,114,128,0.08)', text: '#6b7280', border: 'rgba(107,114,128,0.2)' };

export default function SourceCitations({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div
      style={{
        borderRadius: 16,
        border: '1px solid rgba(79,70,229,0.1)',
        background: '#ffffff',
        overflow: 'hidden',
        boxShadow: '0 1px 4px rgba(79,70,229,0.05)',
      }}
    >
      {/* Toggle button */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 14px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          transition: 'background 0.2s',
          textAlign: 'left',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(79,70,229,0.04)'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: 'rgba(79,70,229,0.08)',
            border: '1px solid rgba(79,70,229,0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <FileText size={13} style={{ color: '#4f46e5' }} />
        </div>

        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 12, fontWeight: 700, color: '#1e1b4b' }}>
            {sources.length} source{sources.length > 1 ? 's' : ''} referenced
          </p>
          <p style={{ fontSize: 11, color: '#6b7280' }}>Click to view details</p>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          {/* Score badges preview */}
          <div style={{ display: 'flex', gap: 4 }}>
            {sources.slice(0, 3).map((s, i) => (
              <div
                key={i}
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: '#6b7280',
                  background: 'rgba(79,70,229,0.04)',
                  border: '1px solid rgba(79,70,229,0.1)',
                  borderRadius: 6,
                  padding: '2px 6px',
                }}
              >
                {Math.round(s.score * 100)}%
              </div>
            ))}
          </div>
          <ChevronDown
            size={14}
            style={{
              color: '#4f46e5',
              transition: 'transform 0.3s cubic-bezier(0.25,0.46,0.45,0.94)',
              transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
              flexShrink: 0,
            }}
          />
        </div>
      </button>

      {/* Expanded sources */}
      {open && (
        <div
          style={{
            borderTop: '1px solid rgba(79,70,229,0.1)',
            padding: '12px 12px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          {sources.map((s, i) => {
            const ext = s.filename.split('.').pop()?.toLowerCase() ?? '';
            const colors = TYPE_COLORS[ext] ?? DEFAULT_COLOR;
            const score = Math.round(s.score * 100);

            return (
              <div
                key={i}
                style={{
                  borderRadius: 12,
                  border: '1px solid rgba(79,70,229,0.1)',
                  background: '#f8f8ff',
                  padding: '10px 12px',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(79,70,229,0.25)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(79,70,229,0.1)'; }}
              >
                {/* Source header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                  {/* File type badge */}
                  <span
                    style={{
                      fontSize: 9,
                      fontWeight: 800,
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      padding: '2px 8px',
                      borderRadius: 6,
                      background: colors.bg,
                      border: `1px solid ${colors.border}`,
                      color: colors.text,
                      flexShrink: 0,
                    }}
                  >
                    {ext}
                  </span>

                  {/* Filename */}
                  <span style={{ fontSize: 12, color: '#1e1b4b', fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {s.filename}
                  </span>

                  {/* Match score */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      flexShrink: 0,
                    }}
                  >
                    <div
                      style={{
                        width: 32,
                        height: 4,
                        borderRadius: 99,
                        background: 'rgba(79,70,229,0.1)',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${score}%`,
                          borderRadius: 99,
                          background: score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444',
                          boxShadow: `0 0 4px ${score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444'}`,
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444',
                      }}
                    >
                      {score}%
                    </span>
                  </div>
                </div>

                {/* Excerpt */}
                <p
                  style={{
                    fontSize: 12,
                    color: '#4b5563',
                    lineHeight: 1.6,
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {s.text}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
