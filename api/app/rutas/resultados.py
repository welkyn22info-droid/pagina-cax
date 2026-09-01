from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.db import conexion_con_usuario
from app.motor.ejecutor import corrida_vigente
from app.seguridad import UsuarioSesion, usuario_actual

router = APIRouter(prefix="/resultados", tags=["resultados"])


@router.get("/valoracion")
def resultado_valoracion(fecha: date, portafolio: str | None = None, usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        corrida_id = corrida_vigente(conn, "valoracion", fecha)
        if corrida_id is None:
            return {"corrida_id": None, "filas": [], "agregados": None}

        condiciones = "WHERE corrida_id = :cid"
        parametros: dict = {"cid": corrida_id}
        if portafolio:
            condiciones += " AND portafolio = :portafolio"
            parametros["portafolio"] = portafolio

        filas = conn.execute(
            text(
                f"SELECT portafolio, instrumento_cod, emisor_cod, nominal, precio_usado, "
                f"valor_mercado, valor_causado, duracion, moneda, metricas_extra "
                f"FROM res.valoracion {condiciones} ORDER BY valor_mercado DESC LIMIT 5000"
            ),
            parametros,
        ).mappings().all()

        agregados = conn.execute(
            text(
                f"SELECT count(*) AS num_posiciones, sum(valor_mercado) AS valor_total, "
                f"count(*) FILTER (WHERE metricas_extra->>'sin_precio' = 'true') AS sin_precio "
                f"FROM res.valoracion {condiciones}"
            ),
            parametros,
        ).mappings().first()

    return {"corrida_id": corrida_id, "filas": [dict(f) for f in filas], "agregados": dict(agregados)}


@router.get("/pasivo")
def resultado_pasivo(fecha: date, usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        corrida_id = corrida_vigente(conn, "pasivo", fecha)
        if corrida_id is None:
            return {"corrida_id": None, "filas": [], "agregados": None}

        filas = conn.execute(
            text(
                "SELECT concepto, valor_presente, duracion, tasa_descuento, metricas_extra "
                "FROM res.pasivo WHERE corrida_id = :cid ORDER BY valor_presente DESC"
            ),
            {"cid": corrida_id},
        ).mappings().all()
        agregados = conn.execute(
            text("SELECT sum(valor_presente) AS valor_total FROM res.pasivo WHERE corrida_id = :cid"),
            {"cid": corrida_id},
        ).mappings().first()

    return {"corrida_id": corrida_id, "filas": [dict(f) for f in filas], "agregados": dict(agregados)}


@router.get("/funding-ratio")
def resultado_funding_ratio(desde: date, hasta: date, usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                "SELECT fr.corrida_id, fr.fecha_datos, fr.valor_activos, fr.valor_pasivos, fr.ratio, "
                "fr.superavit_deficit, fr.corrida_activos, fr.corrida_pasivos "
                "FROM res.funding_ratio fr "
                "JOIN proc.corrida c ON c.id = fr.corrida_id AND c.estado = 'OK' "
                "WHERE fr.fecha_datos BETWEEN :desde AND :hasta "
                "ORDER BY fr.fecha_datos"
            ),
            {"desde": desde, "hasta": hasta},
        ).mappings().all()
    return {"serie": [dict(f) for f in filas]}
