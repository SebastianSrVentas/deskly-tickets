import Link from "next/link";

import { EstadoBadge } from "@/components/EstadoBadge";
import { PrioridadBadge } from "@/components/PrioridadBadge";
import { fechaRelativa, iniciales } from "@/lib/formato";
import type { Ticket } from "@/types/ticket";

export function TicketTabla({ tickets }: { tickets: Ticket[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line bg-slate-50 text-left text-[11px] uppercase tracking-[0.05em] text-muted">
              <th className="w-[92px] px-4 py-2.5 font-semibold">ID</th>
              <th className="px-4 py-2.5 font-semibold">Ticket</th>
              <th className="w-[96px] px-4 py-2.5 font-semibold">Prioridad</th>
              <th className="w-[132px] px-4 py-2.5 font-semibold">Estado</th>
              <th className="w-[168px] px-4 py-2.5 font-semibold">Asignado</th>
              <th className="w-[104px] px-4 py-2.5 font-semibold">Creado</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((ticket) => (
              <tr
                key={ticket.id}
                className="border-b border-line/70 last:border-0 hover:bg-slate-50/80"
              >
                <td
                  className="px-4 py-3 font-mono text-[11px] text-muted"
                  title={ticket.id}
                >
                  #{ticket.id.slice(-6)}
                </td>
                <td className="px-4 py-3">
                  <Link
                    href={`/tickets/${ticket.id}`}
                    className="font-medium text-ink hover:text-brand"
                  >
                    {ticket.titulo}
                  </Link>
                  <p className="mt-0.5 line-clamp-1 max-w-[560px] text-xs text-muted">
                    {ticket.descripcion}
                  </p>
                </td>
                <td className="px-4 py-3">
                  <PrioridadBadge prioridad={ticket.prioridad} />
                </td>
                <td className="px-4 py-3">
                  <EstadoBadge estado={ticket.estado} />
                </td>
                <td className="px-4 py-3">
                  {ticket.asignado_a ? (
                    <span className="flex items-center gap-2 text-ink-soft">
                      <span className="grid size-5 place-items-center rounded-full bg-slate-200 text-[9px] font-semibold text-slate-600">
                        {iniciales(ticket.asignado_a)}
                      </span>
                      {ticket.asignado_a}
                    </span>
                  ) : (
                    <span className="text-xs text-muted">Sin asignar</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  {fechaRelativa(ticket.creado_en)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
