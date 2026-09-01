// Distingue siempre fecha_datos (a qué día corresponden los datos) de las
// marcas de tiempo de operación (sección 20). ISO en la API, dd/mm/aaaa en
// la interfaz (sección 12).

export function ultimoDiaHabil(desde: Date = new Date()): string {
  const fecha = new Date(desde);
  const diaSemana = fecha.getDay(); // 0=domingo, 6=sábado
  if (diaSemana === 0) fecha.setDate(fecha.getDate() - 2);
  else if (diaSemana === 1) fecha.setDate(fecha.getDate() - 3);
  else fecha.setDate(fecha.getDate() - 1);
  return aIso(fecha);
}

export function aIso(fecha: Date): string {
  return fecha.toISOString().slice(0, 10);
}

export function formatearFecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [aaaa, mm, dd] = iso.slice(0, 10).split("-");
  return `${dd}/${mm}/${aaaa}`;
}

export function formatearFechaHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const fecha = new Date(iso);
  return fecha.toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" });
}

export function formatearNumero(valor: number | null | undefined, decimales = 0): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  return valor.toLocaleString("es-CO", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
}

export function formatearPorcentaje(valor: number | null | undefined, decimales = 1): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  return `${(valor * 100).toLocaleString("es-CO", { minimumFractionDigits: decimales, maximumFractionDigits: decimales })}%`;
}
