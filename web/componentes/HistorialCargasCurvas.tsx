"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ErrorApi, Carga } from "@/lib/api";
import { formatearFecha, formatearFechaHora } from "@/lib/fechas";
import { useUsuario } from "@/lib/hooks";

export default function HistorialCargasCurvas() {
  const [anulando, setAnulando] = useState<number | null>(null);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { data: usuario } = useUsuario();
  const cliente = useQueryClient();

  const { data: cargas } = useQuery<Carga[]>({
    queryKey: ["cargas", "curvas", "todas"],
    queryFn: () => api<Carga[]>("/cargas", { query: { tipo_insumo: "curvas" } }),
  });

  async function confirmar(cargaId: number) {
    if (!motivo.trim()) return;
    setError(null);
    try {
      await api(`/cargas/${cargaId}/anular`, { metodo: "POST", cuerpo: { motivo } });
      setAnulando(null);
      setMotivo("");
      cliente.invalidateQueries({ queryKey: ["cargas"] });
      cliente.invalidateQueries({ queryKey: ["curvas"] });
    } catch (err) {
      setError(err instanceof ErrorApi ? err.message : "No se pudo anular la carga.");
    }
  }

  const filas = (cargas || []).slice(0, 100);

  return (
    <div className="border border-[var(--rule)] rounded-lg bg-white">
      <div className="px-4 py-3 border-b border-[var(--rule-soft)]">
        <p className="text-sm font-medium">Cargas de curvas</p>
        <p className="text-xs text-[var(--ink-soft)]">
          Solo puede anular quien cargó cada archivo (o un administrador).
        </p>
      </div>
      <div className="divide-y divide-[var(--rule-soft)] max-h-96 overflow-y-auto">
        {filas.length === 0 && (
          <div className="px-4 py-6 text-sm text-[var(--ink-soft)] text-center">Todavía no hay cargas de curvas.</div>
        )}
        {filas.map((c) => {
          const puedeAnular = !c.anulada_en && usuario && (c.cargado_por === usuario.id || usuario.rol === "admin");
          return (
            <div key={c.id} className="px-4 py-2.5 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <span className={c.anulada_en ? "line-through text-[var(--ink-soft)]" : ""}>
                    {formatearFecha(c.fecha_datos)}
                  </span>
                  <span className="text-xs text-[var(--ink-soft)]">
                    {" "}
                    · {c.cargado_por_nombre} · {formatearFechaHora(c.cargado_en)} · {c.filas_validas ?? 0} filas
                  </span>
                  {c.anulada_en && (
                    <p className="text-xs text-[var(--danger)] mt-0.5">
                      Anulada por {c.anulada_por_nombre} el {formatearFechaHora(c.anulada_en)} — {c.motivo_anulacion}
                    </p>
                  )}
                </div>
                {puedeAnular && (
                  <button
                    onClick={() => {
                      setAnulando(anulando === c.id ? null : c.id);
                      setMotivo("");
                      setError(null);
                    }}
                    className="text-xs text-[var(--danger)] hover:underline shrink-0"
                  >
                    Anular
                  </button>
                )}
              </div>
              {anulando === c.id && (
                <div className="mt-2 flex items-center gap-2">
                  <input
                    type="text"
                    value={motivo}
                    onChange={(e) => setMotivo(e.target.value)}
                    placeholder="Motivo de la anulación"
                    className="flex-1 border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-xs"
                  />
                  <button
                    onClick={() => confirmar(c.id)}
                    disabled={!motivo.trim()}
                    className="text-xs bg-[var(--danger)] text-white rounded-md px-3 py-1.5 disabled:opacity-50"
                  >
                    Confirmar
                  </button>
                </div>
              )}
              {anulando === c.id && error && <p className="text-xs text-[var(--danger)] mt-1">{error}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
