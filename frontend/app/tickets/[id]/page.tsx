import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AccionesTicket } from "@/components/AccionesTicket";
import { AppShell } from "@/components/AppShell";
import { EstadoBadge } from "@/components/EstadoBadge";
import { HiloComentarios } from "@/components/HiloComentarios";
import { PrioridadBadge } from "@/components/PrioridadBadge";
import { obtenerTicket } from "@/lib/api";
import { fechaRelativa } from "@/lib/formato";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const ticket = await obtenerTicket(id);

  // notFound() aqui corre antes del streaming: el status real es 404.
  if (!ticket) {
    notFound();
  }

  return { title: `${ticket.id.slice(-6)} | Deskly` };
}

export default async function DetalleTicket({ params }: Props) {
  const { id } = await params;
  const ticket = await obtenerTicket(id);

  if (!ticket) {
    notFound();
  }

  return (
    <AppShell ticketId={ticket.id}>
      <Link href="/" className="text-xs text-muted transition hover:text-ink">
        Volver a la bandeja
      </Link>

      <div className="mt-3 grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <section className="card p-5">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
              <span className="font-mono" title={ticket.id}>
                #{ticket.id.slice(-6)}
              </span>
              <EstadoBadge estado={ticket.estado} />
            </div>
            <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
              {ticket.titulo}
            </h1>
            <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink-soft">
              {ticket.descripcion}
            </p>
          </section>

          <HiloComentarios
            ticketId={ticket.id}
            comentariosIniciales={ticket.comentarios}
          />
        </div>

        <aside className="space-y-4">
          <section className="card p-4">
            <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Detalle
            </h2>
            <dl className="mt-3 space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <dt className="text-muted">Prioridad</dt>
                <dd>
                  <PrioridadBadge prioridad={ticket.prioridad} />
                </dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-muted">Asignado</dt>
                <dd className="text-ink-soft">
                  {ticket.asignado_a ?? "Sin asignar"}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-muted">Creado</dt>
                <dd className="text-ink-soft">{fechaRelativa(ticket.creado_en)}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-muted">Actualizado</dt>
                <dd className="text-ink-soft">{fechaRelativa(ticket.actualizado_en)}</dd>
              </div>
            </dl>
          </section>

          <section className="card p-4">
            <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Cambiar estado
            </h2>
            <div className="mt-3">
              <AccionesTicket ticketId={ticket.id} estado={ticket.estado} />
            </div>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}
