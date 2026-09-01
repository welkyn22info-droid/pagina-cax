"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ErrorApi } from "@/lib/api";

export default function PaginaCambiarClave() {
  const router = useRouter();
  const [claveActual, setClaveActual] = useState("");
  const [claveNueva, setClaveNueva] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      await api("/auth/cambiar-clave", { metodo: "POST", cuerpo: { clave_actual: claveActual, clave_nueva: claveNueva } });
      router.push("/");
    } catch (err) {
      setError(err instanceof ErrorApi ? err.message : "No se pudo cambiar la contraseña.");
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--paper)] px-4">
      <div className="w-full max-w-sm bg-white border border-[var(--rule)] rounded-lg p-8 shadow-sm">
        <h1 className="text-xl font-semibold mb-1">Cambio de contraseña</h1>
        <p className="text-sm text-[var(--ink-soft)] mb-6">
          Es su primer ingreso: debe definir una contraseña nueva de al menos 12 caracteres.
        </p>
        <form onSubmit={enviar} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--ink-soft)] mb-1">Contraseña temporal</label>
            <input
              type="password"
              required
              value={claveActual}
              onChange={(e) => setClaveActual(e.target.value)}
              className="w-full border border-[var(--rule)] rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--ink-soft)] mb-1">Contraseña nueva</label>
            <input
              type="password"
              required
              minLength={12}
              value={claveNueva}
              onChange={(e) => setClaveNueva(e.target.value)}
              className="w-full border border-[var(--rule)] rounded-md px-3 py-2 text-sm"
            />
          </div>
          {error && <div className="text-sm text-[var(--danger)] bg-[var(--danger-pale)] rounded-md px-3 py-2">{error}</div>}
          <button
            type="submit"
            disabled={cargando}
            className="w-full bg-[var(--teal)] text-white rounded-md py-2 text-sm font-medium disabled:opacity-60"
          >
            {cargando ? "Guardando…" : "Guardar y continuar"}
          </button>
        </form>
      </div>
    </div>
  );
}
