from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.db import conexion_con_usuario
from app.motor.ejecutor import corrida_vigente
from app.seguridad import UsuarioSesion, registrar_evento, requiere_admin, usuario_actual

router = APIRouter(prefix="/cupos", tags=["cupos"])


def _error(codigo: int, error: str, mensaje: str, detalle: dict | None = None) -> HTTPException:
    return HTTPException(status_code=codigo, detail={"error": error, "mensaje": mensaje, "detalle": detalle or {}})


@router.get("/entidades")
def listar_entidades(tipo: str, usuario: UsuarioSesion = Depends(requiere_admin)):
    """Emisores o contrapartes disponibles para parametrizar un límite
    nuevo — no solo los que ya tienen uno (a diferencia de /cupos/limites,
    que solo trae los límites existentes)."""
    if tipo not in ("emisor", "contraparte"):
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "tipo_invalido", "tipo debe ser 'emisor' o 'contraparte'.")
    tabla = "core.emisor" if tipo == "emisor" else "core.contraparte"
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(text(f"SELECT id, codigo, nombre FROM {tabla} WHERE activo ORDER BY nombre")).mappings().all()
    return [dict(f) for f in filas]


@router.get("/consumo")
def consumo_cupos(fecha: date, estado: str | None = None, usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        corrida_id = corrida_vigente(conn, "cupos", fecha)
        if corrida_id is None:
            return {"corrida_id": None, "filas": []}

        condiciones = "WHERE corrida_id = :cid"
        parametros: dict = {"cid": corrida_id}
        if estado:
            condiciones += " AND estado = :estado"
            parametros["estado"] = estado

        filas = conn.execute(
            text(
                f"SELECT tipo, entidad_id, entidad_nombre, limite_id, valor_limite, valor_expuesto, "
                f"utilizacion, estado, detalle FROM res.consumo_cupo {condiciones} "
                f"ORDER BY utilizacion DESC NULLS LAST"
            ),
            parametros,
        ).mappings().all()

    return {"corrida_id": corrida_id, "filas": [dict(f) for f in filas]}


@router.get("/limites")
def listar_limites(usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                "SELECT lc.id, lc.tipo, lc.entidad_id, "
                "COALESCE(e.nombre, c.nombre) AS entidad_nombre, "
                "COALESCE(e.codigo, c.codigo) AS entidad_codigo, "
                "lc.base, lc.valor_limite, lc.umbral_alerta, lc.vigente_desde, lc.vigente_hasta "
                "FROM core.limite_cupo lc "
                "LEFT JOIN core.emisor e ON lc.tipo = 'emisor' AND e.id = lc.entidad_id "
                "LEFT JOIN core.contraparte c ON lc.tipo = 'contraparte' AND c.id = lc.entidad_id "
                "ORDER BY lc.vigente_desde DESC"
            )
        ).mappings().all()
    return [dict(f) for f in filas]


class LimiteEntrada(BaseModel):
    tipo: str
    entidad_id: int
    base: str
    valor_limite: float
    umbral_alerta: float = 0.80
    vigente_desde: date


@router.post("/limites")
def crear_limite(entrada: LimiteEntrada, usuario: UsuarioSesion = Depends(requiere_admin)):
    if entrada.tipo not in ("emisor", "contraparte"):
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "tipo_invalido", "tipo debe ser 'emisor' o 'contraparte'.")
    if entrada.base not in ("monto", "porcentaje_portafolio"):
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "base_invalida", "base debe ser 'monto' o 'porcentaje_portafolio'.")

    with conexion_con_usuario(usuario.id) as conn:
        # Un límite nuevo no reemplaza al anterior: lo versiona por vigencia
        # (sección 11: "Solo admin. Versiona por vigencia"). El límite
        # anterior cierra su vigencia justo antes de que empiece la nueva.
        conn.execute(
            text(
                "UPDATE core.limite_cupo SET vigente_hasta = CAST(:desde AS date) - 1 "
                "WHERE tipo = :tipo AND entidad_id = :entidad_id AND vigente_hasta IS NULL "
                "AND vigente_desde < :desde"
            ),
            {"tipo": entrada.tipo, "entidad_id": entrada.entidad_id, "desde": entrada.vigente_desde},
        )

        limite_id = conn.execute(
            text(
                "INSERT INTO core.limite_cupo (tipo, entidad_id, base, valor_limite, umbral_alerta, "
                "vigente_desde, creado_por) VALUES (:tipo, :entidad_id, :base, :valor_limite, :umbral, "
                ":desde, :usuario_id) RETURNING id"
            ),
            {
                "tipo": entrada.tipo, "entidad_id": entrada.entidad_id, "base": entrada.base,
                "valor_limite": entrada.valor_limite, "umbral": entrada.umbral_alerta,
                "desde": entrada.vigente_desde, "usuario_id": usuario.id,
            },
        ).scalar_one()

        registrar_evento(
            conn, usuario.id, "cambio_limite", "core.limite_cupo", limite_id,
            {"tipo": entrada.tipo, "entidad_id": entrada.entidad_id, "valor_limite": entrada.valor_limite},
        )

    return {"limite_id": limite_id, "mensaje": "Límite creado."}
