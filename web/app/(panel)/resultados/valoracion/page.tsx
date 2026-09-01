"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FilaValoracion } from "@/lib/api";
import { formatearNumero, ultimoDiaHabil } from "@/lib/fechas";
import SelectorFecha from "@/componentes/SelectorFecha";
import TablaResultados, { Columna } from "@/componentes/TablaResultados";
import BotonesResultado from "@/componentes/BotonesResultado";
import { useUsuario } from "@/lib/hooks";
import { puede } from "@/lib/sesion";

interface RespuestaValoracion {
  corrida_id: number | null;
  filas: FilaValoracion[];
  agregados: { num_posiciones: number; valor_total: number; sin_precio: number } | null;
}

const COLUMNAS: Columna<FilaValoracion>[] = [
  { clave: "portafolio", titulo: "Portafolio" },
  { clave: "instrumento_cod", titulo: "Instrumento" },
  { clave: "emisor_cod", titulo: "Emisor" },
  { clave: "nominal", titulo: "Nominal", numerica: true, formatear: (f) => formatearNumero(f.nominal, 0) },
  { clave: "precio_usado", titulo: "Precio", numerica: true, formatear: (f) => formatearNumero(f.precio_usado, 4) },
  { clave: "valor_mercado", titulo: "Valor de mercado", numerica: true, formatear: (f) => formatearNumero(f.valor_mercado, 0) },
  { clave: "moneda", titulo: "Moneda" },
];

export default function PaginaValoracion() {
  const [fecha, setFecha] = useState(ultimoDiaHabil());
  const { data: usuario } = useUsuario();

  const { data } = useQuery<RespuestaValoracion>({
    queryKey: ["resultados", "valoracion", fecha],
    queryFn: () => api("/resultados/valoracion", { query: { fecha } }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Valoración de activos</h1>
        <SelectorFecha valor={fecha} onCambiar={setFecha} />
      </div>

      {!data?.corrida_id ? (
        <p className="text-sm text-[var(--ink-soft)]">Sin resultado de valoración para esta fecha.</p>
      ) : (
        <>
          <div className="flex items-end justify-between mb-6 flex-wrap gap-4">
            <div>
              <p className="text-xs text-[var(--ink-soft)] mb-1">Valor total de mercado</p>
              <p className="text-2xl font-semibold cifra">${formatearNumero(data.agregados?.valor_total, 0)}</p>
              <p className="text-xs text-[var(--ink-soft)] mt-1">
                {data.agregados?.num_posiciones} posiciones
                {data.agregados?.sin_precio ? ` · ${data.agregados.sin_precio} sin precio` : ""}
              </p>
              <Link href={`/procesos/valoracion`} className="text-xs text-[var(--teal)]">Ver corrida #{data.corrida_id} de origen</Link>
            </div>
            <BotonesResultado
              recurso="valoracion"
              fecha={fecha}
              corridaId={data.corrida_id}
              puedePublicar={puede(usuario, "valoracion", "puede_publicar")}
            />
          </div>
          <TablaResultados<FilaValoracion> columnas={COLUMNAS} filas={data.filas} claveFila={(f) => `${f.portafolio}-${f.instrumento_cod}`} busquedaPor={["portafolio", "instrumento_cod", "emisor_cod"]} ordenInicial={{ clave: "valor_mercado", descendente: true }} />
        </>
      )}
    </div>
  );
}
