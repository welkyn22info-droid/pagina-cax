"""Consulta de curvas de mercado para graficar (decisión 18). Es lectura
directa de staging.curva_nodo — no hay proceso ni cálculo: el insumo ya es
el dato final."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.db import conexion_con_usuario
from app.seguridad import UsuarioSesion, usuario_actual

router = APIRouter(prefix="/curvas", tags=["curvas"])


@router.get("/tipos")
def tipos_de_curva(usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                "SELECT DISTINCT cn.tipo_curva FROM staging.curva_nodo cn "
                "JOIN staging.carga c ON c.id = cn.carga_id "
                "WHERE c.estado = 'VALIDADO' AND c.anulada_en IS NULL "
                "ORDER BY cn.tipo_curva"
            )
        ).scalars().all()
    return list(filas)


@router.get("/fechas")
def fechas_disponibles(tipo_curva: str, usuario: UsuarioSesion = Depends(usuario_actual)):
    """Fechas con datos vigentes de esa curva, más recientes primero — para
    poblar el selector de comparación (sección nueva: por defecto se ve la
    última, y de ahí se eligen más para comparar)."""
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                "SELECT DISTINCT cn.fecha_datos FROM staging.curva_nodo cn "
                "JOIN staging.carga c ON c.id = cn.carga_id "
                "WHERE cn.tipo_curva = :tipo AND c.estado = 'VALIDADO' AND c.anulada_en IS NULL "
                "ORDER BY cn.fecha_datos DESC"
            ),
            {"tipo": tipo_curva},
        ).scalars().all()
    return [str(f) for f in filas]


@router.get("")
def leer_curva(tipo_curva: str, fechas: str, usuario: UsuarioSesion = Depends(usuario_actual)):
    """`fechas` es una lista separada por comas (2026-08-01,2026-08-31):
    varias fechas a la vez es exactamente para poder comparar cómo se movió
    la curva entre un día y otro en la misma gráfica."""
    lista_fechas = [f.strip() for f in fechas.split(",") if f.strip()]
    if not lista_fechas:
        return {"series": []}

    with conexion_con_usuario(usuario.id) as conn:
        series = []
        for fecha_iso in lista_fechas:
            try:
                fecha = date.fromisoformat(fecha_iso)
            except ValueError:
                continue
            # Toma la última carga VALIDADA y no anulada de esa fecha —
            # mismo criterio que leer_insumo del motor (app/motor/io.py).
            carga_id = conn.execute(
                text(
                    "SELECT id FROM staging.carga WHERE tipo_insumo = 'curvas' AND fecha_datos = :fecha "
                    "AND estado = 'VALIDADO' AND anulada_en IS NULL ORDER BY cargado_en DESC LIMIT 1"
                ),
                {"fecha": fecha},
            ).scalar()
            if carga_id is None:
                continue
            puntos = conn.execute(
                text(
                    "SELECT nodo, valor FROM staging.curva_nodo "
                    "WHERE carga_id = :carga_id AND tipo_curva = :tipo ORDER BY nodo"
                ),
                {"carga_id": carga_id, "tipo": tipo_curva},
            ).mappings().all()
            series.append({
                "fecha_datos": fecha_iso,
                "carga_id": carga_id,
                "puntos": [{"nodo": p["nodo"], "valor": float(p["valor"])} for p in puntos],
            })

    return {"series": series}
