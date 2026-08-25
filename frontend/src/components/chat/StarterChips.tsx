import React from 'react';
import { Repeat, Zap, FileText, CheckSquare } from 'lucide-react';

interface StarterChipsProps {
  onSelectPrompt: (prompt: string, skill?: string) => void;
}

export const StarterChips: React.FC<StarterChipsProps> = ({ onSelectPrompt }) => {
  const starters = [
    {
      title: "Brian Balfour's 4 Growth Loops",
      description: "Synthesize product-led acquisition & retention loop frameworks",
      icon: Repeat,
      color: "text-indigo-500 bg-indigo-500/10 border-indigo-500/20",
      prompt: "What are Brian Balfour's 4 core growth loops and how do they compound retention?",
      skill: undefined,
    },
    {
      title: "Elena Verna's B2B PLG Engine",
      description: "Tactical levers for Product-Led Sales and monetization",
      icon: Zap,
      color: "text-sky-500 bg-sky-500/10 border-sky-500/20",
      prompt: "Explain Elena Verna's frameworks for Product-Led Growth (PLG) and Product-Led Sales (PLS).",
      skill: undefined,
    },
    {
      title: "Ship 30: SaaS Pricing Strategy",
      description: "~1,250-word atomic essay with 1-3-1 cadence & action checklist",
      icon: FileText,
      color: "text-violet-500 bg-violet-500/10 border-violet-500/20",
      prompt: "Write a Ship 30 for 30 essay on B2B SaaS Pricing Strategies and packaging tiers.",
      skill: "ship30",
    },
    {
      title: "Launch Readiness Checklist",
      description: "Interactive HTML/JS tool widget rendered in side sandbox",
      icon: CheckSquare,
      color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
      prompt: "Create an interactive Product Launch Readiness Checklist with dynamic score tracking.",
      skill: undefined,
    },
  ];

  return (
    <div className="w-full max-w-2xl mx-auto px-4 py-8">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-primary/10 border border-primary/20 text-primary mb-3 shadow-inner">
          <Zap className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-foreground">The Lenny Growth Assistant</h2>
        <p className="text-xs sm:text-sm text-muted mt-1 max-w-md mx-auto">
          Executive product & growth advisory grounded strictly in 200+ Lenny's Podcast and Newsletter transcripts.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {starters.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              onClick={() => onSelectPrompt(item.prompt, item.skill)}
              className="cursor-pointer group flex flex-col text-left p-3.5 rounded-xl bg-surface border border-border hover:border-primary/50 hover:shadow-md transition-all duration-200"
            >
              <div className="flex items-center gap-2 mb-1.5">
                <div className={`p-1.5 rounded-lg border ${item.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="font-semibold text-xs sm:text-sm text-foreground group-hover:text-primary transition-colors">
                  {item.title}
                </span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                {item.description}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
