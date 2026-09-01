"""Valida antes de escribir: falta de columna obligatoria o filas no
convertibles rechazan la carga completa, con el detalle por fila —
no se inserta nada (sección 9)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.ingesta.esquemas import EsquemaInsumo
from app.ingesta.lector import ResultadoLectura, _parsear_fecha, _parsear_numero_colombiano


@dataclass
class ResultadoValidacion:
    aceptado: bool
    df_validado: pd.DataFrame | None = None
    filas_validas: int = 0
    columnas_faltantes: list[str] = field(default_factory=list)
    errores_por_fila: list[dict] = field(default_factory=list)

    def detalle_error(self) -> dict | None:
        if self.aceptado:
            return None
        return {
            "columnas_faltantes": self.columnas_faltantes,
            "errores": self.errores_por_fila[:200],  # el mensaje debe ser legible, no un volcado completo
            "total_errores": len(self.errores_por_fila),
        }

    def mensaje(self, nombre_archivo: str, encabezados_originales: list[str]) -> str:
        if self.aceptado:
            return f"Carga aceptada: {self.filas_validas} filas válidas."
        partes = [f"Carga rechazada: {nombre_archivo}", ""]
        for col in self.columnas_faltantes:
            partes.append(f"  Falta la columna obligatoria {col}.")
        if self.columnas_faltantes:
            partes.append(f"  Encabezados encontrados: {', '.join(encabezados_originales)}")
        for err in self.errores_por_fila[:20]:
            partes.append(f"  Fila {err['fila']}: {err['motivo']} (columna {err['columna']})")
        if len(self.errores_por_fila) > 20:
            partes.append(f"  ... y {len(self.errores_por_fila) - 20} errores más.")
        partes.append("")
        partes.append("  No se cargó ninguna fila.")
        return "\n".join(partes)


def validar(lectura: ResultadoLectura, esquema: EsquemaInsumo) -> ResultadoValidacion:
    df = lectura.df.copy()

    columnas_faltantes = [
        c.destino for c in esquema.columnas
        if c.obligatoria and df[c.destino].isna().all() and len(df) > 0
    ]
    if columnas_faltantes:
        return ResultadoValidacion(aceptado=False, columnas_faltantes=columnas_faltantes)

    if len(df) == 0:
        return ResultadoValidacion(
            aceptado=False,
            errores_por_fila=[{"fila": 0, "columna": "(archivo)", "motivo": "El archivo no tiene filas de datos."}],
        )

    errores: list[dict] = []
    for columna in esquema.columnas:
        for idx, valor in df[columna.destino].items():
            vacio = valor is None or (isinstance(valor, str) and valor.strip() == "") or (
                isinstance(valor, float) and pd.isna(valor)
            )
            if vacio:
                if columna.obligatoria:
                    errores.append({
                        "fila": idx + 1, "columna": columna.destino,
                        "motivo": "Falta un valor obligatorio",
                    })
                continue
            try:
                if columna.tipo == "numero":
                    df.at[idx, columna.destino] = _parsear_numero_colombiano(valor)
                elif columna.tipo == "fecha":
                    df.at[idx, columna.destino] = _parsear_fecha(valor)
                else:
                    df.at[idx, columna.destino] = str(valor).strip()
            except ValueError as exc:
                errores.append({"fila": idx + 1, "columna": columna.destino, "motivo": str(exc)})

    if errores:
        return ResultadoValidacion(aceptado=False, errores_por_fila=errores)

    return ResultadoValidacion(aceptado=True, df_validado=df, filas_validas=len(df))
