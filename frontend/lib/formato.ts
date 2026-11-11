import type { Estado, Prioridad } from "@/types/ticket";

const ETIQUETAS_ESTADO: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
};

const ETIQUETAS_PRIORIDAD: Record<Prioridad, string> = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  critica: "Critica",
};

export function etiquetaEstado(estado: Estado): string {
  return ETIQUETAS_ESTADO[estado];
}

export function etiquetaPrioridad(prioridad: Prioridad): string {
  return ETIQUETAS_PRIORIDAD[prioridad];
}

export function iniciales(nombre: string | null): string {
  if (!nombre) return "?";
  return nombre
    .split(" ")
    .map((parte) => parte[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function fechaRelativa(iso: string): string {
  const diferencia = Date.now() - new Date(iso).getTime();
  const minutos = Math.floor(diferencia / 60_000);

  if (minutos < 1) return "ahora";
  if (minutos < 60) return `hace ${minutos} min`;

  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;

  const dias = Math.floor(horas / 24);
  if (dias === 1) return "ayer";
  return `hace ${dias} dias`;
}

export const TRANSICIONES: Record<Estado, Estado[]> = {
  abierto: ["en_progreso"],
  en_progreso: ["resuelto"],
  resuelto: ["cerrado", "abierto"],
  cerrado: [],
};
