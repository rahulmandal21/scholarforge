"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import PipelineProgress from "@/components/PipelineProgress";
import KnowledgeGraph, { type KGNode, type KGEdge } from "@/components/KnowledgeGraph";
import CodeViewer, { type EvalResult } from "@/components/CodeViewer";
import ResultCard, { type HFModel } from "@/components/ResultCard";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ViewState = "running" | "done" | "error";

interface PipelineResult {
  parsed_paper: { title: string };
  components: { component_name: string }[];
  knowledge_graph: { nodes: KGNode[]; edges: KGEdge[] };
  generated_codes: Record<string, string>;
  eval_results: Record<string, EvalResult>;
  github_url: string;
  hf_models: HFModel[];
}

export default function ResultPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const [viewState, setViewState] = useState<ViewState>("running");
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState<PipelineResult | null>(null);

  const handleComplete = useCallback(() => {
    setViewState("done");
  }, []);

  const handleError = useCallback((message: string) => {
    setErrorMessage(message);
    setViewState("error");
  }, []);

  useEffect(() => {
    if (viewState !== "done") return;

    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`${API_URL}/result/${jobId}`);
        if (!response.ok) throw new Error("Could not fetch the final result.");
        const data: PipelineResult = await response.json();
        if (!cancelled) setResult(data);
      } catch (err) {
        if (!cancelled) {
          handleError(
            err instanceof Error ? err.message : "Failed to load results."
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [viewState, jobId, handleError]);

  return (
    <div className="flex min-h-screen flex-col bg-[#f8f9fd]">
      <header className="mx-auto flex w-full max-w-5xl items-center gap-2.5 px-8 py-6">
        <a href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 font-mono text-sm font-bold text-white">
            S
          </span>
          <span className="text-lg font-semibold text-slate-900">
            ScholarForge
          </span>
        </a>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-8 pb-24">
        {viewState === "running" && (
          <div className="flex flex-col items-center justify-center py-24">
            <h1 className="mb-2 text-2xl font-semibold text-slate-900">
              Working on it&hellip;
            </h1>
            <p className="mb-12 text-sm text-slate-500">
              This usually takes 2&ndash;4 minutes.
            </p>
            <PipelineProgress
              jobId={jobId}
              onComplete={handleComplete}
              onError={handleError}
            />
          </div>
        )}

        {viewState === "error" && (
          <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center">
            <AlertTriangle className="h-10 w-10 text-red-400" />
            <h1 className="text-xl font-semibold text-slate-900">
              Something went wrong
            </h1>
            <p className="text-sm text-slate-500">{errorMessage}</p>
            <a
              href="/"
              className="mt-2 rounded-full bg-slate-900 px-5 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              Try another paper
            </a>
          </div>
        )}

        {viewState === "done" && !result && (
          <div className="flex flex-col items-center justify-center py-24">
            <p className="text-sm text-slate-400">Loading results&hellip;</p>
          </div>
        )}

        {viewState === "done" && result && (
          <div className="space-y-10 pt-8">
            <div>
              <p className="font-mono text-xs uppercase tracking-wider text-indigo-500">
                Done
              </p>
              <h1 className="mt-1 text-2xl font-semibold text-slate-900">
                {result.parsed_paper?.title || "Generated implementation"}
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                {result.components?.length ?? 0} components generated and
                evaluated
              </p>
            </div>

            <section>
              <h2 className="mb-3 text-sm font-semibold text-slate-700">
                Component dependency graph
              </h2>
              <KnowledgeGraph
                nodes={result.knowledge_graph?.nodes ?? []}
                edges={result.knowledge_graph?.edges ?? []}
              />
            </section>

            <section>
              <h2 className="mb-3 text-sm font-semibold text-slate-700">
                Generated code
              </h2>
              <CodeViewer
                generatedCodes={result.generated_codes ?? {}}
                evalResults={result.eval_results ?? {}}
              />
            </section>

            <section>
              <h2 className="mb-3 text-sm font-semibold text-slate-700">
                Links & resources
              </h2>
              <ResultCard
                githubUrl={result.github_url ?? ""}
                hfModels={result.hf_models ?? []}
              />
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
