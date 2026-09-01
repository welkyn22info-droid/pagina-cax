from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.db import conexion_con_usuario
from app.motor.registro import PROCESOS
from app.seguridad import UsuarioSesion, registrar_evento, usuario_actual

router = APIRouter(prefix="/publicaciones", tags=["publicaciones"])


def _error(codigo: int, error: str, mensaje: str, detalle: dict | None = None) -> HTTPException:
    return HTTPException(status_code=codigo, detail={"error": error, "mensaje": mensaje, "detalle": detalle or {}})


class PublicarEntrada(BaseModel):
    corrida_id: int
    titulo: str
    comentario: str | None = None
    destinatarios: list[int]


@router.post("")
def publicar(entrada: PublicarEntrada, usuario: UsuarioSesion = Depends(usuario_actual)):
    if not entrada.destinatarios:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "sin_destinatarios", "Debe seleccionar al menos un destinatario.")

    with conexion_con_usuario(usuario.id) as conn:
        corrida = conn.execute(
            text("SELECT proceso, estado::text FROM proc.corrida WHERE id = :id"),
            {"id": entrada.corrida_id},
        ).mappings().first()
        if corrida is None:
            raise _error(status.HTTP_404_NOT_FOUND, "no_encontrada", "La corrida no existe o no tiene permiso para verla.")
        if corrida["estado"] != "OK":
            raise _error(status.HTTP_409_CONFLICT, "corrida_no_valida", "Solo se puede publicar una corrida en estado OK.")

        modulo = PROCESOS[corrida["proceso"]]["modulo"]
        puede = conn.execute(
            text("SELECT puede_publicar FROM core.permiso WHERE rol = :rol AND modulo = :modulo"),
            {"rol": usuario.rol, "modulo": modulo},
        ).scalar()
        if not puede:
            raise _error(status.HTTP_403_FORBIDDEN, "sin_permiso", f"Su rol ({usuario.rol}) no tiene permiso para publicar {modulo}.")

        publicacion_id = conn.execute(
            text(
                "INSERT INTO audit.publicacion (corrida_id, titulo, comentario, publicada_por) "
                "VALUES (:corrida_id, :titulo, :comentario, :usuario_id) RETURNING id"
            ),
            {"corrida_id": entrada.corrida_id, "titulo": entrada.titulo, "comentario": entrada.comentario, "usuario_id": usuario.id},
        ).scalar_one()

        for destinatario_id in set(entrada.destinatarios):
            conn.execute(
                text("INSERT INTO audit.destinatario (publicacion_id, usuario_id) VALUES (:pid, :uid)"),
                {"pid": publicacion_id, "uid": destinatario_id},
            )

        registrar_evento(
            conn, usuario.id, "publicacion", "audit.publicacion", publicacion_id,
            {"corrida_id": entrada.corrida_id, "destinatarios": entrada.destinatarios},
        )

    return {"publicacion_id": publicacion_id, "mensaje": "Publicación creada."}


@router.get("/pendientes")
def pendientes(usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                "SELECT p.id, p.titulo, p.comentario, p.corrida_id, c.proceso, c.fecha_datos, "
                "p.publicada_por, p.publicada_en "
                "FROM audit.publicacion p "
                "JOIN audit.destinatario d ON d.publicacion_id = p.id AND d.usuario_id = :uid AND d.visto_en IS NULL "
                "JOIN proc.corrida c ON c.id = p.corrida_id "
                "ORDER BY p.publicada_en DESC"
            ),
            {"uid": usuario.id},
        ).mappings().all()
    return [dict(f) for f in filas]


@router.post("/{publicacion_id}/acuse")
def registrar_acuse(publicacion_id: int, usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        resultado = conn.execute(
            text(
                "UPDATE audit.destinatario SET visto_en = now() "
                "WHERE publicacion_id = :pid AND usuario_id = :uid AND visto_en IS NULL"
            ),
            {"pid": publicacion_id, "uid": usuario.id},
        )
        if resultado.rowcount:
            registrar_evento(conn, usuario.id, "acuse", "audit.publicacion", publicacion_id)

    return {"mensaje": "Acuse registrado."}


@router.get("/{publicacion_id}/acuses")
def ver_acuses(publicacion_id: int, usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                "SELECT d.usuario_id, u.nombre, u.correo, d.visto_en "
                "FROM audit.destinatario d JOIN core.usuario u ON u.id = d.usuario_id "
                "WHERE d.publicacion_id = :pid ORDER BY u.nombre"
            ),
            {"pid": publicacion_id},
        ).mappings().all()
    if not filas:
        raise _error(status.HTTP_404_NOT_FOUND, "no_encontrada", "La publicación no existe o no tiene permiso para verla.")
    return [dict(f) for f in filas]
