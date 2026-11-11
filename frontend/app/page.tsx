import type { Metadata } from "next";
import Link from "next/link";

import { AppShell } from "@/components/AppShell";
import { FiltrosTickets } from "@/components/FiltrosTickets";
import { Paginacion } from "@/components/Paginacion";
import { TicketTabla } from "@/components/TicketTabla";
import { listarTickets } from "@/lib/api";
import type { Estado, Prioridad } from "@/types/ticket";

export const metadata: Metadata = {
  title: "Bandeja | Deskly",
};

const POR_PAGINA = 10;
const ESTADOS_VALIDOS: Estado[] = ["abierto", "en_progreso", "resuelto", "cerrado"];
const PRIORIDADES_VALIDAS: Prioridad[] = ["baja", "media", "alta", "critica"];

interface Props {
  searchParams: Promise<{
    estado?: string;
    prioridad?: string;
    q?: string;
    pagina?: string;
  }>;
}

export default async function Home({ searchParams }: Props) {
  const params = await searchParams;

  const estado = ESTADOS_VALIDOS.includes(params.estado as Estado)
    ? (params.estado as Estado)
    : undefined;
  const prioridad = PRIORIDADES_VALIDAS.includes(params.prioridad as Prioridad)
    ? (params.prioridad as Prioridad)
    : undefined;
  const q = params.q?.trim() || undefined;
  const paginaSolicitada = Math.max(1, Number(params.pagina ?? "1") || 1);

  const [pagina, abiertos, enProgreso, criticos, resueltos] = await Promise.all([
    listarTickets({ estado, prioridad, q, pagina: paginaSolicitada, porPagina: POR_PAGINA }),
    listarTickets({ estado: "abierto", porPagina: 1 }),
    listarTickets({ estado: "en_progreso", porPagina: 1 }),
    listarTickets({ prioridad: "critica", porPagina: 1 }),
    listarTickets({ estado: "resuelto", porPagina: 1 }),
  ]);

  const paginaActual = Math.min(pagina.pagina, Math.max(1, pagina.paginas));
  const desde = (paginaActual - 1) * POR_PAGINA;

  return (
    <AppShell>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
            Operacion
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
            Bandeja de tickets
          </h1>
        </div>
        <span className="text-xs text-muted">
          {pagina.total} ticket{pagina.total === 1 ? "" : "s"} en total
        </span>
      </div>

      <section className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card px-4 py-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Abiertos</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">{abiertos.total}</p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
            En progreso
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">
            {enProgreso.total}
          </p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
            Prioridad critica
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-danger">
            {criticos.total}
          </p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Resueltos</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-ok">{resueltos.total}</p>
        </div>
      </section>

      <FiltrosTickets estado={estado} prioridad={prioridad} q={q} />

      {pagina.items.length === 0 ? (
        <div className="card flex flex-col items-center gap-2 px-6 py-16 text-center">
          <h2 className="text-base font-semibold text-ink">Sin tickets por aqui</h2>
          <p className="max-w-sm text-sm text-muted">
            No hay tickets que coincidan con el filtro. Cuando entre uno nuevo aparecera en
            esta lista en vivo.
          </p>
          <Link href="/" className="btn mt-2">
            Limpiar filtros
          </Link>
        </div>
      ) : (
        <TicketTabla tickets={pagina.items} />
      )}

      <Paginacion
        pagina={paginaActual}
        paginas={Math.max(1, pagina.paginas)}
        total={pagina.total}
        desde={desde + 1}
        hasta={Math.min(desde + POR_PAGINA, pagina.total)}
        params={{
          estado,
          prioridad,
          q,
        }}
      />
    </AppShell>
  );
}
