export function DataShelfFallback() {
  return (
    <div className="card flex h-52 items-center justify-center p-4">
      <svg viewBox="0 0 360 160" className="h-full w-full" role="img" aria-label="Data shelf illustration">
        <defs>
          <linearGradient id="shelf" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#1d3b5f" />
            <stop offset="100%" stopColor="#0b1626" />
          </linearGradient>
        </defs>
        <rect x="30" y="120" width="300" height="14" rx="7" fill="url(#shelf)" />
        <rect x="72" y="65" width="48" height="48" rx="8" fill="#37b5ff" opacity="0.85" />
        <rect x="152" y="45" width="56" height="56" rx="8" fill="#35d39d" opacity="0.78" />
        <rect x="244" y="78" width="42" height="42" rx="8" fill="#ffc857" opacity="0.82" />
      </svg>
    </div>
  );
}
