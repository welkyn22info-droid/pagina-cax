"""Definición declarativa de cada tipo de insumo (sección 9). Agregar un
insumo nuevo es agregar una entrada a ESQUEMAS — nada de código disperso."""
from dataclasses import dataclass, field


@dataclass
class Columna:
    destino: str                  # nombre en la tabla de staging
    origen: list[str]             # nombres aceptados en el archivo (antes de normalizar)
    tipo: str                     # 'texto' | 'numero' | 'fecha'
    obligatoria: bool = True


@dataclass
class EsquemaInsumo:
    tipo: str
    tabla: str
    columnas: list[Columna]
    separador: str | None = None      # para TXT; None = autodetectar
    hoja: str | int = 0               # para Excel
    filas_encabezado: int = 0
    decimal: str = "."


ESQUEMAS: dict[str, EsquemaInsumo] = {
    "posiciones": EsquemaInsumo(
        tipo="posiciones",
        tabla="staging.posicion",
        separador="|",
        columnas=[
            Columna("portafolio",       ["PORTAFOLIO", "Portafolio", "PORT"], "texto"),
            Columna("instrumento_cod",  ["NEMOTECNICO", "INSTRUMENTO", "ISIN"], "texto"),
            Columna("emisor_cod",       ["EMISOR", "COD_EMISOR"], "texto", False),
            Columna("contraparte_cod",  ["CONTRAPARTE", "COD_CONTRAPARTE"], "texto", False),
            Columna("nominal",          ["NOMINAL", "VALOR_NOMINAL"], "numero"),
            Columna("cantidad",         ["CANTIDAD", "UNIDADES"], "numero", False),
            Columna("costo_amortizado", ["COSTO_AMORTIZADO", "COSTO"], "numero", False),
            Columna("moneda",           ["MONEDA", "CURRENCY"], "texto", False),
        ],
    ),
    "precios": EsquemaInsumo(
        tipo="precios",
        tabla="staging.precio",
        separador="|",
        columnas=[
            Columna("instrumento_cod", ["NEMOTECNICO", "INSTRUMENTO", "ISIN"], "texto"),
            Columna("precio_limpio",   ["PRECIO_LIMPIO", "PRECIO"], "numero"),
            Columna("precio_sucio",    ["PRECIO_SUCIO"], "numero", False),
            Columna("tasa",            ["TASA", "TIR"], "numero", False),
            Columna("fuente",          ["FUENTE", "PROVEEDOR"], "texto", False),
        ],
    ),
    "flujos_pasivo": EsquemaInsumo(
        tipo="flujos_pasivo",
        tabla="staging.flujo_pasivo",
        separador="|",
        columnas=[
            Columna("concepto",    ["CONCEPTO"], "texto", False),
            Columna("fecha_flujo", ["FECHA_FLUJO", "FECHA_PAGO"], "fecha"),
            Columna("monto",       ["MONTO", "VALOR"], "numero"),
            Columna("moneda",      ["MONEDA", "CURRENCY"], "texto", False),
        ],
    ),
}
