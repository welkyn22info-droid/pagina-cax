"use client";

import { useMemo, useState } from "react";

export interface Columna<T> {
  clave: keyof T & string;
  titulo: string;
  formatear?: (fila: T) => React.ReactNode;
  numerica?: boolean;
}

export default function TablaResultados<T extends object>({
  columnas,
  filas,
  claveFila,
  ordenInicial,
  busquedaPor,
}: {
  columnas: Columna<T>[];
  filas: T[];
  claveFila: (fila: T) => string | number;
  ordenInicial?: { clave: keyof T & string; descendente?: boolean };
  busquedaPor?: (keyof T & string)[];
}) {
  const [busqueda, setBusqueda] = useState("");
  const [orden, setOrden] = useState(ordenInicial || null);

  const filtradas = useMemo(() => {
    if (!busqueda.trim() || !busquedaPor) return filas;
    const q = busqueda.toLowerCase();
    return filas.filter((f) => busquedaPor.some((c) => String(f[c] ?? "").toLowerCase().includes(q)));
  }, [filas, busqueda, busquedaPor]);

  const ordenadas = useMemo(() => {
    if (!orden) return filtradas;
    const copia = [...filtradas];
    copia.sort((a, b) => {
      const va = a[orden.clave];
      const vb = b[orden.clave];
      let cmp = 0;
      if (typeof va === "number" && typeof vb === "number") cmp = va - vb;
      else cmp = String(va ?? "").localeCompare(String(vb ?? ""));
      return orden.descendente ? -cmp : cmp;
    });
    return copia;
  }, [filtradas, orden]);

  function alternarOrden(clave: keyof T & string) {
    setOrden((actual) =>
      actual?.clave === clave ? { clave, descendente: !actual.descendente } : { clave, descendente: false }
    );
  }

  if (filas.length === 0) {
    return <div className="text-sm text-[var(--ink-soft)] py-8 text-center">No hay filas para mostrar.</div>;
  }

  return (
    <div>
      {busquedaPor && (
        <input
          type="text"
          placeholder="Buscar…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="mb-3 w-full max-w-xs border border-[var(--rule)] rounded-md px-3 py-1.5 text-sm"
        />
      )}
      <div className="overflow-x-auto border border-[var(--rule-soft)] rounded-md">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--rule)] bg-gray-50">
              {columnas.map((c) => (
                <th
                  key={c.clave}
                  onClick={() => alternarOrden(c.clave)}
                  className={`px-3 py-2 font-medium text-[var(--ink-soft)] cursor-pointer select-none whitespace-nowrap ${c.numerica ? "text-right" : "text-left"}`}
                >
                  {c.titulo}
                  {orden?.clave === c.clave && (orden.descendente ? " ↓" : " ↑")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ordenadas.map((fila) => (
              <tr key={claveFila(fila)} className="border-b border-[var(--rule-soft)] last:border-0 hover:bg-gray-50">
                {columnas.map((c) => (
                  <td key={c.clave} className={`px-3 py-2 whitespace-nowrap ${c.numerica ? "text-right cifra" : "text-left"}`}>
                    {c.formatear ? c.formatear(fila) : String(fila[c.clave] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-[var(--ink-soft)]">{ordenadas.length} de {filas.length} filas</p>
    </div>
  );
}
