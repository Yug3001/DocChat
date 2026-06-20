export default function TrustSection() {
  return (
    <section className="bg-slate-50 py-20 border-y border-slate-200">
      <div className="mx-auto max-w-6xl px-6">
        <p className="text-center text-sm font-bold uppercase tracking-widest text-slate-400 mb-10">
          Built with enterprise-grade open-source technology
        </p>
        <div className="flex flex-wrap items-center justify-center gap-x-16 gap-y-10 grayscale opacity-70 hover:grayscale-0 hover:opacity-100 transition-all duration-500">
          <div className="flex items-center gap-3 font-extrabold text-2xl text-slate-900">
            <div className="h-10 w-10 rounded-lg bg-slate-900 text-white flex items-center justify-center text-lg shadow-md">G</div>
            Groq LPU
          </div>
          <div className="flex items-center gap-3 font-extrabold text-2xl text-slate-900">
            <div className="h-10 w-10 rounded-lg bg-orange-500 shadow-md"></div>
            ChromaDB
          </div>
          <div className="flex items-center gap-3 font-extrabold text-2xl text-slate-900">
            <span className="text-blue-600 text-4xl font-serif leading-none shadow-sm">ƒ</span>
            FastAPI
          </div>
          <div className="flex items-center gap-3 font-extrabold text-2xl text-slate-900">
            <div className="h-10 w-10 rounded-full border-[5px] border-slate-900 shadow-sm"></div>
            Next.js
          </div>
        </div>
      </div>
    </section>
  );
}
