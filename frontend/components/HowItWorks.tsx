import { FileText, Brain, Code2, CheckCircle } from "lucide-react";

const STEPS = [
  {
    icon: FileText,
    bg: "var(--sf-indigo-soft)",
    color: "#5b5fef",
    step: "01",
    title: "Upload your paper",
    desc: "Drop any ML research paper in PDF format. Works with arXiv papers, conference submissions, and preprints.",
  },
  {
    icon: Brain,
    bg: "rgba(139,92,246,0.12)",
    color: "#8b5cf6",
    step: "02",
    title: "AI reads & reasons",
    desc: "ScholarForge parses the architecture, understands the methodology, and maps out every component.",
  },
  {
    icon: Code2,
    bg: "rgba(59,130,246,0.12)",
    color: "#3b82f6",
    step: "03",
    title: "Code is generated",
    desc: "A complete PyTorch implementation is produced — model architecture, training loop, and data pipeline.",
  },
  {
    icon: CheckCircle,
    bg: "var(--sf-coral-soft)",
    color: "#e2604a",
    step: "04",
    title: "Self-evaluated output",
    desc: "The generated code runs a self-check to verify correctness and flag any issues before you see it.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="flex flex-col gap-10">
      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-[var(--sf-indigo)]">
          How it works
        </p>
        <h2 className="font-display text-3xl font-semibold text-[var(--sf-ink)]">
          From paper to code in seconds
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map(({ icon: Icon, bg, color, step, title, desc }) => (
          <div
            key={step}
            className="flex flex-col gap-4 rounded-2xl border border-[var(--sf-line)] bg-[var(--sf-card)] p-6"
          >
            <div className="flex items-center justify-between">
              <span
                className="flex h-11 w-11 items-center justify-center rounded-xl"
                style={{ background: bg }}
              >
                <Icon className="h-5 w-5" style={{ color }} strokeWidth={1.75} />
              </span>
              <span className="font-mono text-2xl font-semibold text-[var(--sf-line)]">
                {step}
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              <p className="text-sm font-semibold text-[var(--sf-ink)]">{title}</p>
              <p className="text-xs leading-relaxed text-[var(--sf-text-dim)]">{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}