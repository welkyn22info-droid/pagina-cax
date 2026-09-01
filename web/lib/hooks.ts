"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { obtenerToken, UsuarioSesion } from "./sesion";

export function useUsuario() {
  return useQuery<UsuarioSesion>({
    queryKey: ["auth", "yo"],
    queryFn: () => api<UsuarioSesion>("/auth/yo"),
    enabled: typeof window !== "undefined" && Boolean(obtenerToken()),
    staleTime: 60_000,
    retry: false,
  });
}
