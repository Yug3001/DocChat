import { MessageSquareText } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-white py-12 border-t border-slate-200">
      <div className="mx-auto max-w-6xl px-6 flex flex-col items-center justify-between gap-6 sm:flex-row">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
            <MessageSquareText size={16} />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900">
            DocChat
          </span>
        </div>
        <p className="text-sm font-medium text-slate-500">
          © {new Date().getFullYear()} DocChat. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
