"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import type { SerieCurva } from "@/lib/api";
import { formatearFecha } from "@/lib/fechas";

const COLORES = ["var(--teal)", "var(--amber)", "var(--danger)", "#6366f1", "#8b5cf6", "#ec4899", "#0ea5e9", "#84cc16"];

export default function PaginaCurvas() {
  const [tipoCurva, setTipoCurva] = useState<string>("");
  const [fechasSeleccionadas, setFechasSeleccionadas] = useState<string[]>([]);

  const { data: tipos } = useQuery<string[]>({
    queryKey: ["curvas", "tipos"],
    queryFn: () => api<string[]>("/curvas/tipos"),
  });

  useEffect(() => {
    if (!tipoCurva && tipos && tipos.length > 0) setTipoCurva(tipos[0]);
  }, [tipos, tipoCurva]);

  const { data: fechasDisponibles } = useQuery<string[]>({
    queryKey: ["curvas", "fechas", tipoCurva],
    queryFn: () => api<string[]>("/curvas/fechas", { query: { tipo_curva: tipoCurva } }),
    enabled: Boolean(tipoCurva),
  });

  // Por defecto, el último día cargado — comparar más fechas es una elección explícita.
  useEffect(() => {
    if (fechasDisponibles && fechasDisponibles.length > 0 && fechasSeleccionadas.length === 0) {
      setFechasSeleccionadas([fechasDisponibles[0]]);
    }
  }, [fechasDisponibles, fechasSeleccionadas.length]);

  const { data } = useQuery<{ series: SerieCurva[] }>({
    queryKey: ["curvas", "datos", tipoCurva, fechasSeleccionadas],
    queryFn: () => api("/curvas", { query: { tipo_curva: tipoCurva, fechas: fechasSeleccionadas.join(",") } }),
    enabled: Boolean(tipoCurva) && fechasSeleccionadas.length > 0,
  });

  const series = data?.series || [];

  // Recharts necesita una fila por punto del eje X con una columna por
  // serie — se pivotea aquí (las series llegan una lista de puntos por
  // fecha, como tiene sentido guardarlas: no se sabe de antemano cuántas
  // fechas se van a comparar).
  const nodosSet = new Set<number>();
  series.forEach((s) => s.puntos.forEach((p) => nodosSet.add(p.nodo)));
  const nodosOrdenados = Array.from(nodosSet).sort((a, b) => a - b);
  const valoresPorNodo: Record<number, Record<string, number>> = {};
  series.forEach((s) => {
    s.puntos.forEach((p) => {
      (valoresPorNodo[p.nodo] ??= {})[s.fecha_datos] = p.valor;
    });
  });
  const datosGrafica = nodosOrdenados.map((nodo) => ({ nodo, ...valoresPorNodo[nodo] }));

  function alternarFecha(fecha: string) {
    setFechasSeleccionadas((actual) => (actual.includes(fecha) ? actual.filter((f) => f !== fecha) : [...actual, fecha]));
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-lg font-semibold">Curvas de mercado</h1>
        {tipos && tipos.length > 0 && (
          <select
            value={tipoCurva}
            onChange={(e) => {
              setTipoCurva(e.target.value);
              setFechasSeleccionadas([]);
            }}
            aria-label="Tipo de curva"
            className="border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm"
          >
            {tipos.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        )}
      </div>

      {(!tipos || tipos.length === 0) && (
        <p className="text-sm text-[var(--ink-soft)]">Todavía no hay curvas cargadas. Suba un archivo desde Cargas.</p>
      )}

      {tipoCurva && (
        <>
          <div className="mb-4">
            <p className="text-xs font-medium text-[var(--ink-soft)] mb-2">
              Fechas a comparar {fechasSeleccionadas.length === 0 && "(seleccione al menos una)"}
            </p>
            <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
              {(fechasDisponibles || []).map((f) => (
                <button
                  key={f}
                  onClick={() => alternarFecha(f)}
                  className={`text-xs rounded-full px-3 py-1 border transition-colors ${
                    fechasSeleccionadas.includes(f)
                      ? "bg-[var(--teal)] text-white border-[var(--teal)]"
                      : "border-[var(--rule)] text-[var(--ink-soft)] hover:bg-gray-50"
                  }`}
                >
                  {formatearFecha(f)}
                </button>
              ))}
              {(fechasDisponibles || []).length === 0 && (
                <span className="text-xs text-[var(--ink-soft)]">Sin fechas cargadas para esta curva.</span>
              )}
            </div>
          </div>

          <div className="bg-white border border-[var(--rule)] rounded-lg p-5" style={{ height: 440 }}>
            {datosGrafica.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-[var(--ink-soft)]">
                Seleccione al menos una fecha para ver la curva.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={datosGrafica} margin={{ bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--rule-soft)" />
                  <XAxis
                    dataKey="nodo"
                    tick={{ fontSize: 12 }}
                    label={{ value: "Plazo (días)", position: "insideBottom", offset: -8, fontSize: 12 }}
                  />
                  <YAxis tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
                  <Tooltip labelFormatter={(v) => `Nodo ${v} días`} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {series.map((s, idx) => (
                    <Line
                      key={s.fecha_datos}
                      type="monotone"
                      dataKey={s.fecha_datos}
                      name={formatearFecha(s.fecha_datos)}
                      stroke={COLORES[idx % COLORES.length]}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </>
      )}
    </div>
  );
}
