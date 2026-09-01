"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import type { PuntoFundingRatio } from "@/lib/api";
import { formatearFecha, formatearNumero, formatearPorcentaje } from "@/lib/fechas";
import BotonesResultado from "@/componentes/BotonesResultado";
import { useUsuario } from "@/lib/hooks";
import { puede } from "@/lib/sesion";

export default function PaginaFundingRatio() {
  const hoy = new Date().toISOString().slice(0, 10);
  const [desde, setDesde] = useState("2000-01-01");
  const [hasta, setHasta] = useState(hoy);
  const { data: usuario } = useUsuario();

  const { data } = useQuery<{ serie: PuntoFundingRatio[] }>({
    queryKey: ["resultados", "funding-ratio", desde, hasta],
    queryFn: () => api("/resultados/funding-ratio", { query: { desde, hasta } }),
  });

  const serie = [...(data?.serie || [])].sort((a, b) => a.fecha_datos.localeCompare(b.fecha_datos));
  const ultimo = serie[serie.length - 1];
  const anterior = serie[serie.length - 2];
  const variacionDia = ultimo && anterior ? ultimo.ratio - anterior.ratio : null;

  const datosGrafica = serie.map((p) => ({ fecha: formatearFecha(p.fecha_datos), ratio: p.ratio * 100 }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-lg font-semibold">Funding ratio</h1>
        <div className="flex items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            <span className="text-[var(--ink-soft)]">Desde</span>
            <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="border border-[var(--rule)] rounded-md px-2 py-1 cifra" />
          </label>
          <label className="flex items-center gap-2">
            <span className="text-[var(--ink-soft)]">Hasta</span>
            <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="border border-[var(--rule)] rounded-md px-2 py-1 cifra" />
          </label>
        </div>
      </div>

      {!ultimo ? (
        <p className="text-sm text-[var(--ink-soft)]">Sin resultados de funding ratio en el rango seleccionado.</p>
      ) : (
        <>
          <div className="flex items-end justify-between mb-6 flex-wrap gap-4">
            <div className="flex gap-8">
              <div>
                <p className="text-xs text-[var(--ink-soft)] mb-1">Funding ratio — {formatearFecha(ultimo.fecha_datos)}</p>
                <p className="text-2xl font-semibold cifra">{formatearPorcentaje(ultimo.ratio, 1)}</p>
                {variacionDia !== null && (
                  <p className={`text-xs cifra ${variacionDia >= 0 ? "text-[var(--teal)]" : "text-[var(--danger)]"}`}>
                    {variacionDia >= 0 ? "▲" : "▼"} {formatearPorcentaje(Math.abs(variacionDia), 2)} vs. corrida anterior
                  </p>
                )}
              </div>
              <div>
                <p className="text-xs text-[var(--ink-soft)] mb-1">Superávit / déficit</p>
                <p className="text-lg font-semibold cifra">${formatearNumero(ultimo.superavit_deficit, 0)}</p>
              </div>
            </div>
            <BotonesResultado recurso="funding-ratio" fecha={ultimo.fecha_datos} corridaId={ultimo.corrida_id} puedePublicar={puede(usuario, "funding_ratio", "puede_publicar")} />
          </div>

          <div className="bg-white border border-[var(--rule)] rounded-lg p-5 mb-6" style={{ height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={datosGrafica}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--rule-soft)" />
                <XAxis dataKey="fecha" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
                <Tooltip formatter={(v: number) => [`${v.toFixed(2)}%`, "Funding ratio"]} />
                <Line type="monotone" dataKey="ratio" stroke="var(--teal)" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto border border-[var(--rule-soft)] rounded-md">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--rule)] bg-gray-50">
                  <th className="px-3 py-2 text-left font-medium text-[var(--ink-soft)]">Fecha</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--ink-soft)]">Activos</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--ink-soft)]">Pasivos</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--ink-soft)]">Ratio</th>
                  <th className="px-3 py-2 text-right font-medium text-[var(--ink-soft)]">Superávit/déficit</th>
                </tr>
              </thead>
              <tbody>
                {[...serie].reverse().map((p) => (
                  <tr key={p.corrida_id} className="border-b border-[var(--rule-soft)] last:border-0">
                    <td className="px-3 py-2">{formatearFecha(p.fecha_datos)}</td>
                    <td className="px-3 py-2 text-right cifra">${formatearNumero(p.valor_activos, 0)}</td>
                    <td className="px-3 py-2 text-right cifra">${formatearNumero(p.valor_pasivos, 0)}</td>
                    <td className="px-3 py-2 text-right cifra">{formatearPorcentaje(p.ratio, 1)}</td>
                    <td className="px-3 py-2 text-right cifra">${formatearNumero(p.superavit_deficit, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
