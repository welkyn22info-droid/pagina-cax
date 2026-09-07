"use client";

import { useEffect, useRef, useState } from "react";
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
  const [archivo, setArchivo] = useState<File | null>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [subiendo, setSubiendo] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [resultados, setResultados] = useState<ResultadoFecha[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!subiendo) return;
    const inicio = Date.now();
    const intervalo = setInterval(() => setSegundos(Math.floor((Date.now() - inicio) / 1000)), 1000);
    return () => clearInterval(intervalo);
  }, [subiendo]);

  function elegirArchivo(lista: FileList | null) {
    if (!lista || lista.length === 0) return;
    setArchivo(lista[0]);
    setResultados(null);
    setError(null);
  }

  async function cargar() {
    if (!archivo) return;
    setSubiendo(true);
    setSegundos(0);
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
      setArchivo(null);
      onCompletado?.();
    } catch (err) {
      setError(err instanceof ErrorApi ? err.message : "No se pudo procesar el archivo.");
    } finally {
      setSubiendo(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  const exitosas = (resultados || []).filter((r) => r.estado === "VALIDADO" && !r.duplicado).length;
  const yaExistian = (resultados || []).filter((r) => r.duplicado).length;
  const rechazadas = (resultados || []).filter((r) => r.estado === "RECHAZADO").length;

  return (
    <div className="border border-[var(--rule)] rounded-lg p-4 bg-white">
      <p className="text-sm font-medium mb-1">Cargar histórico de curvas</p>
      <p className="text-xs text-[var(--ink-soft)] mb-3">
        Para un archivo con varias fechas a la vez (una columna por día, como llega de la fuente) — se crea una carga
        separada por cada fecha, automáticamente. No hace falta elegir fecha aquí.
      </p>

      {!subiendo && !resultados && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setArrastrando(true);
          }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArrastrando(false);
            elegirArchivo(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg py-6 text-center cursor-pointer transition-colors ${
            arrastrando ? "border-[var(--teal)] bg-[var(--teal-pale)]" : "border-[var(--rule)]"
          }`}
        >
          <p className="text-sm text-[var(--ink-soft)]">
            {archivo ? archivo.name : "Arrastre el archivo aquí, o haga clic para elegirlo"}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".txt,.csv,.xlsx"
            className="hidden"
            onChange={(e) => elegirArchivo(e.target.files)}
          />
        </div>
      )}

      {archivo && !subiendo && !resultados && (
        <div className="mt-3 flex items-center gap-2">
          <button onClick={cargar} className="bg-[var(--teal)] text-white text-sm font-medium rounded-md px-4 py-2">
            Cargar
          </button>
          <button onClick={() => setArchivo(null)} className="text-sm text-[var(--danger)]">
            Quitar
          </button>
          <span className="text-xs text-[var(--ink-soft)]">
            Estimado: ~3 segundos por cada fecha que traiga el archivo.
          </span>
        </div>
      )}

      {subiendo && (
        <div className="mt-3 flex items-center gap-2 text-sm text-[var(--ink-soft)]">
          <span className="h-3 w-3 rounded-full border-2 border-[var(--teal)] border-t-transparent animate-spin" />
          Cargando… {segundos}s transcurridos — no cierre esta página.
        </div>
      )}

      {error && <p className="text-xs text-[var(--danger)] mt-2">{error}</p>}

      {resultados && (
        <div className="mt-3">
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="text-sm rounded-md px-3 py-2 bg-[var(--teal-pale)] text-[var(--teal)]">
              {exitosas} fecha{exitosas === 1 ? "" : "s"} cargada{exitosas === 1 ? "" : "s"} correctamente
              {yaExistian > 0 && ` · ${yaExistian} ya existían`}
              {rechazadas > 0 && ` · ${rechazadas} rechazadas`}
            </div>
            <button onClick={() => setResultados(null)} className="text-xs text-[var(--ink-soft)] hover:underline">
              Cargar otro archivo
            </button>
          </div>
          <div className="border border-[var(--rule-soft)] rounded-md divide-y divide-[var(--rule-soft)] max-h-64 overflow-y-auto">
            {resultados.map((r) => (
              <div key={r.fecha_datos} className="px-3 py-1.5 text-xs flex items-center justify-between gap-2">
                <span>{formatearFecha(r.fecha_datos)}</span>
                <span
                  className={
                    r.estado === "VALIDADO"
                      ? "text-[var(--teal)]"
                      : r.estado === "RECHAZADO"
                        ? "text-[var(--danger)]"
                        : "text-[var(--ink-soft)]"
                  }
                >
                  {r.duplicado ? "Ya existía" : r.estado === "VALIDADO" ? `${r.filas_validas} filas` : r.mensaje}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
