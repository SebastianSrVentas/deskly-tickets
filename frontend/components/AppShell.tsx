"use client";

import Link from "next/link";

import { LiveTickets } from "@/components/LiveTickets";

export function AppShell({
  children,
  ticketId,
}: {
  children: React.ReactNode;
  ticketId?: string;
}) {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-900 text-slate-200">
        <div className="mx-auto flex h-14 max-w-[1280px] items-center gap-4 px-5">
          <Link href="/" className="flex items-center gap-2 font-semibold text-white">
            <span className="grid size-6 place-items-center rounded-md bg-brand text-[11px] font-bold">
              D
            </span>
            Deskly
          </Link>

          <nav className="ml-4 flex gap-1 text-[13px]">
            <Link
              href="/"
              className="rounded-md bg-slate-800 px-2.5 py-1.5 font-medium text-white"
            >
              Bandeja
            </Link>
            <span className="px-2.5 py-1.5 text-slate-400">Equipo</span>
            <span className="px-2.5 py-1.5 text-slate-400">Ajustes</span>
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <LiveTickets ticketId={ticketId} />
            <span className="grid size-7 place-items-center rounded-full bg-slate-700 text-[10px] font-semibold text-slate-100">
              SR
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1280px] px-5 py-6">{children}</main>
    </div>
  );
}
