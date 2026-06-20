import React from "react";
import { getDownloadUrl } from "@/lib/datasetApi";
import { Download } from "lucide-react";

interface Props {
  datasetId: string;
}

export function DownloadButton({ datasetId }: Props) {
  return (
    <a 
      href={getDownloadUrl(datasetId)}
      download
      style={{ 
        display: "inline-flex", 
        alignItems: "center", 
        justifyContent: "center", 
        gap: "8px", 
        padding: "10px 16px", 
        borderRadius: "10px", 
        border: "none", 
        background: "linear-gradient(135deg, #4f46e5, #7c3aed)", 
        color: "#fff", 
        fontWeight: 700, 
        fontSize: "13px",
        textDecoration: "none", 
        textAlign: "center", 
        width: "100%", 
        boxSizing: "border-box",
        cursor: "pointer",
        transition: "all 0.2s ease",
        boxShadow: "0 4px 12px rgba(79, 70, 229, 0.2)"
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = "translateY(-1px)";
        e.currentTarget.style.boxShadow = "0 6px 16px rgba(79, 70, 229, 0.3)";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "0 4px 12px rgba(79, 70, 229, 0.2)";
      }}
    >
      <Download size={14} /> Download Latest CSV
    </a>
  );
}
