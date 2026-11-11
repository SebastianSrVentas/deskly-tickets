"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function ComentarioForm({ ticketId }: { ticketId: string }) {
  const router = useRouter();
  const [autor, setAutor] = useState("");
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    try {
      const respuesta = await fetch(`${base}/api/tickets/${ticketId}/comentarios`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ autor, texto }),
      });

      if (!respuesta.ok) {
        throw new Error(`HTTP ${respuesta.status}`);
      }

      setTexto("");
      router.refresh();
    } catch {
      setError(
        "No se pudo enviar el comentario. El endpoint estara disponible al completar la fase 3.",
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="mt-4 border-t border-line pt-4">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          className="input sm:w-48"
          placeholder="Tu nombre"
          value={autor}
          onChange={(evento) => setAutor(evento.target.value)}
          required
        />
        <input
          className="input flex-1"
          placeholder="Escribe un comentario"
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          required
        />
        <button type="submit" className="btn btn-primary" disabled={enviando}>
          {enviando ? "Enviando..." : "Comentar"}
        </button>
      </div>
      {error ? <p className="mt-2 text-xs text-danger">{error}</p> : null}
    </form>
  );
}
