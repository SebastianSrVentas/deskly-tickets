import Link from "next/link";

const ESTADOS: { valor: string; etiqueta: string }[] = [
  { valor: "", etiqueta: "Todos" },
  { valor: "abierto", etiqueta: "Abierto" },
  { valor: "en_progreso", etiqueta: "En progreso" },
  { valor: "resuelto", etiqueta: "Resuelto" },
  { valor: "cerrado", etiqueta: "Cerrado" },
];

const PRIORIDADES = [
  { valor: "", etiqueta: "Todas las prioridades" },
  { valor: "baja", etiqueta: "Baja" },
  { valor: "media", etiqueta: "Media" },
  { valor: "alta", etiqueta: "Alta" },
  { valor: "critica", etiqueta: "Critica" },
];

interface Props {
  estado?: string;
  prioridad?: string;
  q?: string;
}

export function FiltrosTickets({ estado, prioridad, q }: Props) {
  const conservar = new URLSearchParams();
  if (prioridad) conservar.set("prioridad", prioridad);
  if (q) conservar.set("q", q);

  const hrefEstado = (valor: string) => {
    const params = new URLSearchParams(conservar);
    if (valor) params.set("estado", valor);
    const query = params.toString();
    return query ? `/?${query}` : "/";
  };

  return (
    <div className="mb-3 flex flex-wrap items-center gap-3">
      <div className="flex gap-0.5 rounded-lg bg-slate-200/70 p-1">
        {ESTADOS.map((opcion) => {
          const activo = (estado ?? "") === opcion.valor;
          return (
            <Link
              key={opcion.valor}
              href={hrefEstado(opcion.valor)}
              className={`rounded-md px-2.5 py-1 text-[13px] transition ${
                activo
                  ? "bg-white font-medium text-ink shadow-sm"
                  : "text-muted hover:text-ink"
              }`}
            >
              {opcion.etiqueta}
            </Link>
          );
        })}
      </div>

      <form method="get" className="ml-auto flex flex-wrap items-center gap-2">
        {estado ? <input type="hidden" name="estado" value={estado} /> : null}
        <select
          name="prioridad"
          defaultValue={prioridad ?? ""}
          className="input"
          aria-label="Filtrar por prioridad"
        >
          {PRIORIDADES.map((opcion) => (
            <option key={opcion.valor} value={opcion.valor}>
              {opcion.etiqueta}
            </option>
          ))}
        </select>
        <input
          name="q"
          defaultValue={q ?? ""}
          placeholder="Buscar por titulo o ID"
          className="input w-[210px]"
          aria-label="Buscar tickets"
        />
        <button type="submit" className="btn">
          Aplicar
        </button>
      </form>
    </div>
  );
}
