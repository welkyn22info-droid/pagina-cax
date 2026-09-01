"use client";

import { borrarToken, obtenerToken } from "./sesion";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export class ErrorApi extends Error {
  codigo: string;
  detalle: unknown;
  status: number;

  constructor(status: number, codigo: string, mensaje: string, detalle: unknown) {
    super(mensaje);
    this.status = status;
    this.codigo = codigo;
    this.detalle = detalle;
  }
}

interface OpcionesPeticion {
  metodo?: string;
  cuerpo?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | undefined>;
}

function construirUrl(ruta: string, query?: OpcionesPeticion["query"]): string {
  const url = new URL(BASE + ruta, typeof window !== "undefined" ? window.location.origin : "http://localhost");
  if (query) {
    for (const [clave, valor] of Object.entries(query)) {
      if (valor !== undefined && valor !== "") url.searchParams.set(clave, String(valor));
    }
  }
  // BASE absoluto (dev: http://localhost:8000) necesita la URL completa;
  // BASE relativo (prod detrás de Nginx: "/api") solo necesita path+query,
  // para no atarse a un origin — devolver solo pathname ahí rompería el
  // caso absoluto, que es justo lo que pasaba antes de este ajuste.
  return /^https?:\/\//.test(BASE) ? url.toString() : url.pathname + url.search;
}

export async function api<T>(ruta: string, opciones: OpcionesPeticion = {}): Promise<T> {
  const token = obtenerToken();
  const encabezados: Record<string, string> = {};
  if (token) encabezados["Authorization"] = `Bearer ${token}`;

  let cuerpo: BodyInit | undefined;
  if (opciones.formData) {
    cuerpo = opciones.formData;
  } else if (opciones.cuerpo !== undefined) {
    encabezados["Content-Type"] = "application/json";
    cuerpo = JSON.stringify(opciones.cuerpo);
  }

  const respuesta = await fetch(construirUrl(ruta, opciones.query), {
    method: opciones.metodo || (cuerpo ? "POST" : "GET"),
    headers: encabezados,
    body: cuerpo,
  });

  if (respuesta.status === 401) {
    borrarToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }

  if (!respuesta.ok) {
    let cuerpoError: { error?: string; mensaje?: string; detalle?: unknown } = {};
    try {
      cuerpoError = await respuesta.json();
    } catch {
      // respuesta sin cuerpo JSON (p.ej. error de proxy)
    }
    throw new ErrorApi(
      respuesta.status,
      cuerpoError.error || "error_desconocido",
      cuerpoError.mensaje || `Error ${respuesta.status}`,
      cuerpoError.detalle
    );
  }

  const tipo = respuesta.headers.get("content-type") || "";
  if (tipo.includes("application/json")) return respuesta.json() as Promise<T>;
  return respuesta.blob() as unknown as Promise<T>;
}

// ---- Tipos de dominio (reflejan las tablas de la sección 6) ----

export interface Carga {
  id: number;
  tipo_insumo: string;
  fecha_datos: string;
  nombre_archivo: string;
  filas_leidas: number | null;
  filas_validas: number | null;
  estado: "RECIBIDO" | "VALIDADO" | "RECHAZADO";
  cargado_por: number;
  cargado_en: string;
}

export interface Corrida {
  id: number;
  proceso: string;
  fecha_datos: string;
  estado: "PENDIENTE" | "EJECUTANDO" | "OK" | "ERROR" | "ANULADA";
  disparada_por: number;
  iniciada_en: string;
  finalizada_en: string | null;
  duracion_ms: number | null;
  filas_resultado: number | null;
  mensaje_error: string | null;
}

export interface ProcesoCatalogo {
  proceso: string;
  nombre: string;
  modulo: string;
  requisitos: { tipo_insumo: string | null; proceso_previo: string | null }[];
  ultima_corrida: Corrida | null;
}

export interface FilaValoracion {
  portafolio: string;
  instrumento_cod: string;
  emisor_cod: string | null;
  nominal: number;
  precio_usado: number;
  valor_mercado: number;
  valor_causado: number;
  duracion: number | null;
  moneda: string;
  metricas_extra: Record<string, unknown> | null;
}

export interface FilaPasivo {
  concepto: string;
  valor_presente: number;
  duracion: number | null;
  tasa_descuento: number;
}

export interface PuntoFundingRatio {
  corrida_id: number;
  fecha_datos: string;
  valor_activos: number;
  valor_pasivos: number;
  ratio: number;
  superavit_deficit: number;
}

export interface FilaCupo {
  tipo: "emisor" | "contraparte";
  entidad_id: number;
  entidad_nombre: string;
  limite_id: number | null;
  valor_limite: number | null;
  valor_expuesto: number;
  utilizacion: number | null;
  estado: "OK" | "ALERTA" | "EXCEDIDO" | "SIN_LIMITE";
  detalle: Record<string, unknown> | null;
}

export interface Publicacion {
  id: number;
  titulo: string;
  comentario: string | null;
  corrida_id: number;
  proceso: string;
  fecha_datos: string;
  publicada_por: number;
  publicada_en: string;
}

export interface UsuarioAdmin {
  id: number;
  correo: string;
  nombre: string;
  rol: string;
  activo: boolean;
  debe_cambiar_clave: boolean;
  ultimo_acceso: string | null;
}

export interface LimiteCupo {
  id: number;
  tipo: string;
  entidad_id: number;
  entidad_nombre: string;
  entidad_codigo: string;
  base: string;
  valor_limite: number;
  umbral_alerta: number;
  vigente_desde: string;
  vigente_hasta: string | null;
}
