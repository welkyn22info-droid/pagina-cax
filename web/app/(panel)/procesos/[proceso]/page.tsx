"use client";

import { use, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ErrorApi } from "@/lib/api";
import type { Corrida, ProcesoCatalogo } from "@/lib/api";
import { formatearFechaHora, ultimoDiaHabil } from "@/lib/fechas";
import SelectorFecha from "@/componentes/SelectorFecha";
import EstadoCorrida from "@/componentes/EstadoCorrida";

interface CorridaDetalle extends Corrida {
  log_ejecucion: string | null;
  traza_error: string | null;
  insumos: { carga_id: number | null; tipo_insumo: string | null; nombre_archivo: string | null; corrida_origen: number | null; proceso_origen: string | null }[];
}

const ETIQUETAS_FALTANTE: Record<string, string> = {
  "insumo:posiciones": "faltan posiciones",
  "insumo:precios": "faltan precios",
  "insumo:flujos_pasivo": "faltan flujos de pasivo",
};

function etiquetaFaltante(clave: string): string {
  if (ETIQUETAS_FALTANTE[clave]) return ETIQUETAS_FALTANTE[clave];
  if (clave.startsWith("proceso:")) return `falta ejecutar ${clave.replace("proceso:", "")}`;
  return clave;
}

export default function PaginaDetalleProceso({ params }: { params: Promise<{ proceso: string }> }) {
  const { proceso } = use(params);
  const [fecha, setFecha] = useState(ultimoDiaHabil());
  const [corridaSeleccionada, setCorridaSeleccionada] = useState<number | null>(null);
  const [errorEjecucion, setErrorEjecucion] = useState<string | null>(null);
  const cliente = useQueryClient();

  const { data: catalogo } = useQuery<ProcesoCatalogo[]>({
    queryKey: ["procesos", fecha],
    queryFn: () => api<ProcesoCatalogo[]>("/procesos", { query: { fecha } }),
  });
  const definicion = catalogo?.find((p) => p.proceso === proceso);

  const { data: faltantes } = useQuery<{ faltantes: Record<string, string[]> }>({
    queryKey: ["cargas", "faltantes", fecha],
    queryFn: () => api("/cargas/faltantes", { query: { fecha } }),
  });
  const faltanEsteProceso = faltantes?.faltantes[proceso] || [];

  const { data: historico } = useQuery<Corrida[]>({
    queryKey: ["corridas", proceso, fecha],
    queryFn: () => api<Corrida[]>("/corridas", { query: { proceso, fecha } }),
    refetchInterval: 2000,
  });

  const idCorridaVisible = corridaSeleccionada ?? historico?.[0]?.id ?? null;
  const enEjecucion = historico?.some((c) => c.estado === "EJECUTANDO");

  const { data: detalle } = useQuery<CorridaDetalle>({
    queryKey: ["corrida", idCorridaVisible],
    queryFn: () => api<CorridaDetalle>(`/corridas/${idCorridaVisible}`),
    enabled: idCorridaVisible !== null,
    refetchInterval: enEjecucion ? 2000 : false,
  });

  async function ejecutar() {
    setErrorEjecucion(null);
    try {
      const r = await api<{ corrida_id: number }>("/corridas", {
        metodo: "POST",
        cuerpo: { proceso, fecha_datos: fecha, parametros: {} },
      });
      setCorridaSeleccionada(r.corrida_id);
      cliente.invalidateQueries({ queryKey: ["corridas", proceso, fecha] });
      cliente.invalidateQueries({ queryKey: ["procesos"] });
    } catch (err) {
      setErrorEjecucion(err instanceof ErrorApi ? err.message : "No se pudo iniciar la ejecución.");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">{definicion?.nombre || proceso}</h1>
        <SelectorFecha valor={fecha} onCambiar={setFecha} />
      </div>

      <div className="bg-white border border-[var(--rule)] rounded-lg p-5 mb-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <button
              onClick={ejecutar}
              disabled={faltanEsteProceso.length > 0 || enEjecucion}
              className="bg-[var(--teal)] text-white text-sm font-medium rounded-md px-4 py-2 disabled:opacity-50"
            >
              {enEjecucion ? "Ejecutando…" : "Ejecutar"}
            </button>
            {faltanEsteProceso.length > 0 && (
              <p className="text-xs text-[var(--danger)] mt-2">
                No se puede ejecutar: {faltanEsteProceso.map(etiquetaFaltante).join(", ")}.
              </p>
            )}
            {errorEjecucion && <p className="text-xs text-[var(--danger)] mt-2">{errorEjecucion}</p>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        <div>
          <h2 className="text-sm font-semibold text-[var(--ink-soft)] mb-3">Histórico</h2>
          <div className="bg-white border border-[var(--rule)] rounded-lg divide-y divide-[var(--rule-soft)] max-h-[32rem] overflow-y-auto">
            {(historico || []).length === 0 && (
              <div className="px-4 py-6 text-sm text-[var(--ink-soft)] text-center">Sin corridas para esta fecha.</div>
            )}
            {(historico || []).map((c) => (
              <button
                key={c.id}
                onClick={() => setCorridaSeleccionada(c.id)}
                className={`w-full text-left px-4 py-3 text-sm ${idCorridaVisible === c.id ? "bg-[var(--teal-pale)]" : "hover:bg-gray-50"}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--ink-soft)]">{formatearFechaHora(c.iniciada_en)}</span>
                  <EstadoCorrida estado={c.estado} />
                </div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold text-[var(--ink-soft)] mb-3">Detalle de la corrida</h2>
          {!detalle ? (
            <p className="text-sm text-[var(--ink-soft)]">Seleccione una corrida del histórico.</p>
          ) : (
            <div className="bg-white border border-[var(--rule)] rounded-lg p-5 space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <div>
                  <p className="text-xs text-[var(--ink-soft)]">Estado</p>
                  <EstadoCorrida estado={detalle.estado} />
                </div>
                <div>
                  <p className="text-xs text-[var(--ink-soft)]">Duración</p>
                  <p className="cifra">{detalle.duracion_ms ? `${(detalle.duracion_ms / 1000).toFixed(1)}s` : "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-[var(--ink-soft)]">Filas producidas</p>
                  <p className="cifra">{detalle.filas_resultado ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-[var(--ink-soft)]">Iniciada</p>
                  <p>{formatearFechaHora(detalle.iniciada_en)}</p>
                </div>
              </div>

              {detalle.mensaje_error && (
                <div className="bg-[var(--danger-pale)] text-[var(--danger)] text-sm rounded-md px-3 py-2">
                  {detalle.mensaje_error}
                </div>
              )}

              <div>
                <p className="text-xs font-medium text-[var(--ink-soft)] mb-1">Insumos consumidos</p>
                <ul className="text-sm space-y-1">
                  {detalle.insumos.map((i, idx) => (
                    <li key={idx} className="text-[var(--ink-soft)]">
                      {i.nombre_archivo ? `${i.tipo_insumo}: ${i.nombre_archivo}` : `corrida #${i.corrida_origen} de ${i.proceso_origen}`}
                    </li>
                  ))}
                  {detalle.insumos.length === 0 && <li className="text-[var(--ink-soft)]">Sin insumos registrados.</li>}
                </ul>
              </div>

              {detalle.log_ejecucion && (
                <div>
                  <p className="text-xs font-medium text-[var(--ink-soft)] mb-1">Registro de ejecución</p>
                  <pre className="bg-[var(--ink)] text-gray-200 text-xs rounded-md p-3 overflow-x-auto whitespace-pre-wrap">{detalle.log_ejecucion}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
