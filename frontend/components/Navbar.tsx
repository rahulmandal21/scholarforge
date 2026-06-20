import Link from "next/link";
import LogoMark from "./LogoMark";
import ForgeSpark from "./ForgeSpark";
 
export default function Navbar() {
  return (
    <header className="sticky top-0 z-30 bg-white/60 backdrop-blur-xl border-b border-[var(--sf-line)]/50">
      <div className="mx-auto flex max-w-7xl w-full items-center justify-between px-10 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--sf-line)] bg-white text-[var(--sf-indigo)]">
            <LogoMark className="h-5 w-5" />
          </span>
          <span className="font-display text-lg font-semibold text-[var(--sf-ink)]">
            ScholarForge
          </span>
        </Link>
 
        <ForgeSpark className="h-9 w-9" />
      </div>
    </header>
  );
}
 