"use client";

import { useEffect, useState } from "react";

const TIPS = [
  "Most papers hide their training details in the appendix — ScholarForge reads those too.",
  "Pseudocode in a figure counts as architecture. We parse it like text.",
  "Ambiguous hyperparameters get a documented best guess, not a silent skip.",
  "Multi-stage training (pretrain → fine-tune) is reconstructed as separate loops.",
  "Cited baselines aren't reimplemented — only the paper's own contribution is.",
];

export default function UploadContextStrip() {
  const [tipIndex, setTipIndex] = useState(0);

  useEffect(() => {
    const tipTimer = setInterval(() => {
      setTipIndex((i) => (i + 1) % TIPS.length);
    }, 5000);
    return () => clearInterval(tipTimer);
  }, []);

  return (
    <div className="mb-3 text-xs">
      <p
        key={tipIndex}
        className="animate-[fadeIn_0.4s_ease-out] text-[var(--sf-ink)]/60"
      >
        <span className="font-semibold text-[var(--sf-indigo)]">Tip — </span>
        {TIPS[tipIndex]}
      </p>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(2px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}