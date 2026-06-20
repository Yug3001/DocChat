import React from "react";
import { Mutation } from "@/lib/types";

interface Props {
  history: Mutation[];
  onUndo: (mutationId: string) => void;
  undoing: boolean;
}

export function MutationHistoryPanel({ history, onUndo, undoing }: Props) {
  if (!history || history.length === 0) {
    return <div style={{ fontSize: "13px", color: "#64748b" }}>No mutations recorded yet.</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {history.map(m => (
        <div key={m.mutation_id} style={{ padding: "12px", border: "1px solid #e2e8f0", borderRadius: "8px", background: "#f8fafc" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", fontWeight: 700, color: m.success ? "#1e293b" : "#dc2626" }}>
              v{m.version} - {m.operation_type}
            </span>
            <span style={{ fontSize: "11px", color: "#94a3b8" }}>{new Date(m.executed_at).toLocaleString()}</span>
          </div>
          <div style={{ fontSize: "13px", color: "#475569", marginBottom: "8px" }}>{m.description}</div>
          <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "8px" }}>Rows affected: {m.rows_affected}</div>
          
          {m.success && m.reversible && (
            <button 
              onClick={() => onUndo(m.mutation_id)} 
              disabled={undoing}
              style={{ padding: "4px 10px", fontSize: "12px", borderRadius: "6px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", cursor: undoing ? "not-allowed" : "pointer" }}
            >
              Undo
            </button>
          )}
          {!m.success && m.error_message && (
             <div style={{ fontSize: "12px", color: "#dc2626", marginTop: "4px", background: "#fee2e2", padding: "6px", borderRadius: "4px" }}>
               Failed: {m.error_message}
             </div>
          )}
        </div>
      ))}
    </div>
  );
}
