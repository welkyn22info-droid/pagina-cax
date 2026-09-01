"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatearFechaHora } from "@/lib/fechas";

interface Evento {
  id: number;
  usuario_id: number | null;
  usuario_nombre: string | null;
  accion: string;
  recurso: string | null;
  recurso_id: number | null;
  detalle: Record<string, unknown> | null;
  ocurrido_en: string;
}

const ETIQUETAS_ACCION: Record<string, string> = {
  ingreso: "Ingreso",
  ingreso_fallido: "Ingreso fallido",
  cierre_sesion: "Cierre de sesión",
  carga: "Carga de insumo",
  ejecucion: "Ejecución",
  anulacion: "Anulación de corrida",
  publicacion: "Publicación",
  acuse: "Acuse de lectura",
  exportacion: "Exportación",
  cambio_limite: "Cambio de límite",
  alta_usuario: "Alta de usuario",
  modificacion_usuario: "Modificación de usuario",
  cambio_clave: "Cambio de contraseña",
};

export default function PaginaAuditoria() {
  const [accion, setAccion] = useState("");

  const { data: eventos } = useQuery<Evento[]>({
    queryKey: ["auditoria", accion],
    queryFn: () => api<Evento[]>("/auditoria"),
  });

  const filtrados = accion ? (eventos || []).filter((e) => e.accion === accion) : eventos || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Auditoría</h1>
        <select value={accion} onChange={(e) => setAccion(e.target.value)} className="border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm">
          <option value="">Todas las acciones</option>
          {Object.entries(ETIQUETAS_ACCION).map(([clave, etiqueta]) => (
            <option key={clave} value={clave}>{etiqueta}</option>
          ))}
        </select>
      </div>

      <div className="bg-white border border-[var(--rule)] rounded-lg divide-y divide-[var(--rule-soft)]">
        {filtrados.map((e) => (
          <div key={e.id} className="px-4 py-3 text-sm flex items-center justify-between gap-4">
            <div>
              <span className="font-medium">{ETIQUETAS_ACCION[e.accion] || e.accion}</span>
              <span className="text-[var(--ink-soft)]"> · {e.usuario_nombre || "sistema"}</span>
              {e.recurso && <span className="text-[var(--ink-soft)]"> · {e.recurso}{e.recurso_id ? ` #${e.recurso_id}` : ""}</span>}
            </div>
            <span className="text-xs text-[var(--ink-soft)] whitespace-nowrap">{formatearFechaHora(e.ocurrido_en)}</span>
          </div>
        ))}
        {filtrados.length === 0 && (
          <div className="px-4 py-6 text-sm text-[var(--ink-soft)] text-center">Sin eventos para el filtro seleccionado.</div>
        )}
      </div>
    </div>
  );
}
