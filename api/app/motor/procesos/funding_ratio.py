import pandas as pd

from app.motor.ejecutor import corrida_vigente
from app.motor.io import escribir_resultado, leer_resultado

# Cambia a `from legado.funding import calcular_funding_ratio` cuando
# llegue el código real (ver DECISIONES.md, decisión 2).
from app.legado_simulado.funding import calcular_funding_ratio


def ejecutar(conn, fecha_datos, corrida_id: int, parametros: dict) -> int:
    c_act = corrida_vigente(conn, "valoracion", fecha_datos)
    c_pas = corrida_vigente(conn, "pasivo", fecha_datos)
    if not c_act or not c_pas:
        raise ValueError("Funding ratio requiere valoración y pasivo ejecutados para esta fecha.")

    activos = leer_resultado(conn, "res.valoracion", c_act)
    pasivos = leer_resultado(conn, "res.pasivo", c_pas)

    ratio, superavit = calcular_funding_ratio(activos, pasivos)

    salida = pd.DataFrame([{
        "valor_activos": float(activos["valor_mercado"].sum()) if not activos.empty else 0.0,
        "valor_pasivos": float(pasivos["valor_presente"].sum()) if not pasivos.empty else 0.0,
        "ratio": ratio,
        "superavit_deficit": superavit,
        "corrida_activos": c_act,
        "corrida_pasivos": c_pas,
    }])
    return escribir_resultado(conn, "res.funding_ratio", salida, corrida_id, fecha_datos)
