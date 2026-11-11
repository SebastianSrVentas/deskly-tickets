import { etiquetaPrioridad } from "@/lib/formato";
import type { Prioridad } from "@/types/ticket";

export function PrioridadBadge({ prioridad }: { prioridad: Prioridad }) {
  return <span className={`prio prio-${prioridad}`}>{etiquetaPrioridad(prioridad)}</span>;
}
