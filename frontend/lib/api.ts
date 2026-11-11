import type { PaginaTickets, Ticket } from "@/types/ticket";

const BASE =
  process.env.API_URL_INTERNA ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

export class ErrorApi extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ErrorApi";
  }
}

export interface FiltrosTickets {
  estado?: string;
  prioridad?: string;
  q?: string;
  pagina?: number;
  porPagina?: number;
}

export async function listarTickets(filtros: FiltrosTickets): Promise<PaginaTickets> {
  const params = new URLSearchParams();

  if (filtros.estado) params.set("estado", filtros.estado);
  if (filtros.prioridad) params.set("prioridad", filtros.prioridad);
  if (filtros.q) params.set("q", filtros.q);
  params.set("pagina", String(filtros.pagina ?? 1));
  params.set("por_pagina", String(filtros.porPagina ?? 10));

  const respuesta = await fetch(`${BASE}/api/tickets?${params.toString()}`, {
    cache: "no-store",
  });

  if (!respuesta.ok) {
    throw new ErrorApi("No se pudo cargar la lista de tickets", respuesta.status);
  }

  return (await respuesta.json()) as PaginaTickets;
}

export async function obtenerTicket(id: string): Promise<Ticket | null> {
  const respuesta = await fetch(`${BASE}/api/tickets/${encodeURIComponent(id)}`, {
    cache: "no-store",
  });

  if (respuesta.status === 404) return null;
  if (!respuesta.ok) {
    throw new ErrorApi("No se pudo cargar el ticket", respuesta.status);
  }

  return (await respuesta.json()) as Ticket;
}
