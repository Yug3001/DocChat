import React from "react";
import { Dataset } from "@/lib/types";
import { DownloadButton } from "./DownloadButton";

interface Props {
  dataset: Dataset;
  onSync?: () => void;
  syncing?: boolean;
}

export function DatasetCard({ dataset, onSync, syncing }: Props) {
  const isMySQL = dataset.source_type === "MYSQL";
  const columnsCount = dataset.schema_snapshot?.columns?.length || 0;

  return (
    <div style={{ padding: "16px", background: "#fff", borderRadius: "12px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#1e293b" }}>
          {dataset.display_name}
        </h3>
        <span style={{ fontSize: "12px", padding: "4px 8px", borderRadius: "12px", background: isMySQL ? "#dbeafe" : "#dcfce7", color: isMySQL ? "#1e40af" : "#166534", fontWeight: 600 }}>
          {dataset.source_type}
        </span>
      </div>
      
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "16px", fontSize: "13px", color: "#64748b" }}>
        <div><strong>Rows:</strong> {dataset.row_count}</div>
        <div><strong>Columns:</strong> {columnsCount}</div>
        <div><strong>Version:</strong> v{dataset.version}</div>
        <div><strong>Status:</strong> {dataset.status}</div>
      </div>

      {isMySQL && onSync ? (
        <button 
          onClick={onSync} 
          disabled={syncing}
          style={{ width: "100%", padding: "8px", borderRadius: "8px", border: "1px solid #cbd5e1", background: "#f8fafc", color: "#334155", fontWeight: 600, cursor: syncing ? "not-allowed" : "pointer", opacity: syncing ? 0.7 : 1 }}
        >
          {syncing ? "Syncing Schema..." : "Sync MySQL Schema"}
        </button>
      ) : (
        <DownloadButton datasetId={dataset.dataset_id} />
      )}
    </div>
  );
}
