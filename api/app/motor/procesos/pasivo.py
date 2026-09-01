from app.motor.io import escribir_resultado, leer_insumo

# Cambia a `from legado.pasivo import calcular_pasivo` cuando llegue el
# código real (ver DECISIONES.md, decisión 2).
from app.legado_simulado.pasivo import calcular_pasivo

TASA_DESCUENTO_DEFECTO = 0.095  # 9.5% — solo para el legado simulado; el
# valor real lo define el código legado o el parámetro de la corrida.


def ejecutar(conn, fecha_datos, corrida_id: int, parametros: dict) -> int:
    flujos = leer_insumo(conn, "staging.flujo_pasivo", fecha_datos)

    tasa_descuento = parametros.get("tasa_descuento", TASA_DESCUENTO_DEFECTO)

    resultado = calcular_pasivo(flujos, tasa_descuento, fecha_datos)

    return escribir_resultado(conn, "res.pasivo", resultado, corrida_id, fecha_datos)
