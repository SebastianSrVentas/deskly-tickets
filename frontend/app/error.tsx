"use client";

import { AppShell } from "@/components/AppShell";

export default function ErrorBandeja({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <AppShell>
      <div className="card mx-auto mt-10 flex max-w-lg flex-col gap-3 p-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-danger">
          Error
        </p>
        <h1 className="text-lg font-semibold text-ink">No se pudo cargar la bandeja</h1>
        <p className="text-sm text-muted">
          El servidor no respondio. Revisa que el backend este arriba y vuelve a intentar.
        </p>
        <p className="rounded-md bg-slate-50 px-3 py-2 font-mono text-[11px] text-slate-500">
          {error.message}
          {error.digest ? ` (${error.digest})` : ""}
        </p>
        <button type="button" onClick={reset} className="btn btn-primary self-start">
          Reintentar
        </button>
      </div>
    </AppShell>
  );
}
