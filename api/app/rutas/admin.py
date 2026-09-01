import secrets
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from app.db import conexion_con_usuario
from app.seguridad import (
    UsuarioSesion,
    hash_clave,
    registrar_evento,
    requiere_admin,
    usuario_actual,
    validar_fortaleza_clave,
)

router = APIRouter(tags=["admin"])


def _error(codigo: int, error: str, mensaje: str, detalle: dict | None = None) -> HTTPException:
    return HTTPException(status_code=codigo, detail={"error": error, "mensaje": mensaje, "detalle": detalle or {}})


@router.get("/usuarios")
def directorio_usuarios(usuario: UsuarioSesion = Depends(usuario_actual)):
    """Directorio mínimo (id, nombre, correo, rol) para cualquier usuario
    autenticado — lo necesita quien publica (revisor/admin) para elegir
    destinatarios (sección 13). /admin/usuarios trae más detalle pero es
    solo-admin; este endpoint es el que puede usar cualquier rol."""
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text("SELECT id, correo, nombre, rol::text FROM core.usuario WHERE activo ORDER BY nombre")
        ).mappings().all()
    return [dict(f) for f in filas]


@router.get("/admin/usuarios")
def listar_usuarios(usuario: UsuarioSesion = Depends(requiere_admin)):
    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                "SELECT id, correo, nombre, rol::text, activo, debe_cambiar_clave, ultimo_acceso, creado_en "
                "FROM core.usuario ORDER BY nombre"
            )
        ).mappings().all()
    return [dict(f) for f in filas]


class UsuarioEntrada(BaseModel):
    correo: EmailStr
    nombre: str
    rol: str


ROLES_VALIDOS = ("admin", "analista", "revisor", "consulta")


@router.post("/admin/usuarios")
def crear_usuario(entrada: UsuarioEntrada, usuario: UsuarioSesion = Depends(requiere_admin)):
    if entrada.rol not in ROLES_VALIDOS:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "rol_invalido", f"rol debe ser uno de {ROLES_VALIDOS}.")

    clave_temporal = secrets.token_urlsafe(9)  # 12 caracteres, cumple el mínimo de la sección 7

    with conexion_con_usuario(usuario.id) as conn:
        existe = conn.execute(
            text("SELECT 1 FROM core.usuario WHERE correo = :correo"), {"correo": entrada.correo.lower()}
        ).first()
        if existe:
            raise _error(status.HTTP_409_CONFLICT, "correo_duplicado", "Ya existe un usuario con ese correo.")

        usuario_id = conn.execute(
            text(
                "INSERT INTO core.usuario (correo, nombre, hash_clave, rol, debe_cambiar_clave) "
                "VALUES (:correo, :nombre, :hash, :rol, true) RETURNING id"
            ),
            {"correo": entrada.correo.lower(), "nombre": entrada.nombre, "hash": hash_clave(clave_temporal), "rol": entrada.rol},
        ).scalar_one()
        registrar_evento(conn, usuario.id, "alta_usuario", "core.usuario", usuario_id, {"rol": entrada.rol})

    # La clave temporal se devuelve una sola vez, en la respuesta, para que
    # el admin la comunique fuera de banda; nunca queda en el log ni en auditoría.
    return {"usuario_id": usuario_id, "clave_temporal": clave_temporal}


class UsuarioActualizacion(BaseModel):
    rol: str | None = None
    activo: bool | None = None


@router.patch("/admin/usuarios/{usuario_id}")
def actualizar_usuario(usuario_id: int, entrada: UsuarioActualizacion, usuario: UsuarioSesion = Depends(requiere_admin)):
    if entrada.rol is not None and entrada.rol not in ROLES_VALIDOS:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "rol_invalido", f"rol debe ser uno de {ROLES_VALIDOS}.")

    campos, parametros = [], {"id": usuario_id}
    if entrada.rol is not None:
        campos.append("rol = :rol")
        parametros["rol"] = entrada.rol
    if entrada.activo is not None:
        campos.append("activo = :activo")
        parametros["activo"] = entrada.activo
    if not campos:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "sin_cambios", "No se envió ningún campo para actualizar.")

    with conexion_con_usuario(usuario.id) as conn:
        resultado = conn.execute(text(f"UPDATE core.usuario SET {', '.join(campos)} WHERE id = :id"), parametros)
        if resultado.rowcount == 0:
            raise _error(status.HTTP_404_NOT_FOUND, "no_encontrado", "El usuario no existe.")
        registrar_evento(conn, usuario.id, "modificacion_usuario", "core.usuario", usuario_id, entrada.model_dump(exclude_none=True))

    return {"mensaje": "Usuario actualizado."}


@router.get("/auditoria")
def auditoria(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    usuario_id: int | None = None,
    usuario: UsuarioSesion = Depends(requiere_admin),
):
    condiciones, parametros = [], {}
    if desde:
        condiciones.append("ocurrido_en >= :desde")
        parametros["desde"] = desde
    if hasta:
        condiciones.append("ocurrido_en <= :hasta")
        parametros["hasta"] = hasta
    if usuario_id:
        condiciones.append("usuario_id = :usuario_id")
        parametros["usuario_id"] = usuario_id
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                f"SELECT e.id, e.usuario_id, u.nombre AS usuario_nombre, e.accion, e.recurso, "
                f"e.recurso_id, e.detalle, e.ip, e.ocurrido_en "
                f"FROM audit.evento e LEFT JOIN core.usuario u ON u.id = e.usuario_id "
                f"{where} ORDER BY e.ocurrido_en DESC LIMIT 500"
            ),
            parametros,
        ).mappings().all()
    return [dict(f) for f in filas]


@router.get("/exportar/{recurso}")
def exportar(recurso: str, fecha: date, usuario: UsuarioSesion = Depends(usuario_actual)):
    """Exporta la vista actual a Excel (sección 11: la plataforma reemplaza
    el correo, no la necesidad ocasional de un archivo para un regulador o
    comité). Toda exportación queda registrada en auditoría."""
    from io import BytesIO

    import pandas as pd
    from fastapi.responses import StreamingResponse

    from app.motor.ejecutor import corrida_vigente

    tablas = {
        "valoracion": ("res.valoracion", "valoracion"),
        "pasivo": ("res.pasivo", "pasivo"),
        "cupos": ("res.consumo_cupo", "cupos"),
        "funding-ratio": ("res.funding_ratio", "funding_ratio"),
    }
    if recurso not in tablas:
        raise _error(status.HTTP_404_NOT_FOUND, "recurso_desconocido", f"'{recurso}' no se puede exportar.")

    tabla, proceso = tablas[recurso]
    with conexion_con_usuario(usuario.id) as conn:
        corrida_id = corrida_vigente(conn, proceso, fecha)
        df = pd.read_sql(text(f"SELECT * FROM {tabla} WHERE corrida_id = :cid"), conn, params={"cid": corrida_id}) \
            if corrida_id else pd.DataFrame()
        registrar_evento(conn, usuario.id, "exportacion", tabla, corrida_id, {"fecha": str(fecha), "formato": "xlsx"})

    buffer = BytesIO()
    df.to_excel(buffer, index=False, sheet_name=recurso[:31])
    buffer.seek(0)
    nombre = f"{recurso}_{fecha.isoformat()}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
