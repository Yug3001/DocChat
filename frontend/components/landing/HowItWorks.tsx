import { Upload, Cpu, Search, MessageSquareText } from "lucide-react";

const steps = [
  {
    id: "01",
    name: "Upload Data",
    description: "Drop in your PDFs, spreadsheets, or images. We automatically parse and extract the text.",
    icon: Upload,
  },
  {
    id: "02",
    name: "Local Embed",
    description: "Documents are split into semantic chunks and embedded locally for maximum privacy and speed.",
    icon: Cpu,
  },
  {
    id: "03",
    name: "Vector Retrieval",
    description: "When you ask a question, we retrieve the most relevant chunks and rerank them using a cross-encoder.",
    icon: Search,
  },
  {
    id: "04",
    name: "Cited Answers",
    description: "Our LLM generates a precise answer based only on retrieved context, with exact source citations.",
    icon: MessageSquareText,
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-white py-24 sm:py-32 border-t border-slate-200">
      <div className="mx-auto max-w-6xl px-6">
        <div className="mx-auto max-w-2xl text-center mb-20">
          <h2 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            How the pipeline works
          </h2>
          <p className="mt-6 text-lg leading-relaxed text-slate-500">
            A transparent, multi-stage retrieval architecture designed for accuracy.
          </p>
        </div>

        <div className="relative">
          {/* Connecting line (desktop only) */}
          <div className="absolute top-12 left-[10%] right-[10%] hidden h-[2px] bg-slate-100 lg:block" aria-hidden="true"></div>
          
          <div className="grid grid-cols-1 gap-16 lg:grid-cols-4 lg:gap-8">
            {steps.map((step) => (
              <div key={step.id} className="relative flex flex-col items-center text-center">
                <div className="relative flex h-24 w-24 items-center justify-center rounded-2xl bg-white border-2 border-slate-100 shadow-sm z-10 transition-transform hover:scale-105 hover:border-indigo-200 hover:shadow-md">
                  <step.icon className="h-10 w-10 text-indigo-600" aria-hidden="true" />
                  <div className="absolute -top-4 -right-4 flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 font-mono text-xs font-bold text-white shadow-md ring-4 ring-white">
                    {step.id}
                  </div>
                </div>
                <h3 className="mt-8 text-xl font-bold text-slate-900">{step.name}</h3>
                <p className="mt-3 text-base text-slate-500 leading-relaxed max-w-[250px]">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
