"use client";

import { useEffect, useState } from "react";

/**
 * ForgeSpark — a tiny mascot built from the same gem silhouette as LogoMark,
 * given a face. Idles with a slow ambient blink; waves on hover so it feels
 * alive without ever competing with the page for attention.
 */
export default function ForgeSpark({ className = "h-9 w-9" }: { className?: string }) {
  const [blink, setBlink] = useState(false);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const scheduleBlink = () => {
      // Ambient, irregular blink — every 3.5–6.5s, not a tight loop.
      const delay = 3500 + Math.random() * 3000;
      timeout = setTimeout(() => {
        setBlink(true);
        setTimeout(() => setBlink(false), 140);
        scheduleBlink();
      }, delay);
    };
    scheduleBlink();
    return () => clearTimeout(timeout);
  }, []);

  return (
    <span
      className={`group relative inline-flex ${className} cursor-default items-center justify-center`}
      role="img"
      aria-label="ScholarForge mascot"
    >
      <svg
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="h-full w-full transition-transform duration-300 ease-out group-hover:-rotate-6 group-hover:scale-110"
      >
        {/* Gem body, echoing LogoMark's silhouette */}
        <path
          d="M18 2 L32 13 L26 33 L10 33 L4 13 Z"
          fill="var(--sf-indigo)"
          className="opacity-90"
        />
        <path
          d="M18 2 L32 13 L18 18 Z"
          fill="white"
          className="opacity-25"
        />
        <path d="M18 2 L4 13 L18 18 Z" fill="white" className="opacity-10" />

        {/* Face */}
        {blink ? (
          <>
            <line x1="12.5" y1="17" x2="15.5" y2="17" stroke="white" strokeWidth="1.6" strokeLinecap="round" />
            <line x1="20.5" y1="17" x2="23.5" y2="17" stroke="white" strokeWidth="1.6" strokeLinecap="round" />
          </>
        ) : (
          <>
            <circle cx="14" cy="17" r="1.6" fill="white" />
            <circle cx="22" cy="17" r="1.6" fill="white" />
          </>
        )}
        <path
          d="M14.5 22 Q18 25 21.5 22"
          stroke="white"
          strokeWidth="1.6"
          strokeLinecap="round"
          fill="none"
        />

        {/* Little waving arm — only animates on hover */}
        <path
          d="M27 20 Q31 18 31 14"
          stroke="var(--sf-indigo)"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
          className="origin-[27px_20px] opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-hover:animate-[wave_0.6s_ease-in-out_2]"
        />
      </svg>

      <style jsx>{`
        @keyframes wave {
          0%,
          100% {
            transform: rotate(0deg);
          }
          50% {
            transform: rotate(25deg);
          }
        }
      `}</style>
    </span>
  );
}