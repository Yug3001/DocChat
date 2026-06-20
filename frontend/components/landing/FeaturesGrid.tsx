import { FileText, Globe, Activity, Eye, Zap, Search } from "lucide-react";

const features = [
  {
    name: "Multi-Format Ingestion",
    description: "Seamlessly upload PDF, DOCX, XLSX, and plain text files. The pipeline handles chunking and extraction automatically.",
    icon: FileText,
  },
  {
    name: "Web Scraping",
    description: "Paste a URL and let DocChat recursively scrape, clean, and embed the website content for instant Q&A.",
    icon: Globe,
  },
  {
    name: "Medical Image Analysis",
    description: "Upload X-rays, MRIs, or CT scans. Our dedicated clinical vision model provides structured, educational observations.",
    icon: Activity,
  },
  {
    name: "Transparent Reasoning",
    description: "Never guess why the AI said something. Expand the 'Thinking' panel to see exactly how it formulated its answer.",
    icon: Eye,
  },
  {
    name: "Local & Private Embeddings",
    description: "Uses all-MiniLM-L6-v2 for fast, private, on-device document embedding before querying the LLM.",
    icon: Zap,
  },
  {
    name: "Precise Source Citations",
    description: "Answers are backed by cross-encoder reranked retrieval, with clear citations pointing to the exact source file.",
    icon: Search,
  },
];

export default function FeaturesGrid() {
  return (
    <section id="features" className="bg-white py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-sm font-bold uppercase tracking-widest text-indigo-600 mb-3">Capabilities</h2>
          <p className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            Everything you need to talk to your data
          </p>
          <p className="mt-6 text-lg leading-relaxed text-slate-500">
            A complete retrieval-augmented generation (RAG) pipeline built for speed, accuracy, and transparency.
          </p>
        </div>
        <div className="mx-auto mt-20 max-w-5xl">
          <dl className="grid grid-cols-1 gap-x-12 gap-y-16 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.name} className="flex flex-col rounded-2xl bg-slate-50 p-8 border border-slate-100 shadow-sm transition-all hover:shadow-md">
                <dt className="flex flex-col items-start gap-4 text-xl font-bold text-slate-900">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-md">
                    <feature.icon className="h-6 w-6" aria-hidden="true" />
                  </div>
                  {feature.name}
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-relaxed text-slate-600">
                  <p className="flex-auto">{feature.description}</p>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}
