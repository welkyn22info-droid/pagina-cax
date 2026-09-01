from app.motor.io import escribir_resultado, leer_insumo

# Envoltorio delgado: leer, calcular, escribir. Nada más (sección 8).
# Este import es la única línea que cambia cuando llegue el código real a
# api/legado/ (ver DECISIONES.md, decisión 2):
#   from legado.valoracion import calcular_valoracion
from app.legado_simulado.valoracion import calcular_valoracion


def ejecutar(conn, fecha_datos, corrida_id: int, parametros: dict) -> int:
    # 1. Leer — antes era pd.read_excel("posiciones_20260830.xlsx")
    posiciones = leer_insumo(conn, "staging.posicion", fecha_datos)
    precios = leer_insumo(conn, "staging.precio", fecha_datos)

    # 2. Calcular — firma original, intacta
    resultado = calcular_valoracion(posiciones, precios)

    # 3. Escribir — antes era resultado.to_excel("valoracion_20260830.xlsx")
    return escribir_resultado(conn, "res.valoracion", resultado, corrida_id, fecha_datos)
