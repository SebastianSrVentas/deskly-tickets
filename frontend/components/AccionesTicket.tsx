"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { TRANSICIONES } from "@/lib/formato";
import type { Estado } from "@/types/ticket";

const ETIQUETAS: Record<Estado, string> = {
  abierto: "Reabrir",
  en_progreso: "Pasar a en progreso",
  resuelto: "Marcar como resuelto",
  cerrado: "Cerrar ticket",
};

export function AccionesTicket({
  ticketId,
  estado,
}: {
  ticketId: string;
  estado: Estado;
}) {
  const router = useRouter();
  const [enviando, setEnviando] = useState<Estado | null>(null);
  const [error, setError] = useState<string | null>(null);

  const destinos = TRANSICIONES[estado];

  async function cambiar(destino: Estado) {
    setEnviando(destino);
    setError(null);
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    try {
      const respuesta = await fetch(`${base}/api/tickets/${ticketId}/transicion`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado_destino: destino }),
      });

      if (!respuesta.ok) {
        throw new Error(`HTTP ${respuesta.status}`);
      }

      router.refresh();
    } catch {
      setError(
        "No se pudo cambiar el estado. El endpoint estara disponible al completar la fase 3.",
      );
    } finally {
      setEnviando(null);
    }
  }

  if (destinos.length === 0) {
    return (
      <p className="text-xs text-muted">
        El ticket esta cerrado. No admite mas transiciones.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {destinos.map((destino) => (
        <button
          key={destino}
          type="button"
          onClick={() => cambiar(destino)}
          disabled={enviando !== null}
          className={`btn w-full ${destino === "cerrado" ? "" : "btn-primary"}`}
        >
          {enviando === destino ? "Enviando..." : ETIQUETAS[destino]}
        </button>
      ))}
      {error ? <p className="text-xs text-danger">{error}</p> : null}
    </div>
  );
}
