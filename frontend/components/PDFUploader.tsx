"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { UploadCloud, Loader2, ChevronDown } from "lucide-react";

function GithubIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.57.1.78-.25.78-.55 0-.27-.01-1.16-.02-2.11-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.05 11.05 0 0 1 5.79 0c2.2-1.49 3.18-1.18 3.18-1.18.62 1.59.23 2.76.11 3.05.74.8 1.18 1.83 1.18 3.09 0 4.42-2.7 5.4-5.26 5.68.41.36.78 1.07.78 2.15 0 1.55-.01 2.8-.01 3.18 0 .3.21.66.79.55A10.51 10.51 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5Z" />
    </svg>
  );
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Status = "idle" | "dragging" | "uploading" | "error";

export default function PDFUploader() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [fileName, setFileName] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);

  const uploadFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setStatus("error");
        setErrorMessage("Only PDF files are supported.");
        return;
      }

      setFileName(file.name);
      setStatus("uploading");
      setErrorMessage("");

      try {
        const formData = new FormData();
        formData.append("file", file);
        // Optional: only included if the user chose to provide their own
        // GitHub token. Without it, the backend still runs the full
        // pipeline but skips pushing code anywhere — it never falls back
        // to pushing into the server operator's own GitHub account.
        if (githubToken.trim()) {
          formData.append("github_token", githubToken.trim());
        }

        const response = await fetch(`${API_URL}/upload-paper`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(
            detail?.detail ||
              "Upload failed. Check that the backend server is running."
          );
        }

        const data = await response.json();
        router.push(`/result/${data.job_id}`);
      } catch (err) {
        setStatus("error");
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "Something went wrong. Is the backend running on port 8000?"
        );
      }
    },
    [router, githubToken]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file) uploadFile(file);
    },
    [uploadFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setStatus((s) => (s === "uploading" ? s : "dragging"));
  }, []);

  const handleDragLeave = useCallback(() => {
    setStatus((s) => (s === "dragging" ? "idle" : s));
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) uploadFile(file);
    },
    [uploadFile]
  );

  const isDragging = status === "dragging";
  const isUploading = status === "uploading";
  const isError = status === "error";

  return (
    <div id="upload" className="w-full">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isUploading && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        className={`relative flex flex-col items-center gap-5 overflow-hidden rounded-2xl border-2 border-dashed px-8 py-24 text-center transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sf-indigo)]
          ${
            isDragging
              ? "border-[var(--sf-indigo)] bg-[var(--sf-indigo-soft)]"
              : "border-[var(--sf-line)] bg-[var(--sf-card)] hover:border-[var(--sf-indigo)]/50"
          }
          ${isUploading ? "cursor-wait opacity-90" : ""}`}
      >
        {isDragging && (
          <span className="flow-pulse pointer-events-none absolute left-0 right-0 top-0 h-px bg-[var(--sf-indigo)]" />
        )}

        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileSelect}
          disabled={isUploading}
        />

        {isUploading ? (
          <Loader2 className="h-9 w-9 animate-spin text-[var(--sf-indigo)]" strokeWidth={1.5} />
        ) : (
          <UploadCloud className="h-9 w-9 text-[var(--sf-indigo)]" strokeWidth={1.5} />
        )}

        <div className="pointer-events-none space-y-1.5">
          {isUploading ? (
            <p className="text-base font-medium text-[var(--sf-ink)]">
              Uploading {fileName}&hellip;
            </p>
          ) : (
            <p className="text-base font-medium text-[var(--sf-ink)]">
              Drop your paper here, or{" "}
              <span className="text-[var(--sf-indigo)] underline-offset-4">
                click to browse
              </span>
            </p>
          )}
          <p className="text-sm text-[var(--sf-text-dim)]">PDF only &middot; Up to 50MB</p>
        </div>

        <span className="pointer-events-none rounded-full bg-[var(--sf-card-2)] px-4 py-1.5 text-xs text-[var(--sf-text-dim)]">
          No signup required &middot; Groq-powered backend
        </span>
      </div>

      {isError && (
        <p className="mt-3 text-center text-sm text-[var(--sf-coral)]">
          {errorMessage}
        </p>
      )}

      {/* Optional: push generated code to the uploader's own GitHub account.
          Sits outside the dropzone so clicking it doesn't trigger the file
          picker. Collapsed by default to keep the primary flow (just drop
          a PDF) uncluttered for people who don't need this. */}
      {!isUploading && (
        <div className="mt-5 flex justify-center">
          <div className="w-full max-w-sm">
            <button
              type="button"
              onClick={() => setShowTokenInput((v) => !v)}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--sf-indigo)]/30 bg-[var(--sf-indigo-soft)] px-5 py-3 text-sm font-medium text-[var(--sf-indigo)] transition-colors hover:border-[var(--sf-indigo)]/60 hover:bg-[var(--sf-indigo-soft)]/80"
            >
              <GithubIcon className="h-4 w-4" />
              Push code to your own GitHub
              <span className="text-xs font-normal text-[var(--sf-indigo)]/70">
                (optional)
              </span>
              <ChevronDown
                className={`h-4 w-4 transition-transform ${
                  showTokenInput ? "rotate-180" : ""
                }`}
                strokeWidth={1.5}
              />
            </button>

            {showTokenInput && (
              <div className="mt-3 rounded-xl border border-[var(--sf-line)] bg-[var(--sf-card)] p-4">
                <input
                  type="password"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  className="w-full rounded-lg border border-[var(--sf-line)] bg-[var(--sf-card-2)] px-4 py-2.5 text-sm text-[var(--sf-ink)] placeholder:text-[var(--sf-text-dim)] focus:outline-none focus:ring-2 focus:ring-[var(--sf-indigo)]"
                />
                <p className="mt-2 text-xs text-[var(--sf-text-dim)]">
                  Leave blank to skip GitHub entirely — your code will still
                  be generated and viewable here either way. Your token is
                  sent directly to this app&apos;s backend for this one
                  request and isn&apos;t stored.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}