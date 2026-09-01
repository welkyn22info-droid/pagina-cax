"""Simulación de legado/pasivo.py. Firma y columnas: DECISIONES.md §1."""
import pandas as pd


def calcular_pasivo(flujos: pd.DataFrame, tasa_descuento: float, fecha_valoracion) -> pd.DataFrame:
    if flujos.empty:
        return pd.DataFrame(columns=["concepto", "valor_presente", "duracion", "tasa_descuento", "metricas_extra"])

    tasa_diaria = (1 + tasa_descuento) ** (1 / 365) - 1

    filas = []
    for concepto, grupo in flujos.groupby(flujos["concepto"].fillna("(sin concepto)")):
        vp_total = 0.0
        vp_x_dias = 0.0
        for _, flujo in grupo.iterrows():
            dias = (pd.Timestamp(flujo["fecha_flujo"]) - pd.Timestamp(fecha_valoracion)).days
            dias = max(dias, 0)
            factor = 1 / ((1 + tasa_diaria) ** dias)
            vp = float(flujo["monto"]) * factor
            vp_total += vp
            vp_x_dias += vp * dias

        duracion_anios = (vp_x_dias / vp_total / 365) if vp_total else None
        filas.append({
            "concepto": concepto,
            "valor_presente": round(vp_total, 4),
            "duracion": round(duracion_anios, 6) if duracion_anios is not None else None,
            "tasa_descuento": tasa_descuento,
            "metricas_extra": None,
        })

    return pd.DataFrame(filas)
