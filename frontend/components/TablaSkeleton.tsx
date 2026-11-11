export function TablaSkeleton() {
  return (
    <div className="card overflow-hidden" aria-hidden="true">
      <div className="h-10 border-b border-line bg-slate-50" />
      {[0, 1, 2, 3, 4, 5].map((indice) => (
        <div
          key={indice}
          className="flex items-center gap-6 border-b border-line/70 px-4 py-4 last:border-0"
        >
          <div className="h-3 w-14 animate-pulse rounded bg-slate-200" />
          <div className="h-3 flex-1 animate-pulse rounded bg-slate-200" />
          <div className="h-5 w-20 animate-pulse rounded bg-slate-200" />
          <div className="h-5 w-24 animate-pulse rounded bg-slate-200" />
        </div>
      ))}
    </div>
  );
}

export function ResumenSkeleton() {
  return (
    <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-hidden="true">
      {[0, 1, 2, 3].map((indice) => (
        <div key={indice} className="card px-4 py-3">
          <div className="h-3 w-16 animate-pulse rounded bg-slate-200" />
          <div className="mt-2 h-6 w-10 animate-pulse rounded bg-slate-200" />
        </div>
      ))}
    </div>
  );
}
