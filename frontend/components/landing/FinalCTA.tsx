import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function FinalCTA() {
  return (
    <section className="bg-indigo-600 py-24 sm:py-32 relative overflow-hidden">
      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10 mix-blend-overlay"></div>
      <div className="mx-auto max-w-4xl px-6 text-center relative z-10">
        <h2 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
          Ready to unlock your documents?
        </h2>
        <p className="mx-auto mt-6 max-w-2xl text-xl text-indigo-100 leading-relaxed">
          Stop searching for answers manually. Upload your files and let our RAG pipeline do the heavy lifting in seconds.
        </p>
        <div className="mt-12 flex justify-center">
          <Link
            href="/chat"
            className="group flex items-center justify-center gap-3 rounded-xl bg-white px-10 py-5 text-lg font-bold text-indigo-600 shadow-xl transition-all hover:bg-slate-50 hover:shadow-2xl hover:-translate-y-1"
          >
            Open Chat Interface
            <ArrowRight size={20} className="transition-transform group-hover:translate-x-1.5" />
          </Link>
        </div>
      </div>
    </section>
  );
}
