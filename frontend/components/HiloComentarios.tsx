"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { fechaRelativa, iniciales } from "@/lib/formato";
import type { Comentario, Ticket } from "@/types/ticket";

/**
 * Hilo de comentarios con actualizacion optimista.
 *
 * El comentario temporal entra en la lista antes de que responda el servidor.
 * Si el POST falla, se quita y se muestra el error. Si responde, la propia
 * respuesta trae el ticket completo, asi que se reemplaza el temporal por los
 * comentarios reales sin depender de un refresh (que provocaria un parpadeo).
 *
 * `router.refresh()` se mantiene para sincronizar el resto del detalle si el
 * cambio vino de otro agente.
 */
export function HiloComentarios({
  ticketId,
  comentariosIniciales,
}: {
  ticketId: string;
  comentariosIniciales: Comentario[];
}) {
  const router = useRouter();
  const formulario = useRef<HTMLFormElement>(null);
  const [comentarios, setComentarios] = useState(comentariosIniciales);
  const [error, setError] = useState<string | null>(null);
  const [pendiente, startTransition] = useTransition();

  useEffect(() => {
    setComentarios(comentariosIniciales);
  }, [comentariosIniciales]);

  function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    enviar(new FormData(evento.currentTarget));
  }

  function enviar(datos: FormData) {
    const autor = String(datos.get("autor") ?? "").trim();
    const texto = String(datos.get("texto") ?? "").trim();

    if (!autor || !texto) {
      setError("Escribe tu nombre y el comentario.");
      return;
    }

    setError(null);
    const temporal: Comentario = {
      id: `temp-${Date.now()}`,
      autor,
      texto,
      creado_en: new Date().toISOString(),
    };
    setComentarios((actuales) => [...actuales, temporal]);

    startTransition(async () => {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

      try {
        const respuesta = await fetch(`${base}/api/tickets/${ticketId}/comentarios`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ autor, texto }),
        });

        if (!respuesta.ok) {
          setComentarios((actuales) => actuales.filter((item) => item.id !== temporal.id));
          setError(
            respuesta.status === 409
              ? "El ticket cambio mientras comentabas. Recarga e intenta de nuevo."
              : "No se pudo guardar el comentario. Se revirtio el cambio.",
          );
          return;
        }

        const ticket = (await respuesta.json()) as Ticket;
        setComentarios(ticket.comentarios);
        formulario.current?.reset();
        router.refresh();
      } catch {
        setComentarios((actuales) => actuales.filter((item) => item.id !== temporal.id));
        setError("No se pudo conectar con el servidor. Se revirtio el comentario.");
      }
    });
  }

  return (
    <section className="card p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">Comentarios</h2>
        <span className="text-xs text-muted">{comentarios.length}</span>
      </div>

      <div className="mt-4 space-y-4">
        {comentarios.length === 0 ? (
          <p className="text-sm text-muted">Todavia no hay comentarios en este ticket.</p>
        ) : (
          comentarios.map((comentario) => {
            const esTemporal = comentario.id.startsWith("temp-");
            return (
              <article
                key={comentario.id}
                className={`flex gap-3 ${esTemporal ? "opacity-60" : ""}`}
              >
                <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-brand-soft text-[10px] font-semibold text-brand">
                  {iniciales(comentario.autor)}
                </span>
                <div className="min-w-0">
                  <div className="flex items-baseline gap-2">
                    <p className="text-[13px] font-medium text-ink">{comentario.autor}</p>
                    <p className="text-[11px] text-muted">
                      {esTemporal ? "Enviando..." : fechaRelativa(comentario.creado_en)}
                    </p>
                  </div>
                  <p className="mt-0.5 text-sm leading-relaxed text-ink-soft">
                    {comentario.texto}
                  </p>
                </div>
              </article>
            );
          })
        )}
      </div>

      <form ref={formulario} onSubmit={alEnviar} className="mt-4 border-t border-line pt-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input sm:w-48"
            name="autor"
            placeholder="Tu nombre"
            maxLength={80}
            required
          />
          <input
            className="input flex-1"
            name="texto"
            placeholder="Escribe un comentario"
            maxLength={2000}
            required
          />
          <button type="submit" className="btn btn-primary" disabled={pendiente}>
            {pendiente ? "Enviando..." : "Comentar"}
          </button>
        </div>
        {error ? (
          <p className="mt-2 text-xs text-danger" role="alert">
            {error}
          </p>
        ) : null}
      </form>
    </section>
  );
}
