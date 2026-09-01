"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FilaCupo } from "@/lib/api";
import { formatearNumero, formatearPorcentaje, ultimoDiaHabil } from "@/lib/fechas";
import SelectorFecha from "@/componentes/SelectorFecha";
import SemaforoCupo from "@/componentes/SemaforoCupo";
import BotonesResultado from "@/componentes/BotonesResultado";
import { useUsuario } from "@/lib/hooks";
import { puede } from "@/lib/sesion";

export default function PaginaCupos() {
  const [fecha, setFecha] = useState(ultimoDiaHabil());
  const [soloAlertas, setSoloAlertas] = useState(false);
  const [filaAbierta, setFilaAbierta] = useState<string | null>(null);
  const { data: usuario } = useUsuario();

  const { data } = useQuery<{ corrida_id: number | null; filas: FilaCupo[] }>({
    queryKey: ["cupos", "consumo", fecha],
    queryFn: () => api("/cupos/consumo", { query: { fecha } }),
  });

  const filas = useMemo(() => {
    let f = data?.filas || [];
    if (soloAlertas) f = f.filter((x) => x.estado === "ALERTA" || x.estado === "EXCEDIDO");
    // Orden por defecto: utilización descendente, para que lo crítico esté arriba.
    return [...f].sort((a, b) => (b.utilizacion ?? -1) - (a.utilizacion ?? -1));
  }, [data, soloAlertas]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-lg font-semibold">Cupos de emisor y contraparte</h1>
        <SelectorFecha valor={fecha} onCambiar={setFecha} />
      </div>

      {!data?.corrida_id ? (
        <p className="text-sm text-[var(--ink-soft)]">Sin resultado de cupos para esta fecha.</p>
      ) : (
        <>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={soloAlertas} onChange={(e) => setSoloAlertas(e.target.checked)} />
              Ver solo alertas y excedidos
            </label>
            <BotonesResultado recurso="cupos" fecha={fecha} corridaId={data.corrida_id} puedePublicar={puede(usuario, "cupos", "puede_publicar")} />
          </div>

          <div className="bg-white border border-[var(--rule)] rounded-lg divide-y divide-[var(--rule-soft)]">
            <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 px-4 py-2 text-xs font-medium text-[var(--ink-soft)] bg-gray-50">
              <span>Entidad</span>
              <span className="text-right">Límite</span>
              <span className="text-right">Expuesto</span>
              <span className="text-right">Utilización</span>
              <span className="text-right">Estado</span>
            </div>
            {filas.map((c) => {
              const clave = `${c.tipo}-${c.entidad_id}`;
              const abierta = filaAbierta === clave;
              return (
                <div key={clave}>
                  <button
                    onClick={() => setFilaAbierta(abierta ? null : clave)}
                    className="w-full grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 px-4 py-3 text-sm items-center hover:bg-gray-50 text-left"
                  >
                    <span>
                      {c.entidad_nombre} <span className="text-xs text-[var(--ink-soft)]">({c.tipo})</span>
                    </span>
                    <span className="text-right cifra">{c.valor_limite !== null ? `$${formatearNumero(c.valor_limite, 0)}` : "—"}</span>
                    <span className="text-right cifra">${formatearNumero(c.valor_expuesto, 0)}</span>
                    <span className="text-right cifra">{c.utilizacion !== null ? formatearPorcentaje(c.utilizacion, 1) : "—"}</span>
                    <span className="text-right"><SemaforoCupo estado={c.estado} /></span>
                  </button>
                  {abierta && (
                    <div className="px-4 pb-3 text-xs text-[var(--ink-soft)]">
                      <pre className="bg-gray-50 rounded-md p-2 overflow-x-auto">{JSON.stringify(c.detalle, null, 2)}</pre>
                    </div>
                  )}
                </div>
              );
            })}
            {filas.length === 0 && (
              <div className="px-4 py-6 text-sm text-[var(--ink-soft)] text-center">Sin entidades para mostrar.</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
