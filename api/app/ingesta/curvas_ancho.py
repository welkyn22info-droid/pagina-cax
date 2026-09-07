"""Detecta y pivotea el formato ancho de curvas (una columna por fecha:
Curva;Plazo en días;1/08/2026;2/08/2026;...) a filas largas por fecha —
mismo problema que resuelve operacion/cargar_curvas_historico.py, pero
llamado desde el endpoint de carga (app/rutas/cargas.py) en vez de un
script aparte, para que se pueda subir desde el panel web (decisión 22)."""
from __future__ import annotations

import io

import pandas as pd

from app.ingesta.lector import _detectar_separador, _normalizar_encabezado

_ALIAS_CURVA = {_normalizar_encabezado(a) for a in ["CURVA", "TIPO_CURVA"]}
_ALIAS_NODO = {_normalizar_encabezado(a) for a in ["NODO", "PLAZO EN DIAS", "PLAZO"]}


def es_formato_ancho(encabezados: list[str]) -> bool:
    """Ancho: hay una columna de curva, una de nodo/plazo, y al menos dos
    columnas más que parecen fecha (dd/mm/aaaa). El formato largo normal
    (Curva;Nodo;Valor) tiene exactamente 3 columnas y no matchea esto."""
    normalizados = [_normalizar_encabezado(c) for c in encabezados]
    tiene_curva = any(c in _ALIAS_CURVA for c in normalizados)
    tiene_nodo = any(c in _ALIAS_NODO for c in normalizados)
    columnas_fecha = [c for c in encabezados if not pd.isna(pd.to_datetime(c, dayfirst=True, errors="coerce"))]
    return tiene_curva and tiene_nodo and len(columnas_fecha) >= 2


def pivotear_curvas_ancho(contenido: bytes) -> dict[str, pd.DataFrame]:
    """Devuelve {fecha_iso: DataFrame(curva, nodo, valor)}, uno por cada
    columna de fecha del archivo ancho."""
    separador = _detectar_separador(contenido)
    texto = contenido.decode("utf-8-sig", errors="ignore")
    df = pd.read_csv(io.StringIO(texto), sep=separador, engine="python", dtype=str, skipinitialspace=True)

    mapa = {_normalizar_encabezado(str(c)): c for c in df.columns}
    col_curva = next(mapa[c] for c in mapa if c in _ALIAS_CURVA)
    col_nodo = next(mapa[c] for c in mapa if c in _ALIAS_NODO)
    columnas_fecha = [c for c in df.columns if c not in (col_curva, col_nodo)]

    largo = df.melt(
        id_vars=[col_curva, col_nodo], value_vars=columnas_fecha, var_name="fecha_original", value_name="valor"
    )
    largo["fecha_iso"] = pd.to_datetime(largo["fecha_original"], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    largo = largo.dropna(subset=["fecha_iso"])

    por_fecha: dict[str, pd.DataFrame] = {}
    for fecha_iso, grupo in largo.groupby("fecha_iso"):
        salida = grupo[[col_curva, col_nodo, "valor"]].rename(
            columns={col_curva: "tipo_curva", col_nodo: "nodo", "valor": "valor"}
        )
        por_fecha[fecha_iso] = salida.reset_index(drop=True)
    return por_fecha
