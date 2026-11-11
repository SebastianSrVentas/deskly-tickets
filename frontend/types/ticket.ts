import type { components } from "./api";

type TicketApi = components["schemas"]["TicketSalida"];

export type Estado = components["schemas"]["Estado"];

export type Prioridad = components["schemas"]["Prioridad"];

export type Comentario = components["schemas"]["ComentarioSalida"];

/**
 * El OpenAPI marca `comentarios` como opcional porque Pydantic tiene un
 * default_factory. El backend siempre lo devuelve; el frontend lo exige para
 * no arrastrar `undefined` por todos los componentes.
 */
export type Ticket = Omit<TicketApi, "comentarios"> & {
  comentarios: Comentario[];
};

export type PaginaTickets = Omit<components["schemas"]["PaginaTickets"], "items"> & {
  items: Ticket[];
};

export interface EventoTicket {
  tipo: "ticket.creado" | "ticket.actualizado" | "ticket.comentado";
  datos: Ticket;
}
