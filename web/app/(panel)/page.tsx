"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FilaCupo, ProcesoCatalogo, Publicacion, PuntoFundingRatio } from "@/lib/api";
import { formatearFecha, formatearNumero, formatearPorcentaje, ultimoDiaHabil } from "@/lib/fechas";
import SelectorFecha from "@/componentes/SelectorFecha";
import EstadoCorrida from "@/componentes/EstadoCorrida";

export default function PaginaPanel() {
  const [fecha, setFecha] = useState(ultimoDiaHabil());

  const { data: procesos } = useQuery<ProcesoCatalogo[]>({
    queryKey: ["procesos", fecha],
    queryFn: () => api<ProcesoCatalogo[]>("/procesos", { query: { fecha } }),
  });

  const { data: fr } = useQuery<{ serie: PuntoFundingRatio[] }>({
    queryKey: ["resultados", "funding-ratio", "panel"],
    queryFn: () => api("/resultados/funding-ratio", { query: { desde: "2000-01-01", hasta: fecha } }),
  });

  const { data: cupos } = useQuery<{ filas: FilaCupo[] }>({
    queryKey: ["cupos", "consumo", fecha],
    queryFn: () => api("/cupos/consumo", { query: { fecha } }),
  });

  const { data: pendientes } = useQuery<Publicacion[]>({
    queryKey: ["publicaciones", "pendientes"],
    queryFn: () => api<Publicacion[]>("/publicaciones/pendientes"),
  });

  const serieOrdenada = [...(fr?.serie || [])].sort((a, b) => a.fecha_datos.localeCompare(b.fecha_datos));
  const ultimoFr = serieOrdenada[serieOrdenada.length - 1];
  const frAnterior = serieOrdenada[serieOrdenada.length - 2];
  const variacion = ultimoFr && frAnterior ? ultimoFr.ratio - frAnterior.ratio : null;

  const corridasError = (procesos || []).filter((p) => p.ultima_corrida?.estado === "ERROR" && p.ultima_corrida.fecha_datos === fecha);
  const cuposAlerta = (cupos?.filas || []).filter((c) => c.estado === "ALERTA" || c.estado === "EXCEDIDO");

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Panel</h1>
        <SelectorFecha valor={fecha} onCambiar={setFecha} />
      </div>

      {/* ¿Cuáles son los indicadores? */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white border border-[var(--rule)] rounded-lg p-5">
          <p className="text-xs text-[var(--ink-soft)] mb-1">Funding ratio</p>
          <p className="text-2xl font-semibold cifra">{ultimoFr ? formatearPorcentaje(ultimoFr.ratio, 1) : "—"}</p>
          {variacion !== null && (
            <p className={`text-xs mt-1 cifra ${variacion >= 0 ? "text-[var(--teal)]" : "text-[var(--danger)]"}`}>
              {variacion >= 0 ? "▲" : "▼"} {formatearPorcentaje(Math.abs(variacion), 2)} vs. corrida anterior
            </p>
          )}
        </div>
        <div className="bg-white border border-[var(--rule)] rounded-lg p-5">
          <p className="text-xs text-[var(--ink-soft)] mb-1">Activos / Pasivos</p>
          <p className="text-lg font-semibold cifra">{ultimoFr ? `$${formatearNumero(ultimoFr.valor_activos)}` : "—"}</p>
          <p className="text-xs text-[var(--ink-soft)] cifra">{ultimoFr ? `$${formatearNumero(ultimoFr.valor_pasivos)} en pasivos` : ""}</p>
        </div>
        <div className="bg-white border border-[var(--rule)] rounded-lg p-5">
          <p className="text-xs text-[var(--ink-soft)] mb-1">Cupos en alerta o excedidos</p>
          <p className="text-2xl font-semibold cifra">{cuposAlerta.length}</p>
        </div>
      </div>

      {/* ¿Está el día completo? */}
      <h2 className="text-sm font-semibold text-[var(--ink-soft)] mb-3">Estado del día — {formatearFecha(fecha)}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        {(procesos || []).map((p) => (
          <Link
            key={p.proceso}
            href={`/procesos/${p.proceso}`}
            className="bg-white border border-[var(--rule)] rounded-lg p-4 hover:border-[var(--teal)] transition-colors"
          >
            <p className="text-sm font-medium mb-2">{p.nombre}</p>
            {p.ultima_corrida && p.ultima_corrida.fecha_datos === fecha ? (
              <EstadoCorrida estado={p.ultima_corrida.estado} />
            ) : (
              <EstadoCorrida estado="PENDIENTE" />
            )}
          </Link>
        ))}
      </div>

      {/* ¿Hay algo que requiera mi atención? */}
      <h2 className="text-sm font-semibold text-[var(--ink-soft)] mb-3">Requiere atención</h2>
      <div className="bg-white border border-[var(--rule)] rounded-lg divide-y divide-[var(--rule-soft)]">
        {corridasError.map((p) => (
          <div key={p.proceso} className="px-4 py-3 text-sm flex items-center justify-between">
            <span>{p.nombre} terminó con error el {formatearFecha(p.ultima_corrida?.fecha_datos)}</span>
            <Link href={`/procesos/${p.proceso}`} className="text-[var(--teal)] text-xs">Ver detalle</Link>
          </div>
        ))}
        {cuposAlerta.map((c) => (
          <div key={`${c.tipo}-${c.entidad_id}`} className="px-4 py-3 text-sm flex items-center justify-between">
            <span>{c.entidad_nombre} — cupo {c.estado === "EXCEDIDO" ? "excedido" : "en alerta"}</span>
            <Link href="/controles/cupos" className="text-[var(--teal)] text-xs">Ver cupos</Link>
          </div>
        ))}
        {(pendientes || []).map((pub) => (
          <div key={pub.id} className="px-4 py-3 text-sm flex items-center justify-between">
            <span>Publicación pendiente de acuse: {pub.titulo}</span>
            <Link href={`/resultados/${pub.proceso === "funding_ratio" ? "funding-ratio" : pub.proceso}`} className="text-[var(--teal)] text-xs">Abrir</Link>
          </div>
        ))}
        {corridasError.length === 0 && cuposAlerta.length === 0 && (pendientes || []).length === 0 && (
          <div className="px-4 py-6 text-sm text-[var(--ink-soft)] text-center">Nada pendiente por ahora.</div>
        )}
      </div>
    </div>
  );
}
