import Link from "next/link";

interface Props {
  pagina: number;
  paginas: number;
  total: number;
  desde: number;
  hasta: number;
  params: Record<string, string | undefined>;
}

export function Paginacion({ pagina, paginas, total, desde, hasta, params }: Props) {
  const href = (destino: number) => {
    const query = new URLSearchParams();
    for (const [clave, valor] of Object.entries(params)) {
      if (valor) query.set(clave, valor);
    }
    query.set("pagina", String(destino));
    return `/?${query.toString()}`;
  };

  const numeros = Array.from({ length: paginas }, (_, indice) => indice + 1).filter(
    (numero) =>
      numero === 1 ||
      numero === paginas ||
      Math.abs(numero - pagina) <= 1,
  );

  return (
    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
      <span>
        Mostrando {total === 0 ? 0 : desde} a {hasta} de {total} tickets
      </span>
      <div className="flex items-center gap-1">
        {pagina > 1 ? (
          <Link href={href(pagina - 1)} className="btn px-2.5 py-1 text-xs">
            Anterior
          </Link>
        ) : (
          <span className="btn cursor-not-allowed px-2.5 py-1 text-xs opacity-50">Anterior</span>
        )}

        {numeros.map((numero, indice) => {
          const anterior = numeros[indice - 1];
          const hueco = anterior && numero - anterior > 1;
          return (
            <span key={numero} className="flex items-center gap-1">
              {hueco ? <span className="px-1">...</span> : null}
              <Link
                href={href(numero)}
                className={`grid size-7 place-items-center rounded-md border text-xs ${
                  numero === pagina
                    ? "border-slate-900 bg-slate-900 font-medium text-white"
                    : "border-line bg-surface text-ink-soft hover:bg-slate-50"
                }`}
              >
                {numero}
              </Link>
            </span>
          );
        })}

        {pagina < paginas ? (
          <Link href={href(pagina + 1)} className="btn px-2.5 py-1 text-xs">
            Siguiente
          </Link>
        ) : (
          <span className="btn cursor-not-allowed px-2.5 py-1 text-xs opacity-50">
            Siguiente
          </span>
        )}
      </div>
    </div>
  );
}
