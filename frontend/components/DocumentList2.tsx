"use client";
import { Document } from "@/lib/types";
import { FileText, Trash2 } from "lucide-react";
import clsx from "clsx";

const TYPE_COLORS: Record<string, string> = {
  pdf: "text-red-400 bg-red-500/20",
  docx: "text-blue-400 bg-blue-500/20",
  xlsx: "text-green-400 bg-green-500/20",
  xls: "text-green-400 bg-green-500/20",
  png: "text-purple-400 bg-purple-500/20",
  jpg: "text-purple-400 bg-purple-500/20",
};

interface Props {
  documents: Document[];
  onDelete: (id: string) => void;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export default function DocumentList({ documents, onDelete }: Props) {
  if (!documents.length) {
    return (
      <div className="p-4 rounded-xl border border-white/10 bg-gradient-to-br from-slate-800/40 to-slate-900/40 text-center">
        <FileText size={24} className="text-slate-600 mx-auto mb-2" />
        <p className="text-xs font-semibold text-slate-300">No documents yet</p>
        <p className="text-[11px] text-slate-500 mt-1">Upload files to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="group relative overflow-hidden rounded-xl border border-white/10 bg-gradient-to-r from-slate-800/40 to-slate-900/30 hover:border-indigo-500/50 p-3 transition duration-200 hover:shadow-lg hover:shadow-indigo-500/10"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/0 via-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition" />
          <div className="relative flex items-center gap-3">
            <div className={clsx("rounded-lg p-2 flex-shrink-0", TYPE_COLORS[doc.file_type] ?? "bg-slate-700 text-slate-300")}>
              <FileText size={14} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-100 truncate">{doc.filename}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="inline-block px-2 py-0.5 rounded-full bg-slate-700/40 text-[10px] text-slate-400">
                  {doc.chunk_count > 0 ? `${doc.chunk_count} chunks` : doc.status}
                </span>
                <span className="text-[10px] text-slate-500">{formatSize(doc.file_size)}</span>
              </div>
            </div>
            <button
              onClick={() => onDelete(doc.id)}
              className="opacity-0 group-hover:opacity-100 transition px-2 py-1 rounded-lg text-xs font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/10 flex-shrink-0"
            >
              Remove
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
