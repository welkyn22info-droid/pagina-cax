"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ProcesoCatalogo } from "@/lib/api";
import { formatearFechaHora, ultimoDiaHabil } from "@/lib/fechas";
import SelectorFecha from "@/componentes/SelectorFecha";
import EstadoCorrida from "@/componentes/EstadoCorrida";

const ETIQUETAS_INSUMO: Record<string, string> = {
  posiciones: "posiciones",
  precios: "precios",
  flujos_pasivo: "flujos de pasivo",
};

export default function PaginaProcesos() {
  const [fecha, setFecha] = useState(ultimoDiaHabil());

  const { data: procesos } = useQuery<ProcesoCatalogo[]>({
    queryKey: ["procesos", fecha],
    queryFn: () => api<ProcesoCatalogo[]>("/procesos", { query: { fecha } }),
    refetchInterval: 3000,
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Procesos</h1>
        <SelectorFecha valor={fecha} onCambiar={setFecha} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {(procesos || []).map((p) => {
          const corridaVigente = p.ultima_corrida?.fecha_datos === fecha ? p.ultima_corrida : null;
          return (
            <Link key={p.proceso} href={`/procesos/${p.proceso}`} className="bg-white border border-[var(--rule)] rounded-lg p-5 hover:border-[var(--teal)]">
              <div className="flex items-center justify-between mb-2">
                <p className="font-medium text-sm">{p.nombre}</p>
                <EstadoCorrida estado={corridaVigente?.estado || "PENDIENTE"} />
              </div>
              <p className="text-xs text-[var(--ink-soft)] mb-1">
                Insumos: {p.requisitos.map((r) => (r.tipo_insumo ? ETIQUETAS_INSUMO[r.tipo_insumo] || r.tipo_insumo : `resultado de ${r.proceso_previo}`)).join(", ")}
              </p>
              {corridaVigente && (
                <p className="text-xs text-[var(--ink-soft)]">
                  Última corrida: {formatearFechaHora(corridaVigente.iniciada_en)}
                  {corridaVigente.duracion_ms ? ` · ${(corridaVigente.duracion_ms / 1000).toFixed(1)}s` : ""}
                </p>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
