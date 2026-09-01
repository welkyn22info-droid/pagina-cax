"use client";

import { useRef, useState } from "react";
import { api, ErrorApi } from "@/lib/api";

const TIPOS: { valor: string; etiqueta: string }[] = [
  { valor: "posiciones", etiqueta: "Posiciones" },
  { valor: "precios", etiqueta: "Precios" },
  { valor: "flujos_pasivo", etiqueta: "Flujos de pasivo" },
];

function detectarTipo(nombre: string): string {
  const n = nombre.toLowerCase();
  if (n.includes("posicion")) return "posiciones";
  if (n.includes("precio")) return "precios";
  if (n.includes("flujo") || n.includes("pasivo")) return "flujos_pasivo";
  return "posiciones";
}

interface ArchivoPendiente {
  archivo: File;
  tipo: string;
  estado: "pendiente" | "subiendo" | "listo" | "error";
  resultado?: { estado: string; filas_leidas: number; filas_validas: number; mensaje: string; duplicado: boolean };
  error?: string;
}

export default function SubidorArchivos({ fecha, onCompletado }: { fecha: string; onCompletado?: () => void }) {
  const [pendientes, setPendientes] = useState<ArchivoPendiente[]>([]);
  const [arrastrando, setArrastrando] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function agregarArchivos(lista: FileList) {
    const nuevos: ArchivoPendiente[] = Array.from(lista).map((archivo) => ({
      archivo,
      tipo: detectarTipo(archivo.name),
      estado: "pendiente",
    }));
    setPendientes((actual) => [...actual, ...nuevos]);
  }

  function cambiarTipo(idx: number, tipo: string) {
    setPendientes((actual) => actual.map((p, i) => (i === idx ? { ...p, tipo } : p)));
  }

  function quitar(idx: number) {
    setPendientes((actual) => actual.filter((_, i) => i !== idx));
  }

  async function confirmarTodos() {
    for (let i = 0; i < pendientes.length; i++) {
      if (pendientes[i].estado === "listo") continue;
      setPendientes((actual) => actual.map((p, idx) => (idx === i ? { ...p, estado: "subiendo" } : p)));
      const form = new FormData();
      form.append("archivo", pendientes[i].archivo);
      form.append("tipo_insumo", pendientes[i].tipo);
      form.append("fecha_datos", fecha);
      try {
        const resultado = await api<{ estado: string; filas_leidas: number; filas_validas: number; mensaje: string; duplicado: boolean }>(
          "/cargas",
          { metodo: "POST", formData: form }
        );
        setPendientes((actual) => actual.map((p, idx) => (idx === i ? { ...p, estado: "listo", resultado } : p)));
      } catch (err) {
        const mensaje = err instanceof ErrorApi ? err.message : "No se pudo subir el archivo.";
        setPendientes((actual) => actual.map((p, idx) => (idx === i ? { ...p, estado: "error", error: mensaje } : p)));
      }
    }
    onCompletado?.();
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          if (e.dataTransfer.files.length) agregarArchivos(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg py-10 text-center cursor-pointer transition-colors ${
          arrastrando ? "border-[var(--teal)] bg-[var(--teal-pale)]" : "border-[var(--rule)] bg-white"
        }`}
      >
        <p className="text-sm text-[var(--ink-soft)]">Arrastre uno o varios archivos aquí, o haga clic para elegirlos</p>
        <p className="text-xs text-[var(--ink-soft)] mt-1">TXT o Excel — el tipo se detecta por el nombre y se puede corregir abajo</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".txt,.xlsx,.xls"
          className="hidden"
          onChange={(e) => e.target.files && agregarArchivos(e.target.files)}
        />
      </div>

      {pendientes.length > 0 && (
        <div className="mt-4 space-y-2">
          {pendientes.map((p, idx) => (
            <div key={idx} className="border border-[var(--rule-soft)] rounded-md p-3 bg-white">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <span className="text-sm font-medium">{p.archivo.name}</span>
                <div className="flex items-center gap-2">
                  <select
                    value={p.tipo}
                    disabled={p.estado === "listo" || p.estado === "subiendo"}
                    onChange={(e) => cambiarTipo(idx, e.target.value)}
                    className="border border-[var(--rule)] rounded-md px-2 py-1 text-xs"
                  >
                    {TIPOS.map((t) => (
                      <option key={t.valor} value={t.valor}>{t.etiqueta}</option>
                    ))}
                  </select>
                  {p.estado === "pendiente" && (
                    <button onClick={() => quitar(idx)} className="text-xs text-[var(--danger)]">Quitar</button>
                  )}
                  {p.estado === "subiendo" && <span className="text-xs text-[var(--ink-soft)]">Subiendo…</span>}
                </div>
              </div>

              {p.resultado && (
                <div className={`mt-2 text-xs rounded-md px-2.5 py-2 whitespace-pre-line font-mono ${
                  p.resultado.estado === "VALIDADO" ? "bg-[var(--teal-pale)] text-[var(--teal)]" : "bg-[var(--danger-pale)] text-[var(--danger)]"
                }`}>
                  {p.resultado.duplicado
                    ? "Este archivo ya se había cargado para esta fecha. No se volvió a insertar."
                    : p.resultado.mensaje}
                </div>
              )}
              {p.error && (
                <div className="mt-2 text-xs rounded-md px-2.5 py-2 bg-[var(--danger-pale)] text-[var(--danger)]">{p.error}</div>
              )}
            </div>
          ))}

          <button
            onClick={confirmarTodos}
            disabled={pendientes.every((p) => p.estado === "listo") || pendientes.some((p) => p.estado === "subiendo")}
            className="mt-2 bg-[var(--teal)] text-white text-sm font-medium rounded-md px-4 py-2 disabled:opacity-50"
          >
            Confirmar y cargar
          </button>
        </div>
      )}
    </div>
  );
}
