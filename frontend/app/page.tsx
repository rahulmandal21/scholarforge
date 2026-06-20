import { BookOpen, Code2, Box } from "lucide-react";

import PDFUploader from "@/components/PDFUploader";
import UploadContextStrip from "@/components/UploadContextStrip";

import HowItWorks from "@/components/HowItWorks";


const FEATURE_PILLS = [
  { icon: BookOpen, bg: "var(--sf-indigo-soft)", color: "#5b5fef", title: "Read", sub: "Paper parsing" },
  { icon: Code2, bg: "rgba(59,130,246,0.12)", color: "#3b82f6", title: "Reason", sub: "Model reasoning" },
  { icon: Box, bg: "var(--sf-coral-soft)", color: "#e2604a", title: "Generate", sub: "PyTorch code" },
];

export default function Home() {
  return (
    <main className="mx-auto flex max-w-7xl w-full flex-1 flex-col gap-12 px-10 py-24">
      <section className="grid grid-cols-1 items-center gap-16 lg:grid-cols-2">
        <div className="flex flex-col gap-8">
          <div className="flex flex-wrap items-center gap-4">
            <span
              className="rounded-full px-4 py-1.5 font-mono text-xs uppercase tracking-[0.2em]"
              style={{ background: "linear-gradient(90deg, var(--sf-indigo-soft), var(--sf-coral-soft))" }}
            >
              <span className="text-[var(--sf-indigo)]">PDF</span>
              <span className="text-[var(--sf-text-dim)]"> &rarr; </span>
              <span className="text-[var(--sf-coral)]">PYTHON</span>
            </span>
            <span className="flex items-center gap-1.5 text-xs text-[var(--sf-text-dim)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--sf-green)]" />
              100% local &middot; Privacy first
            </span>
          </div>

          <h1 className="font-display max-w-xl text-6xl leading-[1.05] font-semibold text-[var(--sf-ink)] lg:text-7xl">
            Drop a paper.
            <br />
            <span
              className="italic"
              style={{
                background: "linear-gradient(90deg, #5b5fef, #8b5cf6)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              Get back code.
            </span>
          </h1>

          <p className="max-w-md text-lg text-[var(--sf-text)]">
            ScholarForge reads any ML research paper and generates a working,
            self-evaluated PyTorch implementation — architecture, training
            loop, and all.
          </p>

          <div className="flex flex-wrap gap-8 pt-2">
            {FEATURE_PILLS.map(({ icon: Icon, bg, color, title, sub }) => (
              <div key={title} className="flex items-center gap-3">
                <span
                  className="flex h-12 w-12 items-center justify-center rounded-xl"
                  style={{ background: bg }}
                >
                  <Icon className="h-6 w-6" style={{ color }} strokeWidth={1.75} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-[var(--sf-ink)]">{title}</p>
                  <p className="text-xs text-[var(--sf-text-dim)]">{sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT COLUMN — uploader */}
        <div className="w-full flex items-center justify-center">
          <div className="w-full">
            <UploadContextStrip />
            <PDFUploader />
          </div>
        </div>
      </section>
<HowItWorks />
     
    </main>
  );
}