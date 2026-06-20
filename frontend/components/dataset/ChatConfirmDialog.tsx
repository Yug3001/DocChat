import React from "react";

interface Props {
  payload: any;
  onConfirm: (req: any) => void;
  onCancel: () => void;
  confirming: boolean;
}

export function ChatConfirmDialog({ payload, onConfirm, onCancel, confirming }: Props) {
  if (!payload || payload.action !== "REQUIRE_CONFIRMATION") return null;

  return (
    <div style={{ padding: "16px", borderRadius: "12px", border: "1px solid #e2e8f0", background: "#fff", marginTop: "12px", boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)" }}>
      <h4 style={{ margin: "0 0 12px 0", fontSize: "16px", fontWeight: 700, color: "#1e293b" }}>Review Changes</h4>
      
      <div style={{ marginBottom: "12px", padding: "10px", background: "#f8fafc", borderRadius: "8px", fontSize: "13px", color: "#475569" }}>
        <strong>Action:</strong> {payload.description}
      </div>

      <div style={{ marginBottom: "16px", background: "#1e293b", borderRadius: "8px", padding: "12px", overflowX: "auto" }}>
        <pre style={{ margin: 0, color: "#e2e8f0", fontSize: "13px", fontFamily: "monospace" }}>{payload.sql}</pre>
      </div>

      <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
        <button 
          onClick={onCancel}
          disabled={confirming}
          style={{ padding: "8px 16px", borderRadius: "8px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", fontWeight: 600, cursor: confirming ? "not-allowed" : "pointer" }}
        >
          Cancel
        </button>
        <button 
          onClick={() => onConfirm({
            forward_sql: payload.sql,
            intent: payload.intent,
            description: payload.description
          })}
          disabled={confirming}
          style={{ padding: "8px 16px", borderRadius: "8px", border: "none", background: "#dc2626", color: "#fff", fontWeight: 600, cursor: confirming ? "not-allowed" : "pointer", opacity: confirming ? 0.7 : 1 }}
        >
          {confirming ? "Executing..." : "Confirm Execution"}
        </button>
      </div>
    </div>
  );
}
