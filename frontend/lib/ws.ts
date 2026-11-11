/**
 * URL del WebSocket de eventos.
 *
 * En el navegador no existe `API_URL_INTERNA`: se usa la URL publica. Si el
 * backend esta en otro host, define `NEXT_PUBLIC_WS_URL` (por ejemplo
 * `wss://api.deskly.dev`) y se respeta tal cual.
 */
export function urlWebSocket(ticketId?: string): string {
  const explicita = process.env.NEXT_PUBLIC_WS_URL;
  const base =
    explicita ??
    (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^http/, "ws");

  const url = new URL("/ws/tickets", base);
  if (ticketId) {
    url.searchParams.set("ticket_id", ticketId);
  }
  return url.toString();
}
