"use client";
import { useState } from "react";
import { ChevronDown, Brain, Cpu } from "lucide-react";

interface Props {
  thinking: string;
  isStreaming?: boolean;
}

export default function ThinkingPanel({ thinking, isStreaming }: Props) {
  const [open, setOpen] = useState(false);
  if (!thinking) return null;

  return (
    <div
      style={{
        marginBottom: 10,
        borderRadius: 14,
        border: '1px solid rgba(124,58,237,0.2)',
        background: 'rgba(124,58,237,0.05)',
        overflow: 'hidden',
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 12px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background 0.2s',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(124,58,237,0.08)'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
      >
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: 7,
            background: 'rgba(124,58,237,0.15)',
            border: '1px solid rgba(124,58,237,0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Cpu size={12} style={{ color: '#a78bfa' }} />
        </div>

        <span style={{ fontSize: 12, fontWeight: 600, color: '#a78bfa', flex: 1 }}>
          {isStreaming ? 'Reasoning…' : 'View reasoning'}
        </span>

        {isStreaming && (
          <span style={{ display: 'flex', gap: 3, marginRight: 6 }}>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="animate-pulse-dot"
                style={{
                  display: 'inline-block',
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: '#7c3aed',
                  animationDelay: `${i * 0.18}s`,
                }}
              />
            ))}
          </span>
        )}

        <ChevronDown
          size={13}
          style={{
            color: '#6d28d9',
            transition: 'transform 0.3s',
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          }}
        />
      </button>

      {open && (
        <div
          style={{
            borderTop: '1px solid rgba(124,58,237,0.15)',
            padding: '10px 14px',
            maxHeight: 240,
            overflowY: 'auto',
          }}
        >
          <pre
            style={{
              margin: 0,
              fontSize: 12,
              color: '#6d28d9',
              lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
              fontFamily: "'JetBrains Mono', 'Monaco', monospace",
            }}
          >
            {thinking}
          </pre>
        </div>
      )}
    </div>
  );
}