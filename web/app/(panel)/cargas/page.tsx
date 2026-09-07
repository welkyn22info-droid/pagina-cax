"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ErrorApi, Carga } from "@/lib/api";
import { formatearFecha, formatearFechaHora, ultimoDiaHabil } from "@/lib/fechas";
import SelectorFecha from "@/componentes/SelectorFecha";
import SubidorArchivos from "@/componentes/SubidorArchivos";
import CargarCurvasHistorico from "@/componentes/CargarCurvasHistorico";
import { useUsuario } from "@/lib/hooks";
import { puede } from "@/lib/sesion";

const ETIQUETAS_TIPO: Record<string, string> = {
  posiciones: "Posiciones",
  precios: "Precios",
  flujos_pasivo: "Flujos de pasivo",
  curvas: "Curvas de mercado",
};

const MODULO_POR_TIPO: Record<string, string> = {
  posiciones: "valoracion",
  precios: "valoracion",
  flujos_pasivo: "pasivo",
  curvas: "curvas",
};

const ETIQUETAS_ESTADO: Record<string, string> = {
  VALIDADO: "Cargado",
  RECHAZADO: "Rechazado",
  RECIBIDO: "Recibido",
};

export default function PaginaCargas() {
  const [fecha, setFecha] = useState(ultimoDiaHabil());
  const [anulando, setAnulando] = useState<number | null>(null);
  const [motivoAnulacion, setMotivoAnulacion] = useState("");
  const [errorAnulacion, setErrorAnulacion] = useState<string | null>(null);
  const cliente = useQueryClient();
  const { data: usuario } = useUsuario();

  const { data: faltantes, refetch: refetchFaltantes } = useQuery<{ faltantes: Record<string, string[]> }>({
    queryKey: ["cargas", "faltantes", fecha],
    queryFn: () => api("/cargas/faltantes", { query: { fecha } }),
  });

  const { data: cargas, refetch: refetchCargas } = useQuery<Carga[]>({
    queryKey: ["cargas", fecha],
    queryFn: () => api<Carga[]>("/cargas", { query: { fecha } }),
  });

  const insumosEsperados = ["posiciones", "precios", "flujos_pasivo"];
  const cargadosPorTipo = new Set((cargas || []).filter((c) => c.estado === "VALIDADO" && !c.anulada_en).map((c) => c.tipo_insumo));

  function alTerminar() {
    refetchCargas();
    refetchFaltantes();
    cliente.invalidateQueries({ queryKey: ["procesos"] });
    cliente.invalidateQueries({ queryKey: ["curvas"] });
  }

  async function confirmarAnulacion(cargaId: number) {
    if (!motivoAnulacion.trim()) return;
    setErrorAnulacion(null);
    try {
      await api(`/cargas/${cargaId}/anular`, { metodo: "POST", cuerpo: { motivo: motivoAnulacion } });
      setAnulando(null);
      setMotivoAnulacion("");
      alTerminar();
    } catch (err) {
      setErrorAnulacion(err instanceof ErrorApi ? err.message : "No se pudo anular la carga.");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Cargas</h1>
        <SelectorFecha valor={fecha} onCambiar={setFecha} />
      </div>

      <h2 className="text-sm font-semibold text-[var(--ink-soft)] mb-3">Insumos esperados para el {formatearFecha(fecha)}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
        {insumosEsperados.map((tipo) => {
          const cargado = cargadosPorTipo.has(tipo);
          const cargaRechazada = (cargas || []).find((c) => c.tipo_insumo === tipo && c.estado === "RECHAZADO" && !cargado);
          return (
            <div key={tipo} className="bg-white border border-[var(--rule)] rounded-lg p-4">
              <p className="text-sm font-medium mb-1">{ETIQUETAS_TIPO[tipo]}</p>
              {cargado ? (
                <span className="text-xs text-[var(--teal)]">Cargado</span>
              ) : cargaRechazada ? (
                <span className="text-xs text-[var(--danger)]">Rechazado — vuelva a cargar</span>
              ) : (
                <span className="text-xs text-[var(--ink-soft)]">Faltante</span>
              )}
            </div>
          );
        })}
      </div>

      <h2 className="text-sm font-semibold text-[var(--ink-soft)] mb-3">Subir archivos</h2>
      <SubidorArchivos fecha={fecha} onCompletado={alTerminar} />

      <div className="mt-6">
        <CargarCurvasHistorico onCompletado={alTerminar} />
      </div>

      <h2 className="text-sm font-semibold text-[var(--ink-soft)] mt-8 mb-3">Historial de cargas — {formatearFecha(fecha)}</h2>
      <div className="bg-white border border-[var(--rule)] rounded-lg divide-y divide-[var(--rule-soft)]">
        {(cargas || []).length === 0 && (
          <div className="px-4 py-6 text-sm text-[var(--ink-soft)] text-center">Sin cargas registradas para esta fecha.</div>
        )}
        {(cargas || []).map((c) => (
          <div key={c.id} className="px-4 py-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className={`font-medium ${c.anulada_en ? "line-through text-[var(--ink-soft)]" : ""}`}>{c.nombre_archivo}</p>
                <p className="text-xs text-[var(--ink-soft)]">
                  {ETIQUETAS_TIPO[c.tipo_insumo] || c.tipo_insumo} · {formatearFechaHora(c.cargado_en)} · {c.filas_validas ?? 0} filas
                </p>
                {c.anulada_en && (
                  <p className="text-xs text-[var(--danger)] mt-0.5">
                    Anulada el {formatearFechaHora(c.anulada_en)} — {c.motivo_anulacion}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {c.estado === "VALIDADO" && !c.anulada_en && puede(usuario, MODULO_POR_TIPO[c.tipo_insumo] || c.tipo_insumo, "puede_cargar") && (
                  <button
                    onClick={() => {
                      setAnulando(anulando === c.id ? null : c.id);
                      setMotivoAnulacion("");
                      setErrorAnulacion(null);
                    }}
                    className="text-xs text-[var(--danger)] hover:underline"
                  >
                    Anular
                  </button>
                )}
                <span className={`text-xs font-medium ${c.estado === "VALIDADO" ? "text-[var(--teal)]" : c.estado === "RECHAZADO" ? "text-[var(--danger)]" : "text-[var(--ink-soft)]"}`}>
                  {ETIQUETAS_ESTADO[c.estado] || c.estado}
                </span>
              </div>
            </div>
            {anulando === c.id && (
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="text"
                  value={motivoAnulacion}
                  onChange={(e) => setMotivoAnulacion(e.target.value)}
                  placeholder="Motivo de la anulación"
                  className="flex-1 border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-xs"
                />
                <button
                  onClick={() => confirmarAnulacion(c.id)}
                  disabled={!motivoAnulacion.trim()}
                  className="text-xs bg-[var(--danger)] text-white rounded-md px-3 py-1.5 disabled:opacity-50"
                >
                  Confirmar
                </button>
              </div>
            )}
            {anulando === c.id && errorAnulacion && <p className="text-xs text-[var(--danger)] mt-1">{errorAnulacion}</p>}
          </div>
        ))}
      </div>

      {faltantes && Object.values(faltantes.faltantes).some((f) => f.length > 0) && (
        <p className="mt-4 text-xs text-[var(--ink-soft)]">
          Nota: los procesos que dependen de un insumo faltante no podrán ejecutarse hasta que se cargue.
        </p>
      )}
    </div>
  );
}
