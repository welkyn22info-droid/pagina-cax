"use client";

export default function SelectorFecha({
  valor,
  onCambiar,
  etiqueta = "Fecha de datos",
}: {
  valor: string;
  onCambiar: (fecha: string) => void;
  etiqueta?: string;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-[var(--ink-soft)]">{etiqueta}</span>
      <input
        type="date"
        value={valor}
        onChange={(e) => onCambiar(e.target.value)}
        className="border border-[var(--rule)] rounded-md px-2.5 py-1.5 text-sm cifra focus:outline-none focus:ring-2 focus:ring-[var(--teal)]"
      />
    </label>
  );
}
