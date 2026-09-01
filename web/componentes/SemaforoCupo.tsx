// El color nunca es el único portador de información (sección 12): el
// semáforo siempre lleva también la etiqueta de texto.
const ESTILOS: Record<string, string> = {
  OK: "bg-[var(--teal-pale)] text-[var(--teal)]",
  ALERTA: "bg-[var(--amber-pale)] text-[var(--amber)]",
  EXCEDIDO: "bg-[var(--danger-pale)] text-[var(--danger)]",
  SIN_LIMITE: "bg-gray-100 text-gray-600",
};

const ETIQUETAS: Record<string, string> = {
  OK: "OK",
  ALERTA: "Alerta",
  EXCEDIDO: "Excedido",
  SIN_LIMITE: "Sin límite parametrizado",
};

export default function SemaforoCupo({ estado }: { estado: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${ESTILOS[estado] || "bg-gray-100 text-gray-600"}`}>
      {ETIQUETAS[estado] || estado}
    </span>
  );
}
