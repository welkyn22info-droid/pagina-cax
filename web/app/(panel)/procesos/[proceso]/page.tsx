"use client";

import { use, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ErrorApi } from "@/lib/api";
import type { Corrida, ProcesoCatalogo } from "@/lib/api";
import { formatearFechaHora, ultimoDiaHabil } from "@/lib/fechas";
import SelectorFecha from "@/componentes/SelectorFecha";
import EstadoCorrida from "@/componentes/EstadoCorrida";
import { useUsuario } from "@/lib/hooks";
import { puede } from "@/lib/sesion";

interface CorridaDetalle extends Corrida {
  log_ejecucion: string | null;
  traza_error: string | null;
  insumos: { carga_id: number | null; tipo_insumo: string | null; nombre_archivo: string | null; corrida_origen: number | null; proceso_origen: string | null }[];
  resultado_borrador: Record<string, unknown>[] | null;
  confirmada_por: number | null;
  confirmada_en: string | null;
}

function VistaPreviaBorrador({ filas }: { filas: Record<string, unknown>[] }) {
  if (filas.length === 0) {
    return <p className="text-sm text-[var(--ink-soft)]">El cálculo no produjo filas.</p>;
  }
  const columnas = Object.keys(filas[0]).filter((c) => c !== "corrida_id" && c !== "fecha_datos");
  return (
    <div className="overflow-x-auto border border-[var(--rule-soft)] rounded-md max-h-80">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-gray-50">
          <tr className="border-b border-[var(--rule)]">
            {columnas.map((c) => (
              <th key={c} className="px-3 py-2 text-left font-medium text-[var(--ink-soft)] whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila, idx) => (
            <tr key={idx} className="border-b border-[var(--rule-soft)] last:border-0">
              {columnas.map((c) => (
                <td key={c} className="px-3 py-2 whitespace-nowrap cifra">{String(fila[c] ?? "—")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
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
  const [confirmando, setConfirmando] = useState(false);
  const [mostrarDescarte, setMostrarDescarte] = useState(false);
  const [motivoDescarte, setMotivoDescarte] = useState("");
  const [errorConfirmacion, setErrorConfirmacion] = useState<string | null>(null);
  const cliente = useQueryClient();
  const { data: usuario } = useUsuario();

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
  const pendienteDeConfirmar = historico?.some((c) => c.estado === "PENDIENTE_CONFIRMACION");

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

  function invalidarTrasCambioDeEstado() {
    cliente.invalidateQueries({ queryKey: ["corridas", proceso, fecha] });
    cliente.invalidateQueries({ queryKey: ["corrida", idCorridaVisible] });
    cliente.invalidateQueries({ queryKey: ["procesos"] });
    cliente.invalidateQueries({ queryKey: ["resultados"] });
  }

  async function confirmar() {
    if (idCorridaVisible === null) return;
    setErrorConfirmacion(null);
    setConfirmando(true);
    try {
      await api(`/corridas/${idCorridaVisible}/confirmar`, { metodo: "POST" });
      invalidarTrasCambioDeEstado();
    } catch (err) {
      setErrorConfirmacion(err instanceof ErrorApi ? err.message : "No se pudo confirmar el resultado.");
    } finally {
      setConfirmando(false);
    }
  }

  async function descartar() {
    if (idCorridaVisible === null || !motivoDescarte.trim()) return;
    setErrorConfirmacion(null);
    try {
      await api(`/corridas/${idCorridaVisible}/anular`, { metodo: "POST", cuerpo: { motivo: motivoDescarte } });
      setMostrarDescarte(false);
      setMotivoDescarte("");
      invalidarTrasCambioDeEstado();
    } catch (err) {
      setErrorConfirmacion(err instanceof ErrorApi ? err.message : "No se pudo descartar la corrida.");
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
              disabled={faltanEsteProceso.length > 0 || enEjecucion || pendienteDeConfirmar}
              className="bg-[var(--teal)] text-white text-sm font-medium rounded-md px-4 py-2 disabled:opacity-50"
            >
              {enEjecucion ? "Ejecutando…" : "Ejecutar"}
            </button>
            {faltanEsteProceso.length > 0 && (
              <p className="text-xs text-[var(--danger)] mt-2">
                No se puede ejecutar: {faltanEsteProceso.map(etiquetaFaltante).join(", ")}.
              </p>
            )}
            {pendienteDeConfirmar && faltanEsteProceso.length === 0 && (
              <p className="text-xs text-[var(--amber)] mt-2">
                Hay un resultado pendiente de confirmar o descartar más abajo.
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

              {detalle.estado === "PENDIENTE_CONFIRMACION" && (
                <div className="border border-[var(--amber)] bg-[var(--amber-pale)] rounded-lg p-4 space-y-3">
                  <p className="text-sm text-[var(--amber)] font-medium">
                    El cálculo terminó pero todavía no está en la base. Audite las filas antes de confirmar.
                  </p>
                  <VistaPreviaBorrador filas={detalle.resultado_borrador || []} />
                  {definicion && puede(usuario, definicion.modulo, "puede_publicar") && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={confirmar}
                          disabled={confirmando}
                          className="bg-[var(--teal)] text-white text-sm font-medium rounded-md px-4 py-2 disabled:opacity-50"
                        >
                          {confirmando ? "Confirmando…" : "Confirmar y cargar a la base"}
                        </button>
                        <button
                          onClick={() => setMostrarDescarte((v) => !v)}
                          className="text-sm border border-[var(--rule)] rounded-md px-4 py-2 hover:bg-white"
                        >
                          Descartar
                        </button>
                      </div>
                      {mostrarDescarte && (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={motivoDescarte}
                            onChange={(e) => setMotivoDescarte(e.target.value)}
                            placeholder="Motivo del descarte"
                            className="flex-1 border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm"
                          />
                          <button
                            onClick={descartar}
                            disabled={!motivoDescarte.trim()}
                            className="text-sm bg-[var(--danger)] text-white rounded-md px-3 py-1.5 disabled:opacity-50"
                          >
                            Confirmar descarte
                          </button>
                        </div>
                      )}
                      {errorConfirmacion && <p className="text-xs text-[var(--danger)]">{errorConfirmacion}</p>}
                    </div>
                  )}
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
