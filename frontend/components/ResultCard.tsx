import { ExternalLink, Download } from "lucide-react";

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

export interface HFModel {
  model_id: string;
  task: string;
  downloads: number;
  model_url: string;
}

interface ResultCardProps {
  githubUrl: string;
  hfModels: HFModel[];
}

export default function ResultCard({ githubUrl, hfModels }: ResultCardProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {githubUrl && (
        <a
          href={githubUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white p-5 transition-colors hover:border-indigo-200"
        >
          <span className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900">
              <GithubIcon className="h-5 w-5 text-white" />
            </span>
            <span>
              <p className="text-sm font-semibold text-slate-800">
                View on GitHub
              </p>
              <p className="text-xs text-slate-400">
                Code pushed to a new public repo
              </p>
            </span>
          </span>
          <ExternalLink className="h-4 w-4 text-slate-300" />
        </a>
      )}

      {hfModels.length > 0 && (
        <div className="rounded-2xl border border-slate-100 bg-white p-5">
          <p className="mb-3 text-sm font-semibold text-slate-800">
            Related HuggingFace models
          </p>
          <ul className="space-y-2">
            {hfModels.slice(0, 4).map((model) => (
              <li key={model.model_id}>
                <a
                  href={model.model_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between gap-2 text-xs text-slate-500 hover:text-indigo-600"
                >
                  <span className="flex items-center gap-1.5 truncate">
                    <Download className="h-3 w-3 shrink-0" />
                    <span className="truncate font-mono">
                      {model.model_id}
                    </span>
                  </span>
                  <span className="shrink-0 text-slate-300">
                    {model.downloads.toLocaleString()}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
