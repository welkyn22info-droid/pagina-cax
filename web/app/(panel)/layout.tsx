"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useUsuario } from "@/lib/hooks";
import { borrarToken, obtenerToken, puede } from "@/lib/sesion";
import type { Publicacion } from "@/lib/api";

interface ItemNav {
  href: string;
  etiqueta: string;
  modulo?: string;
  soloAdmin?: boolean;
}

const NAV: ItemNav[] = [
  { href: "/", etiqueta: "Panel" },
  { href: "/cargas", etiqueta: "Cargas" },
  { href: "/procesos", etiqueta: "Procesos" },
  { href: "/resultados/valoracion", etiqueta: "Valoración", modulo: "valoracion" },
  { href: "/resultados/pasivo", etiqueta: "Pasivo", modulo: "pasivo" },
  { href: "/resultados/funding-ratio", etiqueta: "Funding ratio", modulo: "funding_ratio" },
  { href: "/controles/cupos", etiqueta: "Cupos", modulo: "cupos" },
  { href: "/auditoria", etiqueta: "Auditoría", soloAdmin: true },
  { href: "/admin/usuarios", etiqueta: "Usuarios", soloAdmin: true },
  { href: "/admin/limites", etiqueta: "Límites de cupo", soloAdmin: true },
];

export default function LayoutPanel({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: usuario, isError, isLoading } = useUsuario();

  useEffect(() => {
    if (!obtenerToken()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    if (isError) router.replace("/login");
  }, [isError, router]);

  const { data: pendientes } = useQuery<Publicacion[]>({
    queryKey: ["publicaciones", "pendientes"],
    queryFn: () => api<Publicacion[]>("/publicaciones/pendientes"),
    enabled: Boolean(usuario),
    refetchInterval: 30_000,
  });

  function cerrarSesion() {
    api("/auth/logout", { metodo: "POST" }).finally(() => {
      borrarToken();
      router.push("/login");
    });
  }

  if (isLoading || !usuario) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-[var(--ink-soft)]">Cargando…</div>;
  }

  const itemsVisibles = NAV.filter((item) => {
    if (item.soloAdmin) return usuario.rol === "admin";
    if (item.modulo) return puede(usuario, item.modulo, "puede_ver");
    return true;
  });

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 bg-[var(--ink)] text-white flex flex-col">
        <div className="px-5 py-5 border-b border-white/10">
          <p className="font-semibold text-sm">Plataforma de riesgo</p>
          <p className="text-xs text-white/50 mt-0.5">{usuario.nombre}</p>
          <p className="text-[10px] uppercase tracking-wide text-white/40 mt-0.5">{usuario.rol}</p>
        </div>
        <nav className="flex-1 py-3">
          {itemsVisibles.map((item) => {
            const activo = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-5 py-2 text-sm ${
                  activo ? "bg-white/10 text-white font-medium" : "text-white/70 hover:bg-white/5 hover:text-white"
                }`}
              >
                {item.etiqueta}
                {item.href === "/" && pendientes && pendientes.length > 0 && (
                  <span className="bg-[var(--amber)] text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">
                    {pendientes.length}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <button onClick={cerrarSesion} className="px-5 py-4 text-sm text-white/60 hover:text-white text-left border-t border-white/10">
          Cerrar sesión
        </button>
      </aside>
      <main className="flex-1 min-w-0 p-8 max-w-6xl">{children}</main>
    </div>
  );
}
