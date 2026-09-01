"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ErrorApi, LimiteCupo } from "@/lib/api";
import { formatearFecha, formatearNumero, formatearPorcentaje } from "@/lib/fechas";

interface Entidad {
  id: number;
  codigo: string;
  nombre: string;
}

export default function PaginaLimites() {
  const cliente = useQueryClient();
  const [mostrarForm, setMostrarForm] = useState(false);
  const [tipo, setTipo] = useState<"emisor" | "contraparte">("emisor");
  const [entidadId, setEntidadId] = useState<number | "">("");
  const [base, setBase] = useState<"monto" | "porcentaje_portafolio">("monto");
  const [valorLimite, setValorLimite] = useState("");
  const [umbral, setUmbral] = useState("0.80");
  const [vigenteDesde, setVigenteDesde] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  const { data: limites, refetch } = useQuery<LimiteCupo[]>({
    queryKey: ["cupos", "limites"],
    queryFn: () => api<LimiteCupo[]>("/cupos/limites"),
  });

  const { data: entidades } = useQuery<Entidad[]>({
    queryKey: ["cupos", "entidades", tipo],
    queryFn: () => api<Entidad[]>("/cupos/entidades", { query: { tipo } }),
    enabled: mostrarForm,
  });

  async function crear(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!entidadId) {
      setError("Seleccione una entidad.");
      return;
    }
    try {
      await api("/cupos/limites", {
        metodo: "POST",
        cuerpo: {
          tipo,
          entidad_id: entidadId,
          base,
          valor_limite: base === "porcentaje_portafolio" ? Number(valorLimite) / 100 : Number(valorLimite),
          umbral_alerta: Number(umbral),
          vigente_desde: vigenteDesde,
        },
      });
      setMostrarForm(false);
      setValorLimite("");
      refetch();
      cliente.invalidateQueries({ queryKey: ["cupos"] });
    } catch (err) {
      setError(err instanceof ErrorApi ? err.message : "No se pudo crear el límite.");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Límites de cupo</h1>
        <button onClick={() => setMostrarForm((v) => !v)} className="text-sm bg-[var(--teal)] text-white rounded-md px-3 py-1.5">
          {mostrarForm ? "Cancelar" : "Nuevo límite"}
        </button>
      </div>

      {mostrarForm && (
        <form onSubmit={crear} className="bg-white border border-[var(--rule)] rounded-lg p-5 mb-6 grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Tipo</label>
            <select value={tipo} onChange={(e) => { setTipo(e.target.value as "emisor" | "contraparte"); setEntidadId(""); }} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm">
              <option value="emisor">Emisor</option>
              <option value="contraparte">Contraparte</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Entidad</label>
            <select required value={entidadId} onChange={(e) => setEntidadId(Number(e.target.value))} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm">
              <option value="">Seleccione…</option>
              {(entidades || []).map((en) => <option key={en.id} value={en.id}>{en.nombre} ({en.codigo})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Base</label>
            <select value={base} onChange={(e) => setBase(e.target.value as "monto" | "porcentaje_portafolio")} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm">
              <option value="monto">Monto</option>
              <option value="porcentaje_portafolio">% del portafolio</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">{base === "monto" ? "Valor límite ($)" : "Valor límite (%)"}</label>
            <input required type="number" step="any" value={valorLimite} onChange={(e) => setValorLimite(e.target.value)} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm cifra" />
          </div>
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Umbral de alerta (0-1)</label>
            <input required type="number" step="0.01" min="0" max="1" value={umbral} onChange={(e) => setUmbral(e.target.value)} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm cifra" />
          </div>
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Vigente desde</label>
            <input required type="date" value={vigenteDesde} onChange={(e) => setVigenteDesde(e.target.value)} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm cifra" />
          </div>
          <div className="sm:col-span-3">
            <button type="submit" className="text-sm bg-[var(--teal)] text-white rounded-md px-3 py-1.5">Crear límite</button>
            {error && <span className="text-xs text-[var(--danger)] ml-3">{error}</span>}
          </div>
        </form>
      )}

      <div className="bg-white border border-[var(--rule)] rounded-lg divide-y divide-[var(--rule-soft)]">
        {(limites || []).map((l) => (
          <div key={l.id} className="px-4 py-3 flex items-center justify-between text-sm flex-wrap gap-2">
            <div>
              <p className="font-medium">{l.entidad_nombre} <span className="text-xs text-[var(--ink-soft)]">({l.tipo})</span></p>
              <p className="text-xs text-[var(--ink-soft)]">
                Vigente desde {formatearFecha(l.vigente_desde)}{l.vigente_hasta ? ` hasta ${formatearFecha(l.vigente_hasta)}` : ""}
              </p>
            </div>
            <div className="text-right">
              <p className="cifra font-medium">
                {l.base === "monto" ? `$${formatearNumero(l.valor_limite, 0)}` : formatearPorcentaje(l.valor_limite, 1)}
              </p>
              <p className="text-xs text-[var(--ink-soft)]">alerta desde {formatearPorcentaje(l.umbral_alerta, 0)}</p>
            </div>
          </div>
        ))}
        {(limites || []).length === 0 && (
          <div className="px-4 py-6 text-sm text-[var(--ink-soft)] text-center">Sin límites parametrizados.</div>
        )}
      </div>
    </div>
  );
}
