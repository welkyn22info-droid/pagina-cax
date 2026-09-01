import pandas as pd
from sqlalchemy import text

from app.motor.ejecutor import corrida_vigente
from app.motor.io import escribir_resultado, leer_insumo, leer_resultado

# Cambia a `from legado.cupos import calcular_consumo_cupo` cuando llegue
# el código real (ver DECISIONES.md, decisión 2).
from app.legado_simulado.cupos import calcular_consumo_cupo


def ejecutar(conn, fecha_datos, corrida_id: int, parametros: dict) -> int:
    c_val = corrida_vigente(conn, "valoracion", fecha_datos)
    if not c_val:
        raise ValueError("Cupos requiere valoración ejecutada para esta fecha.")

    posiciones = leer_insumo(conn, "staging.posicion", fecha_datos)
    valoracion = leer_resultado(conn, "res.valoracion", c_val)
    limites = _leer_limites_vigentes(conn, fecha_datos)
    entidades = _leer_entidades(conn)

    resultado = calcular_consumo_cupo(posiciones, valoracion, limites, entidades)
    if resultado.empty:
        return 0

    return escribir_resultado(conn, "res.consumo_cupo", resultado, corrida_id, fecha_datos)


def _leer_limites_vigentes(conn, fecha_datos) -> pd.DataFrame:
    """El límite aplicable es el vigente A LA FECHA DE DATOS, no el vigente
    hoy (sección 14) — así un recálculo de una fecha pasada usa el límite
    que regía entonces, aunque hoy exista uno más nuevo."""
    sql = text("""
        SELECT DISTINCT ON (lc.tipo, lc.entidad_id)
               lc.tipo, lc.entidad_id, lc.id AS limite_id, lc.base,
               lc.valor_limite, lc.umbral_alerta,
               COALESCE(e.codigo, c.codigo) AS codigo_entidad
        FROM core.limite_cupo lc
        LEFT JOIN core.emisor e ON lc.tipo = 'emisor' AND e.id = lc.entidad_id
        LEFT JOIN core.contraparte c ON lc.tipo = 'contraparte' AND c.id = lc.entidad_id
        WHERE lc.vigente_desde <= :fecha
          AND (lc.vigente_hasta IS NULL OR lc.vigente_hasta >= :fecha)
        ORDER BY lc.tipo, lc.entidad_id, lc.vigente_desde DESC
    """)
    return pd.read_sql(sql, conn, params={"fecha": fecha_datos})


def _leer_entidades(conn) -> pd.DataFrame:
    """Maestro de emisores y contrapartes (id, código, nombre) para poder
    resolver entidad_id y el nombre real incluso cuando la entidad no
    tiene límite parametrizado (sección 14: se reporta igual, con la
    marca de "sin límite", nunca se omite)."""
    sql = text("""
        SELECT 'emisor' AS tipo, id AS entidad_id, codigo, nombre FROM core.emisor
        UNION ALL
        SELECT 'contraparte' AS tipo, id AS entidad_id, codigo, nombre FROM core.contraparte
    """)
    return pd.read_sql(sql, conn)
