import Link from "next/link";
import { MessageSquareText } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/90 backdrop-blur-md shadow-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
            <MessageSquareText size={18} />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900">
            DocChat
          </span>
        </div>

        {/* Links */}
        <div className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
          <a href="#features" className="hover:text-indigo-600 transition-colors">
            Features
          </a>
          <a href="#how-it-works" className="hover:text-indigo-600 transition-colors">
            How it Works
          </a>
        </div>

        {/* CTA */}
        <div className="flex items-center gap-4">
          <Link
            href="/chat"
            className="flex items-center justify-center rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition-all hover:bg-indigo-700 hover:shadow-lg hover:-translate-y-0.5"
          >
            Open Chat
          </Link>
        </div>
      </div>
    </nav>
  );
}
