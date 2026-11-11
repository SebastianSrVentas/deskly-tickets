"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";

import { ConnectionStatus } from "@/components/ConnectionStatus";
import { useTicketStream } from "@/hooks/useTicketStream";

/**
 * Puente entre el WebSocket y los Server Components.
 *
 * `router.refresh()` vuelve a pedir el RSC de la ruta actual sin recargar la
 * pagina. El debounce evita una revalidacion por cada evento cuando llega una
 * rafaga (por ejemplo, varios agentes comentando a la vez).
 */
export function LiveTickets({ ticketId }: { ticketId?: string }) {
  const router = useRouter();
  const pendiente = useRef<ReturnType<typeof setTimeout> | null>(null);

  const alEvento = useCallback(() => {
    if (pendiente.current) clearTimeout(pendiente.current);
    pendiente.current = setTimeout(() => router.refresh(), 300);
  }, [router]);

  useEffect(
    () => () => {
      if (pendiente.current) clearTimeout(pendiente.current);
    },
    [],
  );

  const { estado } = useTicketStream({ ticketId, onEvento: alEvento });
  return <ConnectionStatus estado={estado} />;
}
