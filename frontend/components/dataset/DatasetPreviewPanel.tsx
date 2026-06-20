import React from "react";

interface Props {
  data: any[];
  columns: {name: string, type: string}[];
}

export function DatasetPreviewPanel({ data, columns }: Props) {
  if (!data || data.length === 0) {
    return <div style={{ padding: "20px", textAlign: "center", color: "#64748b" }}>No data available for preview.</div>;
  }

  return (
    <div style={{ overflowX: "auto", border: "1px solid #e2e8f0", borderRadius: "8px", background: "#fff" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
        <thead>
          <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
            {columns.map(c => (
              <th key={c.name} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 600, color: "#334155", whiteSpace: "nowrap" }}>
                {c.name} <span style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 400, marginLeft: "4px" }}>({c.type})</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
              {columns.map(c => (
                <td key={c.name} style={{ padding: "8px 12px", color: "#475569", whiteSpace: "nowrap", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {row[c.name]?.toString() || ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
