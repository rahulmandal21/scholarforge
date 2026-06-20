"use client";

import { useState } from "react";
import { Check, X, Copy, CheckCheck } from "lucide-react";

export interface EvalResult {
  final_score: number | null;
  attempts: number;
  passed: boolean | null;
}

interface CodeViewerProps {
  generatedCodes: Record<string, string>;
  evalResults: Record<string, EvalResult>;
}

function scoreBadgeClasses(score: number | null) {
  if (score === null) return "bg-slate-100 text-slate-500";
  if (score > 0.8) return "bg-emerald-50 text-emerald-600";
  if (score >= 0.6) return "bg-amber-50 text-amber-600";
  return "bg-rose-50 text-rose-600";
}

function formatComponentName(name: string) {
  return name
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function CodeViewer({
  generatedCodes,
  evalResults,
}: CodeViewerProps) {
  const componentNames = Object.keys(generatedCodes);
  const [activeTab, setActiveTab] = useState(componentNames[0] ?? "");
  const [copied, setCopied] = useState(false);

  if (componentNames.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-2xl border border-slate-100 bg-white text-sm text-slate-400">
        No generated code available.
      </div>
    );
  }

  const activeCode = generatedCodes[activeTab] ?? "";
  const activeEval = evalResults[activeTab];

  const handleCopy = async () => {
    await navigator.clipboard.writeText(activeCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white">
      {/* Tabs */}
      <div className="flex flex-wrap gap-1 overflow-x-auto border-b border-slate-100 bg-slate-50/60 px-3 pt-3">
        {componentNames.map((name) => {
          const evalRes = evalResults[name];
          const isActive = name === activeTab;
          return (
            <button
              key={name}
              onClick={() => setActiveTab(name)}
              className={`flex items-center gap-2 rounded-t-lg px-4 py-2 text-xs font-medium transition-colors ${
                isActive
                  ? "bg-white text-slate-900 shadow-[0_-1px_0_0_#e2e8f0_inset]"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {formatComponentName(name)}
              {evalRes?.passed === true && (
                <Check className="h-3 w-3 text-emerald-500" />
              )}
              {evalRes?.passed === false && (
                <X className="h-3 w-3 text-rose-400" />
              )}
            </button>
          );
        })}
      </div>

      {/* Eval score bar */}
      {activeEval && (
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-3">
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${scoreBadgeClasses(
              activeEval.final_score
            )}`}
          >
            {activeEval.final_score !== null
              ? `Score: ${activeEval.final_score.toFixed(2)}`
              : "Score: n/a"}
          </span>
          <span className="text-xs text-slate-400">
            {activeEval.attempts}{" "}
            {activeEval.attempts === 1 ? "attempt" : "attempts"}
          </span>
        </div>
      )}

      {/* Code block */}
      <div className="relative">
        <button
          onClick={handleCopy}
          className="absolute right-4 top-4 flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700"
        >
          {copied ? (
            <>
              <CheckCheck className="h-3.5 w-3.5" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" /> Copy
            </>
          )}
        </button>
        <pre className="max-h-[480px] overflow-auto bg-slate-900 px-5 py-6 text-xs leading-relaxed text-slate-200">
          <code>{activeCode}</code>
        </pre>
      </div>
    </div>
  );
}
