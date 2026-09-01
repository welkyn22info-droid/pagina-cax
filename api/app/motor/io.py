"""Capa de entrada y salida compartida por todos los envoltorios (sección 8).
Ningún envoltorio lee un archivo ni escribe uno: todo pasa por aquí, que
solo habla con Postgres. Esto es lo que reemplaza pd.read_excel/to_excel en
el código legado."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

# tabla.split(".")[-1] -> tipo_insumo en staging.carga. Explícito en vez de
# adivinar con un sufijo "+s": staging.flujo_pasivo no es "flujo_pasivos".
_TIPO_INSUMO_POR_TABLA = {
    "posicion": "posiciones",
    "precio": "precios",
    "flujo_pasivo": "flujos_pasivo",
}


def leer_insumo(conn: Connection, tabla: str, fecha_datos, columnas: list[str] | None = None) -> pd.DataFrame:
    """Devuelve el insumo del día como DataFrame, tomando solo la última
    carga VALIDADA de esa fecha. Reemplaza pd.read_excel en el código legado."""
    nombre_tabla = tabla.split(".")[-1]
    tipo = _TIPO_INSUMO_POR_TABLA.get(nombre_tabla, nombre_tabla)
    cols = ", ".join(columnas) if columnas else "*"
    sql = text(f"""
        SELECT {cols} FROM {tabla} s
        WHERE s.fecha_datos = :fecha
          AND s.carga_id = (
              SELECT c.id FROM staging.carga c
              WHERE c.fecha_datos = :fecha
                AND c.estado = 'VALIDADO'
                AND c.tipo_insumo = :tipo
              ORDER BY c.cargado_en DESC LIMIT 1
          )
    """)
    return pd.read_sql(sql, conn, params={"fecha": fecha_datos, "tipo": tipo})


def leer_resultado(conn: Connection, tabla: str, corrida_id: int) -> pd.DataFrame:
    """Lee el resultado de una corrida previa. Usado por procesos derivados
    como funding ratio, que consume valoración y pasivo."""
    sql = text(f"SELECT * FROM {tabla} WHERE corrida_id = :cid")
    return pd.read_sql(sql, conn, params={"cid": corrida_id})


def escribir_resultado(conn: Connection, tabla: str, df: pd.DataFrame, corrida_id: int, fecha_datos) -> int:
    """Escribe el DataFrame de salida a la tabla de resultados. Estampa
    corrida_id y fecha_datos. Reemplaza to_excel en el código legado.

    Usa los tipos reales de la tabla destino (reflejados con el inspector
    de SQLAlchemy) en vez de dejar que pandas los adivine: una columna
    completamente None —como duracion cuando el legado no la calcula—
    pandas la infiere como texto, y Postgres rechaza escribirla en una
    columna numeric. El tipo reflejado (numeric, jsonb, etc.) es siempre
    el correcto porque viene de la tabla misma."""
    if df.empty:
        return 0
    salida = df.copy()
    salida["corrida_id"] = corrida_id
    salida["fecha_datos"] = fecha_datos
    esquema, nombre = tabla.split(".")

    columnas_tabla = inspect(conn).get_columns(nombre, schema=esquema)
    tipos_reflejados = {c["name"]: c["type"] for c in columnas_tabla}
    dtype = {col: tipos_reflejados[col] for col in salida.columns if col in tipos_reflejados}

    salida.to_sql(nombre, conn, schema=esquema, if_exists="append", index=False, dtype=dtype or None)
    return len(salida)
