"""Simulación de legado/funding.py. Firma tomada literalmente del ejemplo
de la sección 8 de la especificación."""
import pandas as pd


def calcular_funding_ratio(activos: pd.DataFrame, pasivos: pd.DataFrame) -> tuple[float, float]:
    valor_activos = float(activos["valor_mercado"].sum()) if not activos.empty else 0.0
    valor_pasivos = float(pasivos["valor_presente"].sum()) if not pasivos.empty else 0.0

    if valor_pasivos == 0:
        ratio = float("inf") if valor_activos > 0 else 0.0
    else:
        ratio = valor_activos / valor_pasivos

    superavit = valor_activos - valor_pasivos
    return round(ratio, 6), round(superavit, 4)
