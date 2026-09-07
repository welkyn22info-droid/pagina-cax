"use client";

import { useRef, useState } from "react";
import { api, ErrorApi } from "@/lib/api";
import { formatearFecha } from "@/lib/fechas";

interface ResultadoFecha {
  fecha_datos: string;
  carga_id: number | null;
  estado: string;
  duplicado: boolean;
  filas_validas: number;
  mensaje: string;
}

export default function CargarCurvasHistorico({ onCompletado }: { onCompletado?: () => void }) {
  const [subiendo, setSubiendo] = useState(false);
  const [resultados, setResultados] = useState<ResultadoFecha[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function subir(archivo: File) {
    setSubiendo(true);
    setError(null);
    setResultados(null);
    const form = new FormData();
    form.append("archivo", archivo);
    try {
      const r = await api<{ archivo: string; fechas_procesadas: number; resultados: ResultadoFecha[] }>(
        "/cargas/curvas-multiples",
        { metodo: "POST", formData: form }
      );
      setResultados(r.resultados);
      onCompletado?.();
    } catch (err) {
      setError(err instanceof ErrorApi ? err.message : "No se pudo procesar el archivo.");
    } finally {
      setSubiendo(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="border border-[var(--rule)] rounded-lg p-4 bg-white">
      <p className="text-sm font-medium mb-1">Cargar histórico de curvas</p>
      <p className="text-xs text-[var(--ink-soft)] mb-3">
        Para un archivo con varias fechas a la vez (una columna por día, como llega de la fuente) — se crea una carga
        separada por cada fecha, automáticamente. No hace falta elegir fecha aquí.
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.csv,.xlsx"
        disabled={subiendo}
        onChange={(e) => e.target.files?.[0] && subir(e.target.files[0])}
        className="text-xs"
      />
      {subiendo && <p className="text-xs text-[var(--ink-soft)] mt-2">Procesando — puede tardar unos segundos por cada fecha…</p>}
      {error && <p className="text-xs text-[var(--danger)] mt-2">{error}</p>}
      {resultados && (
        <div className="mt-3 border border-[var(--rule-soft)] rounded-md divide-y divide-[var(--rule-soft)] max-h-64 overflow-y-auto">
          {resultados.map((r) => (
            <div key={r.fecha_datos} className="px-3 py-1.5 text-xs flex items-center justify-between gap-2">
              <span>{formatearFecha(r.fecha_datos)}</span>
              <span className={r.estado === "VALIDADO" ? "text-[var(--teal)]" : r.estado === "RECHAZADO" ? "text-[var(--danger)]" : "text-[var(--ink-soft)]"}>
                {r.duplicado ? "Ya existía" : r.estado === "VALIDADO" ? `${r.filas_validas} filas` : r.mensaje}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
