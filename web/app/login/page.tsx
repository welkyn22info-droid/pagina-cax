"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ErrorApi } from "@/lib/api";
import { guardarToken } from "@/lib/sesion";

export default function PaginaLogin() {
  const router = useRouter();
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const resp = await api<{ token: string; debe_cambiar_clave: boolean }>("/auth/login", {
        metodo: "POST",
        cuerpo: { correo, clave },
      });
      guardarToken(resp.token);
      router.push(resp.debe_cambiar_clave ? "/cambiar-clave" : "/");
    } catch (err) {
      setError(err instanceof ErrorApi ? err.message : "No se pudo conectar con el servidor.");
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--paper)] px-4">
      <div className="w-full max-w-sm bg-white border border-[var(--rule)] rounded-lg p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-[var(--ink)] mb-1">Plataforma de riesgo</h1>
        <p className="text-sm text-[var(--ink-soft)] mb-6">Ingrese con su correo y contraseña.</p>

        <form onSubmit={enviar} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--ink-soft)] mb-1">Correo</label>
            <input
              type="email"
              required
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
              className="w-full border border-[var(--rule)] rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--teal)]"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--ink-soft)] mb-1">Contraseña</label>
            <input
              type="password"
              required
              value={clave}
              onChange={(e) => setClave(e.target.value)}
              className="w-full border border-[var(--rule)] rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--teal)]"
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="text-sm text-[var(--danger)] bg-[var(--danger-pale)] rounded-md px-3 py-2">{error}</div>
          )}

          <button
            type="submit"
            disabled={cargando}
            className="w-full bg-[var(--teal)] text-white rounded-md py-2 text-sm font-medium disabled:opacity-60"
          >
            {cargando ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
      </div>
    </div>
  );
}
