"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FilaPasivo } from "@/lib/api";
import { formatearNumero, ultimoDiaHabil } from "@/lib/fechas";
import SelectorFecha from "@/componentes/SelectorFecha";
import TablaResultados, { Columna } from "@/componentes/TablaResultados";
import BotonesResultado from "@/componentes/BotonesResultado";
import { useUsuario } from "@/lib/hooks";
import { puede } from "@/lib/sesion";

interface RespuestaPasivo {
  corrida_id: number | null;
  filas: FilaPasivo[];
  agregados: { valor_total: number } | null;
}

const COLUMNAS: Columna<FilaPasivo>[] = [
  { clave: "concepto", titulo: "Concepto" },
  { clave: "valor_presente", titulo: "Valor presente", numerica: true, formatear: (f) => formatearNumero(f.valor_presente, 0) },
  { clave: "duracion", titulo: "Duración (años)", numerica: true, formatear: (f) => formatearNumero(f.duracion ?? undefined, 2) },
  { clave: "tasa_descuento", titulo: "Tasa de descuento", numerica: true, formatear: (f) => `${(f.tasa_descuento * 100).toFixed(2)}%` },
];

export default function PaginaPasivo() {
  const [fecha, setFecha] = useState(ultimoDiaHabil());
  const { data: usuario } = useUsuario();

  const { data } = useQuery<RespuestaPasivo>({
    queryKey: ["resultados", "pasivo", fecha],
    queryFn: () => api("/resultados/pasivo", { query: { fecha } }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Cálculo de pasivo</h1>
        <SelectorFecha valor={fecha} onCambiar={setFecha} />
      </div>

      {!data?.corrida_id ? (
        <p className="text-sm text-[var(--ink-soft)]">Sin resultado de pasivo para esta fecha.</p>
      ) : (
        <>
          <div className="flex items-end justify-between mb-6 flex-wrap gap-4">
            <div>
              <p className="text-xs text-[var(--ink-soft)] mb-1">Valor presente total</p>
              <p className="text-2xl font-semibold cifra">${formatearNumero(data.agregados?.valor_total, 0)}</p>
              <Link href="/procesos/pasivo" className="text-xs text-[var(--teal)]">Ver corrida #{data.corrida_id} de origen</Link>
            </div>
            <BotonesResultado recurso="pasivo" fecha={fecha} corridaId={data.corrida_id} puedePublicar={puede(usuario, "pasivo", "puede_publicar")} />
          </div>
          <TablaResultados<FilaPasivo> columnas={COLUMNAS} filas={data.filas} claveFila={(f) => f.concepto} busquedaPor={["concepto"]} ordenInicial={{ clave: "valor_presente", descendente: true }} />
        </>
      )}
    </div>
  );
}
