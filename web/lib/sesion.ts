"use client";

// Sesión en localStorage: son 5-10 usuarios en red interna (sección 7),
// no se justifica un proveedor externo de identidad ni cookies de sesión.

export interface Permiso {
  modulo: string;
  puede_ver: boolean;
  puede_cargar: boolean;
  puede_ejecutar: boolean;
  puede_publicar: boolean;
}

export interface UsuarioSesion {
  id: number;
  correo: string;
  nombre: string;
  rol: "admin" | "analista" | "revisor" | "consulta";
  permisos: Permiso[];
}

const CLAVE_TOKEN = "riesgo_token";

export function guardarToken(token: string) {
  localStorage.setItem(CLAVE_TOKEN, token);
}

export function obtenerToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(CLAVE_TOKEN);
}

export function borrarToken() {
  localStorage.removeItem(CLAVE_TOKEN);
}

export function puede(usuario: UsuarioSesion | undefined, modulo: string, accion: keyof Omit<Permiso, "modulo">): boolean {
  if (!usuario) return false;
  const p = usuario.permisos.find((p) => p.modulo === modulo);
  return p ? Boolean(p[accion]) : false;
}
