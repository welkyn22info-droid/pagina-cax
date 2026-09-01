from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.config import config
from app.db import conexion_con_usuario, obtener_conexion_sin_usuario
from app.seguridad import (
    UsuarioSesion,
    crear_token,
    hash_clave,
    registrar_evento,
    usuario_actual,
    validar_fortaleza_clave,
    verificar_clave,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginEntrada(BaseModel):
    correo: str
    clave: str


class LoginSalida(BaseModel):
    token: str
    usuario: dict
    debe_cambiar_clave: bool


class CambiarClaveEntrada(BaseModel):
    clave_actual: str
    clave_nueva: str = Field(min_length=1)


def _error(codigo: int, error: str, mensaje: str, detalle: dict | None = None) -> HTTPException:
    return HTTPException(status_code=codigo, detail={"error": error, "mensaje": mensaje, "detalle": detalle or {}})


@router.post("/login", response_model=LoginSalida)
def login(entrada: LoginEntrada, request: Request):
    ip = request.client.host if request.client else None

    with obtener_conexion_sin_usuario() as conn:
        fila = conn.execute(
            text(
                "SELECT id, correo, nombre, hash_clave, rol::text AS rol, activo, "
                "debe_cambiar_clave, intentos_fallidos, bloqueado_hasta "
                "FROM core.usuario WHERE correo = :correo"
            ),
            {"correo": entrada.correo.strip().lower()},
        ).mappings().first()

        credenciales_invalidas = _error(
            status.HTTP_401_UNAUTHORIZED, "credenciales_invalidas", "Correo o contraseña incorrectos.",
        )

        if fila is None or not fila["activo"]:
            raise credenciales_invalidas

        if fila["bloqueado_hasta"] and fila["bloqueado_hasta"] > datetime.now(timezone.utc):
            raise _error(
                status.HTTP_423_LOCKED,
                "usuario_bloqueado",
                f"Cuenta bloqueada temporalmente por intentos fallidos. Intente después de "
                f"{fila['bloqueado_hasta'].strftime('%H:%M')}.",
            )

        if not verificar_clave(entrada.clave, fila["hash_clave"]):
            nuevos_intentos = fila["intentos_fallidos"] + 1
            bloqueo = None
            if nuevos_intentos >= config.intentos_max_fallidos:
                bloqueo = datetime.now(timezone.utc) + timedelta(minutes=config.bloqueo_minutos)
                nuevos_intentos = 0
            conn.execute(
                text(
                    "UPDATE core.usuario SET intentos_fallidos = :intentos, bloqueado_hasta = :bloqueo "
                    "WHERE id = :id"
                ),
                {"intentos": nuevos_intentos, "bloqueo": bloqueo, "id": fila["id"]},
            )
            registrar_evento(conn, fila["id"], "ingreso_fallido", "usuario", fila["id"], {"ip": ip})
            raise credenciales_invalidas

        conn.execute(
            text(
                "UPDATE core.usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL, "
                "ultimo_acceso = now() WHERE id = :id"
            ),
            {"id": fila["id"]},
        )
        registrar_evento(conn, fila["id"], "ingreso", "usuario", fila["id"], {"ip": ip}, ip)

        token = crear_token(fila["id"])
        return LoginSalida(
            token=token,
            usuario={"id": fila["id"], "correo": fila["correo"], "nombre": fila["nombre"], "rol": fila["rol"]},
            debe_cambiar_clave=fila["debe_cambiar_clave"],
        )


@router.post("/logout")
def logout(usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        registrar_evento(conn, usuario.id, "cierre_sesion", "usuario", usuario.id)
    return {"mensaje": "Sesión cerrada."}


@router.get("/yo")
def yo(usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        permisos = conn.execute(
            text(
                "SELECT modulo, puede_ver, puede_cargar, puede_ejecutar, puede_publicar "
                "FROM core.permiso WHERE rol = :rol"
            ),
            {"rol": usuario.rol},
        ).mappings().all()
    return {
        "id": usuario.id,
        "correo": usuario.correo,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "permisos": [dict(p) for p in permisos],
    }


@router.post("/cambiar-clave")
def cambiar_clave(entrada: CambiarClaveEntrada, usuario: UsuarioSesion = Depends(usuario_actual)):
    error_fortaleza = validar_fortaleza_clave(entrada.clave_nueva)
    if error_fortaleza:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "clave_debil", error_fortaleza)

    with conexion_con_usuario(usuario.id) as conn:
        hash_actual = conn.execute(
            text("SELECT hash_clave FROM core.usuario WHERE id = :id"), {"id": usuario.id}
        ).scalar()
        if not verificar_clave(entrada.clave_actual, hash_actual):
            raise _error(status.HTTP_401_UNAUTHORIZED, "clave_actual_incorrecta", "La contraseña actual no es correcta.")

        conn.execute(
            text(
                "UPDATE core.usuario SET hash_clave = :hash, debe_cambiar_clave = false WHERE id = :id"
            ),
            {"hash": hash_clave(entrada.clave_nueva), "id": usuario.id},
        )
        registrar_evento(conn, usuario.id, "cambio_clave", "usuario", usuario.id)

    return {"mensaje": "Contraseña actualizada."}
