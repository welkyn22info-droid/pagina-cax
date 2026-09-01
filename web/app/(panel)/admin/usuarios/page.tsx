"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ErrorApi, UsuarioAdmin } from "@/lib/api";
import { formatearFechaHora } from "@/lib/fechas";

const ROLES = ["admin", "analista", "revisor", "consulta"];

export default function PaginaUsuarios() {
  const cliente = useQueryClient();
  const [mostrarForm, setMostrarForm] = useState(false);
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState("analista");
  const [claveTemporal, setClaveTemporal] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: usuarios, refetch } = useQuery<UsuarioAdmin[]>({
    queryKey: ["admin", "usuarios"],
    queryFn: () => api<UsuarioAdmin[]>("/admin/usuarios"),
  });

  async function crear(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const r = await api<{ usuario_id: number; clave_temporal: string }>("/admin/usuarios", {
        metodo: "POST",
        cuerpo: { correo, nombre, rol },
      });
      setClaveTemporal(r.clave_temporal);
      setCorreo("");
      setNombre("");
      refetch();
    } catch (err) {
      setError(err instanceof ErrorApi ? err.message : "No se pudo crear el usuario.");
    }
  }

  async function alternarActivo(u: UsuarioAdmin) {
    await api(`/admin/usuarios/${u.id}`, { metodo: "PATCH", cuerpo: { activo: !u.activo } });
    cliente.invalidateQueries({ queryKey: ["admin", "usuarios"] });
  }

  async function cambiarRol(u: UsuarioAdmin, nuevoRol: string) {
    await api(`/admin/usuarios/${u.id}`, { metodo: "PATCH", cuerpo: { rol: nuevoRol } });
    cliente.invalidateQueries({ queryKey: ["admin", "usuarios"] });
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Usuarios</h1>
        <button onClick={() => setMostrarForm((v) => !v)} className="text-sm bg-[var(--teal)] text-white rounded-md px-3 py-1.5">
          {mostrarForm ? "Cancelar" : "Nuevo usuario"}
        </button>
      </div>

      {mostrarForm && (
        <form onSubmit={crear} className="bg-white border border-[var(--rule)] rounded-lg p-5 mb-6 grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Correo</label>
            <input required type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Nombre</label>
            <input required value={nombre} onChange={(e) => setNombre(e.target.value)} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-[var(--ink-soft)] mb-1">Rol</label>
            <select value={rol} onChange={(e) => setRol(e.target.value)} className="w-full border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm">
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="sm:col-span-3">
            <button type="submit" className="text-sm bg-[var(--teal)] text-white rounded-md px-3 py-1.5">Crear</button>
            {error && <span className="text-xs text-[var(--danger)] ml-3">{error}</span>}
          </div>
        </form>
      )}

      {claveTemporal && (
        <div className="bg-[var(--amber-pale)] text-[var(--amber)] text-sm rounded-md px-4 py-3 mb-6">
          Usuario creado. Contraseña temporal (comuníquela fuera de esta pantalla, no vuelve a mostrarse):{" "}
          <code className="font-mono font-semibold">{claveTemporal}</code>
        </div>
      )}

      <div className="bg-white border border-[var(--rule)] rounded-lg divide-y divide-[var(--rule-soft)]">
        {(usuarios || []).map((u) => (
          <div key={u.id} className="px-4 py-3 flex items-center justify-between gap-4 text-sm flex-wrap">
            <div>
              <p className="font-medium">{u.nombre} <span className="text-[var(--ink-soft)] font-normal">— {u.correo}</span></p>
              <p className="text-xs text-[var(--ink-soft)]">Último acceso: {formatearFechaHora(u.ultimo_acceso)}</p>
            </div>
            <div className="flex items-center gap-3">
              <select value={u.rol} onChange={(e) => cambiarRol(u, e.target.value)} className="border border-[var(--rule)] rounded-md px-2 py-1 text-xs">
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <button onClick={() => alternarActivo(u)} className={`text-xs px-2.5 py-1 rounded-full ${u.activo ? "bg-[var(--teal-pale)] text-[var(--teal)]" : "bg-gray-100 text-gray-500"}`}>
                {u.activo ? "Activo" : "Inactivo"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
