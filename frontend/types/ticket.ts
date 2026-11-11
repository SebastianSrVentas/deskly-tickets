export type Estado = "abierto" | "en_progreso" | "resuelto" | "cerrado";

export type Prioridad = "baja" | "media" | "alta" | "critica";

export interface Comentario {
  id: string;
  autor: string;
  texto: string;
  creado_en: string;
}

export interface Ticket {
  id: string;
  titulo: string;
  descripcion: string;
  prioridad: Prioridad;
  estado: Estado;
  asignado_a: string | null;
  comentarios: Comentario[];
  creado_en: string;
  actualizado_en: string;
}

export interface PaginaTickets {
  items: Ticket[];
  total: number;
  pagina: number;
  por_pagina: number;
  paginas: number;
}

export interface EventoTicket {
  tipo: "ticket.creado" | "ticket.actualizado" | "ticket.comentado";
  datos: Ticket;
}
