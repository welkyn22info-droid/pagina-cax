const ESTILOS: Record<string, string> = {
  PENDIENTE: "bg-gray-100 text-gray-600",
  EJECUTANDO: "bg-[var(--amber-pale)] text-[var(--amber)]",
  OK: "bg-[var(--teal-pale)] text-[var(--teal)]",
  ERROR: "bg-[var(--danger-pale)] text-[var(--danger)]",
  ANULADA: "bg-gray-100 text-gray-500 line-through",
};

const ETIQUETAS: Record<string, string> = {
  PENDIENTE: "Pendiente",
  EJECUTANDO: "Ejecutando",
  OK: "Correcto",
  ERROR: "Con error",
  ANULADA: "Anulada",
};

export default function EstadoCorrida({ estado }: { estado: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${ESTILOS[estado] || "bg-gray-100 text-gray-600"}`}>
      {estado === "EJECUTANDO" && (
        <span className="h-1.5 w-1.5 rounded-full bg-[var(--amber)] animate-pulse" />
      )}
      {ETIQUETAS[estado] || estado}
    </span>
  );
}
