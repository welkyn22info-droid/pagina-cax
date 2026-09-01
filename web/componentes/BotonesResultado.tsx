"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ErrorApi } from "@/lib/api";
import { obtenerToken } from "@/lib/sesion";

interface UsuarioDirectorio {
  id: number;
  nombre: string;
  correo: string;
  rol: string;
}

export default function BotonesResultado({
  recurso,
  fecha,
  corridaId,
  puedePublicar,
}: {
  recurso: "valoracion" | "pasivo" | "cupos" | "funding-ratio";
  fecha: string;
  corridaId: number;
  puedePublicar: boolean;
}) {
  const [modalAbierto, setModalAbierto] = useState(false);

  async function exportar() {
    const base = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    const respuesta = await fetch(`${base}/exportar/${recurso}?fecha=${fecha}`, {
      headers: { Authorization: `Bearer ${obtenerToken()}` },
    });
    if (!respuesta.ok) return;
    const blob = await respuesta.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${recurso}_${fecha}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex items-center gap-2">
      <button onClick={exportar} className="text-sm border border-[var(--rule)] rounded-md px-3 py-1.5 hover:bg-gray-50">
        Exportar a Excel
      </button>
      {puedePublicar && (
        <button onClick={() => setModalAbierto(true)} className="text-sm bg-[var(--teal)] text-white rounded-md px-3 py-1.5">
          Publicar
        </button>
      )}
      {modalAbierto && <ModalPublicar recurso={recurso} corridaId={corridaId} onCerrar={() => setModalAbierto(false)} />}
    </div>
  );
}

function ModalPublicar({ recurso, corridaId, onCerrar }: { recurso: string; corridaId: number; onCerrar: () => void }) {
  const [titulo, setTitulo] = useState(`${recurso} — corrida #${corridaId}`);
  const [comentario, setComentario] = useState("");
  const [seleccionados, setSeleccionados] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  const { data: usuarios } = useQuery<UsuarioDirectorio[]>({
    queryKey: ["usuarios"],
    queryFn: () => api<UsuarioDirectorio[]>("/usuarios"),
  });

  function alternar(id: number) {
    setSeleccionados((actual) => (actual.includes(id) ? actual.filter((x) => x !== id) : [...actual, id]));
  }

  async function publicar() {
    if (seleccionados.length === 0) {
      setError("Seleccione al menos un destinatario.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await api("/publicaciones", {
        metodo: "POST",
        cuerpo: { corrida_id: corridaId, titulo, comentario: comentario || null, destinatarios: seleccionados },
      });
      setEnviado(true);
    } catch (err) {
      setError(err instanceof ErrorApi ? err.message : "No se pudo publicar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        {enviado ? (
          <div>
            <p className="text-sm font-medium mb-4">Publicación creada. Los destinatarios verán el aviso al entrar.</p>
            <button onClick={onCerrar} className="text-sm bg-[var(--teal)] text-white rounded-md px-3 py-1.5">Cerrar</button>
          </div>
        ) : (
          <>
            <h3 className="font-semibold mb-4">Publicar resultado</h3>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Título</label>
            <input value={titulo} onChange={(e) => setTitulo(e.target.value)} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm mb-3" />
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Comentario (opcional)</label>
            <textarea value={comentario} onChange={(e) => setComentario(e.target.value)} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm mb-3" rows={2} />
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Destinatarios</label>
            <div className="border border-[var(--rule)] rounded-md max-h-40 overflow-y-auto mb-3">
              {(usuarios || []).map((u) => (
                <label key={u.id} className="flex items-center gap-2 px-2.5 py-1.5 text-sm border-b border-[var(--rule-soft)] last:border-0">
                  <input type="checkbox" checked={seleccionados.includes(u.id)} onChange={() => alternar(u.id)} />
                  {u.nombre} <span className="text-xs text-[var(--ink-soft)]">({u.rol})</span>
                </label>
              ))}
            </div>
            {error && <p className="text-xs text-[var(--danger)] mb-3">{error}</p>}
            <div className="flex items-center gap-2 justify-end">
              <button onClick={onCerrar} className="text-sm px-3 py-1.5">Cancelar</button>
              <button onClick={publicar} disabled={enviando} className="text-sm bg-[var(--teal)] text-white rounded-md px-3 py-1.5 disabled:opacity-50">
                {enviando ? "Publicando…" : "Publicar"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
