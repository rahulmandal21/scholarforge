export default function LogoMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <rect x="1.5" y="1.5" width="37" height="37" rx="11" stroke="currentColor" strokeWidth="2.2" />
      <path
        d="M27 14.5c0-2.6-2.7-4.3-7-4.3s-7 1.9-7 4.5c0 6.2 13.6 3.3 13.6 9.6 0 2.7-2.9 4.6-7 4.6s-7.3-1.8-7.6-4.6"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </svg>
  );
}