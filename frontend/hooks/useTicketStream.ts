"use client";

import { useEffect, useRef, useState } from "react";

import type { EventoTicket } from "@/types/ticket";
import { urlWebSocket } from "@/lib/ws";

export type EstadoConexion = "conectado" | "desconectado" | "reconectando";

interface Opciones {
  ticketId?: string;
  onEvento: (evento: EventoTicket) => void;
}

interface MensajeStream {
  tipo?: string;
  datos?: EventoTicket["datos"];
}

const TIPOS_EVENTO = new Set(["ticket.creado", "ticket.actualizado", "ticket.comentado"]);
const ESPERA_MAXIMA_MS = 30_000;

/**
 * Suscripcion al WebSocket de tickets con reconexion exponencial.
 *
 * El callback vive en un ref para que cambiar de handler no cierre y reabra
 * la conexion. El cleanup cierra el socket y cancela el reintento pendiente:
 * sin eso, al navegar quedaria un socket huerfano y un timer vivo.
 */
export function useTicketStream({ ticketId, onEvento }: Opciones): {
  estado: EstadoConexion;
} {
  const [estado, setEstado] = useState<EstadoConexion>("desconectado");
  const callback = useRef(onEvento);

  useEffect(() => {
    callback.current = onEvento;
  }, [onEvento]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let cerrado = false;
    let reintento: ReturnType<typeof setTimeout> | null = null;
    let intentos = 0;

    const conectar = () => {
      if (intentos > 0) {
        setEstado("reconectando");
      }
      socket = new WebSocket(urlWebSocket(ticketId));

      socket.onopen = () => {
        intentos = 0;
        setEstado("conectado");
      };

      socket.onmessage = (mensaje) => {
        try {
          const evento = JSON.parse(mensaje.data as string) as MensajeStream;
          if (!evento.tipo || !TIPOS_EVENTO.has(evento.tipo) || !evento.datos) {
            return;
          }
          callback.current({
            tipo: evento.tipo as EventoTicket["tipo"],
            datos: evento.datos,
          });
        } catch {
          // Un mensaje que no es JSON no debe tumbar la suscripcion.
        }
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        if (cerrado) return;
        setEstado("desconectado");
        const espera = Math.min(ESPERA_MAXIMA_MS, 1000 * 2 ** intentos);
        intentos += 1;
        reintento = setTimeout(conectar, espera);
      };
    };

    conectar();

    return () => {
      cerrado = true;
      if (reintento) clearTimeout(reintento);
      socket?.close();
    };
  }, [ticketId]);

  return { estado };
}
