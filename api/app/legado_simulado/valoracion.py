"""Simulación de legado/valoracion.py. Firma y columnas: DECISIONES.md §1."""
import numpy as np
import pandas as pd


def calcular_valoracion(posiciones: pd.DataFrame, precios: pd.DataFrame) -> pd.DataFrame:
    if posiciones.empty:
        return pd.DataFrame(columns=[
            "portafolio", "instrumento_cod", "emisor_cod", "nominal", "precio_usado",
            "valor_mercado", "valor_causado", "duracion", "moneda", "metricas_extra",
        ])

    precios_por_instrumento = (
        precios.dropna(subset=["instrumento_cod"])
        .drop_duplicates(subset=["instrumento_cod"], keep="last")
        .set_index("instrumento_cod")["precio_limpio"]
    )

    filas = []
    for _, pos in posiciones.iterrows():
        nominal = float(pos["nominal"] or 0)
        precio = precios_por_instrumento.get(pos["instrumento_cod"])
        sin_precio = precio is None or (isinstance(precio, float) and np.isnan(precio))
        precio_usado = float(precio) if not sin_precio else 0.0
        valor_mercado = nominal * (precio_usado / 100.0)
        valor_causado = float(pos.get("costo_amortizado") or nominal)

        filas.append({
            "portafolio": pos["portafolio"],
            "instrumento_cod": pos["instrumento_cod"],
            "emisor_cod": pos.get("emisor_cod"),
            "nominal": nominal,
            "precio_usado": precio_usado,
            "valor_mercado": round(valor_mercado, 4),
            "valor_causado": round(valor_causado, 4),
            "duracion": None,
            "moneda": pos.get("moneda") or "COP",
            "metricas_extra": {"sin_precio": True} if sin_precio else None,
        })

    return pd.DataFrame(filas)
