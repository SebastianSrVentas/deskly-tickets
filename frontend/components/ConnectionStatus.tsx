"use client";

import type { EstadoConexion } from "@/hooks/useTicketStream";

const ETIQUETAS: Record<EstadoConexion, string> = {
  conectado: "Conectado",
  desconectado: "Desconectado",
  reconectando: "Reconectando",
};

const COLORES: Record<EstadoConexion, string> = {
  conectado: "bg-emerald-400",
  desconectado: "bg-red-400",
  reconectando: "bg-amber-400",
};

export function ConnectionStatus({ estado }: { estado: EstadoConexion }) {
  return (
    <span
      className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11.5px] text-slate-300"
      title={`WebSocket: ${ETIQUETAS[estado].toLowerCase()}`}
      role="status"
      aria-live="polite"
    >
      <span
        className={`size-1.5 rounded-full ${COLORES[estado]} ${
          estado === "reconectando" ? "animate-pulse" : ""
        }`}
      />
      {ETIQUETAS[estado]}
    </span>
  );
}
