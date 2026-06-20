"use client";

import { useState, useEffect } from "react";
import { MessageSquare, FileText, ChevronDown, ChevronRight, Activity, Terminal } from "lucide-react";

interface DemoState {
  step: "idle" | "thinking" | "streaming" | "done";
  prompt: string;
  answer: string;
  thinking: string;
}

const DEMO_SCENARIOS = [
  {
    label: "Summarize Q3 Financials",
    prompt: "What were the key drivers of Q3 revenue growth according to the earnings report?",
    thinking: "Scanning Q3_Earnings.pdf... Found revenue breakdown on page 4. Identifying key drivers: Enterprise software sales (+24%), Cloud infrastructure expansion (+18%). Formulating concise summary.",
    answer: "Based on the Q3 Earnings Report, revenue growth was primarily driven by two key factors:\n\n1. **Enterprise Software Sales:** Increased by 24% year-over-year, driven by high adoption of the new security suite.\n2. **Cloud Infrastructure:** Expanded by 18%, benefiting from recent data center upgrades.\n\nOverall, these segments offset the slight decline in legacy hardware sales."
  },
  {
    label: "Analyze Medical Image",
    prompt: "Analyze this chest X-ray image for any abnormalities.",
    thinking: "Image type: Radiograph (Chest PA). Scanning lung fields, cardiomediastinal silhouette, and bony thorax... Lungs appear clear. No focal consolidation, pleural effusion, or pneumothorax detected. Cardiac silhouette is within normal limits.",
    answer: "⚠️ *This analysis is for educational purposes only and is not a medical diagnosis.*\n\n**Image Type:** Chest X-ray (PA view).\n\n**Findings:**\n• The lungs are clear without focal consolidation, pleural effusion, or pneumothorax.\n• The cardiomediastinal silhouette is normal in size and contour.\n• Bony structures appear intact.\n\n**Conclusion:** No acute cardiopulmonary abnormalities detected."
  },
  {
    label: "Scrape & Query Website",
    prompt: "What are the core features listed on the pricing page?",
    thinking: "Scraping URL: https://example.com/pricing... Extracted 3 pages. Chunking text. Searching for 'core features'. Found feature matrix. Extracting standard vs pro tier differences.",
    answer: "According to the pricing page, the core features included in all tiers are:\n\n• Unlimited document uploads\n• Standard SSL encryption\n• 24/7 email support\n\nThe **Pro tier** additionally includes priority routing and local model execution."
  }
];

export default function LiveDemoPreview() {
  const [state, setState] = useState<DemoState>({
    step: "idle",
    prompt: "",
    answer: "",
    thinking: ""
  });

  const [displayedText, setDisplayedText] = useState("");
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true);

  // Handle typing effect
  useEffect(() => {
    if (state.step === "streaming") {
      let i = 0;
      setDisplayedText("");
      const interval = setInterval(() => {
        setDisplayedText(state.answer.substring(0, i + 1));
        i++;
        if (i >= state.answer.length) {
          clearInterval(interval);
          setState(s => ({ ...s, step: "done" }));
        }
      }, 15); // typing speed
      return () => clearInterval(interval);
    }
  }, [state.step, state.answer]);

  const runScenario = (scenario: typeof DEMO_SCENARIOS[0]) => {
    setState({ step: "idle", prompt: scenario.prompt, answer: scenario.answer, thinking: scenario.thinking });
    setDisplayedText("");
    setIsThinkingExpanded(true);
    
    // Fake delay for network request
    setTimeout(() => {
      setState(s => ({ ...s, step: "thinking" }));
      
      // Fake delay for thinking
      setTimeout(() => {
        setIsThinkingExpanded(false);
        setState(s => ({ ...s, step: "streaming" }));
      }, 2000);
    }, 400);
  };

  return (
    <section id="demo" className="bg-slate-50 py-24 sm:py-32 border-y border-slate-200">
      <div className="mx-auto max-w-6xl px-6">
        
        {/* Section Header */}
        <div className="mb-16 text-center">
          <h2 className="text-4xl font-extrabold tracking-tight text-slate-900">Experience the difference</h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-500 leading-relaxed">
            See exactly how DocChat processes your requests with full transparency. 
            Select an example below to watch the pipeline in action.
          </p>
        </div>

        {/* Main Content Layout */}
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
          
          {/* Controls Column */}
          <div className="flex flex-col gap-6 lg:col-span-5">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Try an example</h3>
              <div className="flex flex-col gap-3">
                {DEMO_SCENARIOS.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => runScenario(s)}
                    className={`group flex items-center justify-between rounded-xl px-5 py-4 text-left font-medium transition-all duration-200 ${
                      state.prompt === s.prompt 
                        ? "bg-indigo-600 text-white shadow-md ring-2 ring-indigo-600 ring-offset-2 ring-offset-slate-50" 
                        : "bg-white border border-slate-200 text-slate-700 hover:border-indigo-300 hover:shadow-md hover:-translate-y-0.5"
                    }`}
                  >
                    <span>{s.label}</span>
                    <ChevronRight size={18} className={state.prompt === s.prompt ? "text-indigo-200" : "text-slate-400 group-hover:text-indigo-500"} />
                  </button>
                ))}
              </div>
            </div>
            
            <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/50 p-6 shadow-sm">
              <div className="flex items-center gap-2 font-bold text-indigo-900 text-lg mb-2">
                <Activity size={20} />
                No black boxes
              </div>
              <p className="text-sm text-indigo-700 leading-relaxed">
                Watch the AI's internal reasoning process before it answers, ensuring you understand exactly how it arrived at its conclusion and which sources it referenced.
              </p>
            </div>
          </div>

          {/* Mock Chat Window Column */}
          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-slate-200 bg-white shadow-2xl overflow-hidden flex flex-col h-[650px] ring-1 ring-slate-900/5">
              
              {/* Header */}
              <div className="border-b border-slate-100 bg-slate-50 px-5 py-3.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-slate-200"></div>
                  <div className="h-3 w-3 rounded-full bg-slate-200"></div>
                  <div className="h-3 w-3 rounded-full bg-slate-200"></div>
                </div>
                <span className="rounded-md bg-slate-200/50 px-2 py-1 font-mono text-[10px] font-bold tracking-wider text-slate-500">
                  DOCCHAT_SESSION
                </span>
                <div className="w-[60px]"></div> {/* spacer for centering */}
              </div>

              {/* Chat Area */}
              <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-8 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] bg-fixed relative">
                
                {state.step === "idle" && !state.prompt && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400">
                    <div className="rounded-full bg-slate-50 p-6 mb-4 shadow-inner">
                      <MessageSquare size={40} className="opacity-50 text-slate-400" />
                    </div>
                    <p className="font-medium text-slate-500">Select an example prompt to start</p>
                  </div>
                )}

                {state.prompt && (
                  <div className="flex justify-end animate-slide-up">
                    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-indigo-600 px-5 py-3.5 text-white shadow-sm font-medium leading-relaxed">
                      {state.prompt}
                    </div>
                  </div>
                )}

                {state.step !== "idle" && (
                  <div className="flex gap-4 animate-slide-up">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white shadow-md">
                      <Terminal size={18} />
                    </div>
                    <div className="flex-1 space-y-4 pt-1">
                      
                      {/* Thinking Block */}
                      <div className="rounded-xl border border-slate-200 bg-slate-50 shadow-sm overflow-hidden transition-all">
                        <button 
                          onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
                          className="flex w-full items-center gap-2 px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500 hover:bg-slate-100 transition-colors"
                        >
                          <ChevronDown size={16} className={`transition-transform duration-200 ${isThinkingExpanded ? "" : "-rotate-90"}`} />
                          {state.step === "thinking" ? "Thinking" : "Thought process"}
                          {state.step === "thinking" && <span className="ml-1 h-2 w-2 rounded-full bg-indigo-500 animate-pulse-dot"></span>}
                        </button>
                        
                        {isThinkingExpanded && (
                          <div className="border-t border-slate-200 p-4 font-mono text-[12px] text-slate-600 leading-relaxed bg-white">
                            {state.step === "thinking" ? (
                              <span className="animate-pulse">Analyzing request...</span>
                            ) : (
                              state.thinking
                            )}
                          </div>
                        )}
                      </div>

                      {/* Answer Block */}
                      {(state.step === "streaming" || state.step === "done") && (
                        <div className="prose prose-slate prose-sm max-w-none text-slate-700 bg-white border border-slate-100 rounded-xl p-5 shadow-sm">
                          {displayedText.split('\n').map((line, i) => {
                            if (line.startsWith('• ') || line.match(/^\d+\./)) {
                              return <p key={i} className="pl-4 my-1">{line}</p>;
                            }
                            if (line.startsWith('**') && line.endsWith('**')) {
                              return <p key={i} className="font-bold my-2 text-slate-900">{line.replace(/\*\*/g, '')}</p>;
                            }
                            return <p key={i} className="my-2">{line.replace(/\*\*/g, '')}</p>;
                          })}
                          {state.step === "streaming" && (
                            <span className="inline-block w-2 h-4 ml-1 align-middle bg-indigo-600 animate-blink"></span>
                          )}
                        </div>
                      )}

                      {/* Source Citation */}
                      {state.step === "done" && (
                        <div className="mt-4 flex flex-wrap gap-2 animate-fade-in">
                          <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm hover:border-indigo-300 hover:text-indigo-600 transition-colors cursor-pointer">
                            <FileText size={14} className="text-indigo-500" />
                            Source referenced
                          </div>
                        </div>
                      )}

                    </div>
                  </div>
                )}

              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
