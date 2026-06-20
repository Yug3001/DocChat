"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { CloudUpload, CheckCircle2, FileText, X } from "lucide-react";

const ACCEPTED = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "application/vnd.ms-excel": [".xls"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/jpg": [".jpg", ".jpeg"],  // non-standard, some browsers send this
  "image/webp": [".webp"],
};

const FORMAT_LABELS = [
  { ext: "PDF", color: "#ef4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.2)" },
  { ext: "DOCX", color: "#3b82f6", bg: "rgba(59,130,246,0.08)", border: "rgba(59,130,246,0.2)" },
  { ext: "XLSX", color: "#10b981", bg: "rgba(16,185,129,0.08)", border: "rgba(16,185,129,0.2)" },
  { ext: "XLS", color: "#10b981", bg: "rgba(16,185,129,0.08)", border: "rgba(16,185,129,0.2)" },
  { ext: "PNG", color: "#8b5cf6", bg: "rgba(139,92,246,0.08)", border: "rgba(139,92,246,0.2)" },
  { ext: "JPG", color: "#f97316", bg: "rgba(249,115,22,0.08)", border: "rgba(249,115,22,0.2)" },
];

interface Props {
  onUpload: (files: File[]) => void;
  uploading: boolean;
  error: string | null;
  compact?: boolean;
}

export default function FileUpload({ onUpload, uploading, error, compact = false }: Props) {
  const [progress, setProgress] = useState(0);
  const [success, setSuccess] = useState(false);
  const [queuedFiles, setQueuedFiles] = useState<File[]>([]);
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Simulate progress bar
  useEffect(() => {
    if (uploading) {
      setSuccess(false);
      setProgress(0);
      progressRef.current = setInterval(() => {
        setProgress((p) => {
          if (p >= 88) { clearInterval(progressRef.current!); return 88; }
          return p + Math.random() * 12;
        });
      }, 200);
    } else if (progress > 0) {
      clearInterval(progressRef.current!);
      if (!error) {
        setProgress(100);
        setTimeout(() => {
          setSuccess(true);
          setQueuedFiles([]);
          setTimeout(() => { setSuccess(false); setProgress(0); }, 2500);
        }, 300);
      } else {
        setProgress(0);
      }
    }
    return () => { if (progressRef.current) clearInterval(progressRef.current); };
  }, [uploading, error, progress]);

  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length) {
        setQueuedFiles(accepted);
        setSuccess(false);
        onUpload(accepted);
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    disabled: uploading,
  });

  /* ─── COMPACT MODE (sidebar) ─────────────────────── */
  if (compact) {
    return (
      <div>
        <div
          {...getRootProps()}
          className="flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200"
          style={{
            background: isDragActive ? "rgba(79,70,229,0.12)" : "rgba(79,70,229,0.04)",
            border: `1px dashed ${isDragActive ? "rgba(79,70,229,0.5)" : "rgba(79,70,229,0.2)"}`,
          }}
          onMouseEnter={e => { if (!isDragActive) { (e.currentTarget as HTMLElement).style.background = "rgba(79,70,229,0.08)"; } }}
          onMouseLeave={e => { if (!isDragActive) { (e.currentTarget as HTMLElement).style.background = "rgba(79,70,229,0.04)"; } }}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <div className="w-4 h-4 rounded-full border-2 flex-shrink-0" style={{ borderColor: "rgba(79,70,229,0.2)", borderTopColor: "#4f46e5", animation: "spin 0.7s linear infinite" }} />
          ) : success ? (
            <CheckCircle2 size={16} style={{ color: "#10b981", flexShrink: 0 }} />
          ) : (
            <CloudUpload size={16} style={{ color: isDragActive ? "#4f46e5" : "#6b7280", flexShrink: 0 }} />
          )}
          <span style={{ fontSize: 12, fontWeight: 600, color: uploading ? "#4f46e5" : success ? "#10b981" : "#6b7280" }}>
            {uploading ? "Uploading…" : success ? "Uploaded!" : isDragActive ? "Drop here" : "Upload files"}
          </span>
        </div>
        {uploading && (
          <div className="mt-2 h-1 rounded-full overflow-hidden" style={{ background: "rgba(79,70,229,0.1)" }}>
            <div className="h-full rounded-full transition-all duration-300" style={{ width: `${Math.min(progress, 100)}%`, background: "linear-gradient(90deg,#4f46e5,#7c3aed)" }} />
          </div>
        )}
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  /* ─── FULL MODE (dashboard) ──────────────────────── */
  return (
    <div className="flex flex-col gap-4">

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className="relative overflow-hidden rounded-2xl cursor-pointer transition-all duration-300 group"
        style={{
          border: `2px dashed ${isDragActive ? "#4f46e5" : success ? "#10b981" : "rgba(79,70,229,0.2)"}`,
          background: isDragActive
            ? "rgba(79,70,229,0.06)"
            : success
            ? "rgba(16,185,129,0.04)"
            : "#ffffff",
          boxShadow: isDragActive
            ? "0 0 0 4px rgba(79,70,229,0.08), inset 0 0 40px rgba(79,70,229,0.04)"
            : success
            ? "0 0 0 4px rgba(16,185,129,0.06)"
            : "0 1px 4px rgba(79,70,229,0.05)",
          minHeight: "clamp(140px, 20vw, 220px)",
        }}
        onMouseEnter={e => {
          if (!isDragActive && !success && !uploading) {
            const el = e.currentTarget as HTMLElement;
            el.style.borderColor = "rgba(79,70,229,0.4)";
            el.style.background = "rgba(79,70,229,0.03)";
          }
        }}
        onMouseLeave={e => {
          if (!isDragActive && !success && !uploading) {
            const el = e.currentTarget as HTMLElement;
            el.style.borderColor = "rgba(79,70,229,0.2)";
            el.style.background = "#ffffff";
          }
        }}
      >
        <input {...getInputProps()} />

        {/* Animated corner accents */}
        {isDragActive && (
          <>
            <div className="absolute top-0 left-0 w-8 h-8" style={{ borderTop: "2px solid #4f46e5", borderLeft: "2px solid #4f46e5", borderRadius: "8px 0 0 0" }} />
            <div className="absolute top-0 right-0 w-8 h-8" style={{ borderTop: "2px solid #4f46e5", borderRight: "2px solid #4f46e5", borderRadius: "0 8px 0 0" }} />
            <div className="absolute bottom-0 left-0 w-8 h-8" style={{ borderBottom: "2px solid #4f46e5", borderLeft: "2px solid #4f46e5", borderRadius: "0 0 0 8px" }} />
            <div className="absolute bottom-0 right-0 w-8 h-8" style={{ borderBottom: "2px solid #4f46e5", borderRight: "2px solid #4f46e5", borderRadius: "0 0 8px 0" }} />
          </>
        )}

        <div className="flex flex-col items-center justify-center gap-4 p-10">

          {/* SUCCESS STATE */}
          {success ? (
            <>
              <div className="flex items-center justify-center w-16 h-16 rounded-2xl" style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)" }}>
                <CheckCircle2 size={32} style={{ color: "#10b981" }} />
              </div>
              <div className="text-center">
                <p style={{ fontSize: 16, fontWeight: 700, color: "#10b981", marginBottom: 4 }}>Upload Complete!</p>
                <p style={{ fontSize: 13, color: "#6b7280" }}>Your file{queuedFiles.length > 1 ? "s are" : " is"} being processed</p>
              </div>
            </>
          ) : uploading ? (
            /* UPLOADING STATE */
            <>
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: "rgba(79,70,229,0.08)", border: "1px solid rgba(79,70,229,0.15)" }}>
                  <CloudUpload size={28} style={{ color: "#4f46e5", animation: "bounce-upload 1s ease-in-out infinite" }} />
                </div>
                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center" style={{ background: "linear-gradient(135deg,#4f46e5,#7c3aed)" }}>
                  <div className="w-2 h-2 rounded-full border-2 border-white" style={{ borderTopColor: "transparent", animation: "spin 0.7s linear infinite" }} />
                </div>
              </div>
              <div className="text-center w-full max-w-xs">
                <p style={{ fontSize: 14, fontWeight: 700, color: "#1e1b4b", marginBottom: 2 }}>Uploading…</p>
                {queuedFiles.length > 0 && (
                  <div className="flex items-center gap-2 justify-center mb-3">
                    <FileText size={12} style={{ color: "#6b7280" }} />
                    <p style={{ fontSize: 12, color: "#6b7280" }}>{queuedFiles[0].name}</p>
                  </div>
                )}
                {/* Progress bar */}
                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(79,70,229,0.1)" }}>
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(progress, 100)}%`, background: "linear-gradient(90deg,#4f46e5,#7c3aed)", boxShadow: "0 0 8px rgba(79,70,229,0.3)" }}
                  />
                </div>
                <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 8 }}>{Math.round(Math.min(progress, 100))}%</p>
              </div>
            </>
          ) : (
            /* DEFAULT STATE */
            <>
              <div
                className="relative flex items-center justify-center w-16 h-16 rounded-2xl transition-all duration-300 group-hover:scale-110"
                style={{
                  background: isDragActive ? "rgba(79,70,229,0.1)" : "rgba(79,70,229,0.04)",
                  border: `1px solid ${isDragActive ? "rgba(79,70,229,0.3)" : "rgba(79,70,229,0.1)"}`,
                }}
              >
                <div
                  className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{ background: "radial-gradient(circle at center, rgba(79,70,229,0.15) 0%, transparent 70%)" }}
                />
                <CloudUpload
                  size={30}
                  style={{ color: isDragActive ? "#4f46e5" : "#9ca3af", transition: "color 0.2s" }}
                  className="relative group-hover:text-[#4f46e5]"
                />
              </div>

              <div className="text-center">
                <p style={{ fontSize: 15, fontWeight: 700, color: "#374151", marginBottom: 4 }}>
                  {isDragActive ? (
                    <span style={{ color: "#4f46e5" }}>Drop your files here</span>
                  ) : (
                    <>
                      <span>Drag & drop or </span>
                      <span style={{ color: "#4f46e5", textDecoration: "underline", textUnderlineOffset: 3 }}>browse files</span>
                    </>
                  )}
                </p>
                <p style={{ fontSize: 12, color: "#9ca3af" }}>Max 50MB per file</p>
              </div>

              {/* Format pills */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
                {FORMAT_LABELS.map(({ ext, color, bg, border }) => (
                  <span
                    key={ext}
                    style={{
                      background: bg,
                      border: `1px solid ${border}`,
                      color,
                      fontSize: 11,
                      fontWeight: 800,
                      letterSpacing: "0.06em",
                      padding: "4px 12px",
                      borderRadius: 8,
                      boxShadow: `0 1px 2px rgba(0,0,0,0.02)`,
                    }}
                  >
                    {ext}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 px-4 py-3 rounded-xl" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <X size={14} style={{ color: "#ef4444", flexShrink: 0, marginTop: 1 }} />
          <p style={{ fontSize: 12, color: "#ef4444", fontWeight: 600 }}>{error}</p>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes bounce-upload {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
      `}</style>
    </div>
  );
}
