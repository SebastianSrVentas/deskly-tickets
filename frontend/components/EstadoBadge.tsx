import { etiquetaEstado } from "@/lib/formato";
import type { Estado } from "@/types/ticket";

export function EstadoBadge({ estado }: { estado: Estado }) {
  return <span className={`badge badge-${estado}`}>{etiquetaEstado(estado)}</span>;
}
