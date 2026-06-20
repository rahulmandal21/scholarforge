"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Maps your LangGraph node names (Phase 9) to human-friendly stage labels.
// Order here defines the order shown in the stepper.
const STAGES = [
  { key: "parse_node", label: "Parsing PDF" },
  { key: "decompose_node", label: "Decomposing paper" },
  { key: "kg_node", label: "Building knowledge graph" },
  { key: "retrieve_node", label: "Retrieving similar code" },
  { key: "codegen_eval_node", label: "Generating & evaluating code" },
  { key: "mcp_push_node", label: "Pushing to GitHub" },
] as const;

type JobStatus = {
  status: "queued" | "running" | "done" | "error";
  stage: string;
  progress_percent: number;
  message: string;
};

interface PipelineProgressProps {
  jobId: string;
  onComplete: () => void;
  onError: (message: string) => void;
}

export default function PipelineProgress({
  jobId,
  onComplete,
  onError,
}: PipelineProgressProps) {
  const [job, setJob] = useState<JobStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const response = await fetch(`${API_URL}/status/${jobId}`);
        if (!response.ok) {
          throw new Error("Could not fetch job status.");
        }
        const data: JobStatus = await response.json();
        if (cancelled) return;

        setJob(data);

        if (data.status === "done") {
          onComplete();
          return; // stop polling
        }
        if (data.status === "error") {
          onError(data.message || "Pipeline failed.");
          return; // stop polling
        }
        timeoutId = setTimeout(poll, 2000);
      } catch (err) {
        if (cancelled) return;
        onError(
          err instanceof Error ? err.message : "Lost connection to backend."
        );
      }
    };

    poll();

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [jobId, onComplete, onError]);

  const currentStageIndex = job
    ? STAGES.findIndex((s) => s.key === job.stage)
    : -1;

  return (
    <div className="mx-auto w-full max-w-lg">
      {/* Overall progress bar */}
      <div className="mb-8 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-700 ease-out"
          style={{ width: `${job?.progress_percent ?? 0}%` }}
        />
      </div>

      <ol className="space-y-5">
        {STAGES.map((stage, index) => {
          const isComplete =
            currentStageIndex > index ||
            (currentStageIndex === index && job?.status === "done");
          const isActive = currentStageIndex === index && job?.status !== "done";

          return (
            <li key={stage.key} className="flex items-center gap-4">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center">
                {isComplete ? (
                  <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                ) : isActive ? (
                  <span className="relative flex h-4 w-4">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
                    <span className="relative inline-flex h-4 w-4 rounded-full bg-indigo-500" />
                  </span>
                ) : (
                  <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                )}
              </span>
              <span
                className={`text-sm ${
                  isActive
                    ? "font-semibold text-slate-900"
                    : isComplete
                    ? "text-slate-500 line-through decoration-slate-300"
                    : "text-slate-400"
                }`}
              >
                {stage.label}
              </span>
            </li>
          );
        })}
      </ol>

      {job && (
        <p className="mt-8 flex items-center justify-center gap-2 text-center font-mono text-xs text-slate-400">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          {job.message}
        </p>
      )}
    </div>
  );
}
