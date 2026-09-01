"""Hash de contraseñas, tokens de sesión y dependencias de FastAPI para
autenticación y autorización (sección 7).

La autorización tiene dos capas, deliberadamente redundantes:
- Aquí se verifica el permiso antes de intentar la acción, para poder
  devolver un mensaje claro ("no tiene permiso para publicar valoración").
- En Postgres, las políticas RLS (migración 006/009) son las que de verdad
  deciden qué filas se pueden leer, incluso si este chequeo tuviera un error.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import config
from app.db import conexion_con_usuario


def hash_clave(clave_plana: str) -> str:
    return bcrypt.hashpw(clave_plana.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verificar_clave(clave_plana: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(clave_plana.encode("utf-8"), hash_guardado.encode("utf-8"))


def validar_fortaleza_clave(clave_plana: str) -> str | None:
    if len(clave_plana) < config.clave_min_longitud:
        return f"La contraseña debe tener al menos {config.clave_min_longitud} caracteres."
    return None


@dataclass
class UsuarioSesion:
    id: int
    correo: str
    nombre: str
    rol: str


def crear_token(usuario_id: int) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + timedelta(hours=config.jwt_horas_vigencia)).timestamp()),
    }
    return jwt.encode(payload, config.secreto_jwt, algorithm="HS256")


def _decodificar_token(token: str) -> int:
    try:
        payload = jwt.decode(token, config.secreto_jwt, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "sesion_expirada", "mensaje": "La sesión expiró. Ingrese de nuevo.", "detalle": {}},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_invalido", "mensaje": "La sesión no es válida. Ingrese de nuevo.", "detalle": {}},
        )
    return int(payload["sub"])


def _extraer_token(request: Request) -> str:
    encabezado = request.headers.get("Authorization", "")
    if not encabezado.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "sin_token", "mensaje": "Debe iniciar sesión.", "detalle": {}},
        )
    return encabezado.removeprefix("Bearer ").strip()


def usuario_actual(request: Request) -> UsuarioSesion:
    """Dependencia base: exige un token válido y un usuario activo, y deja
    la sesión disponible para el resto del request."""
    token = _extraer_token(request)
    usuario_id = _decodificar_token(token)

    with conexion_con_usuario(usuario_id) as conn:
        fila = conn.execute(
            text("SELECT id, correo, nombre, rol::text, activo FROM core.usuario WHERE id = :id"),
            {"id": usuario_id},
        ).mappings().first()

    if fila is None or not fila["activo"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "usuario_inactivo", "mensaje": "El usuario no existe o está inactivo.", "detalle": {}},
        )

    return UsuarioSesion(id=fila["id"], correo=fila["correo"], nombre=fila["nombre"], rol=fila["rol"])


def requiere_permiso(modulo: str, accion: str):
    """Genera una dependencia que exige un permiso concreto (ver/cargar/
    ejecutar/publicar) sobre un módulo, según la matriz de core.permiso."""

    columna = {
        "ver": "puede_ver",
        "cargar": "puede_cargar",
        "ejecutar": "puede_ejecutar",
        "publicar": "puede_publicar",
    }[accion]

    def dependencia(usuario: UsuarioSesion = Depends(usuario_actual)) -> UsuarioSesion:
        with conexion_con_usuario(usuario.id) as conn:
            permitido = conn.execute(
                text(f"SELECT {columna} FROM core.permiso WHERE rol = :rol AND modulo = :modulo"),
                {"rol": usuario.rol, "modulo": modulo},
            ).scalar()
        if not permitido:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "sin_permiso",
                    "mensaje": f"Su rol ({usuario.rol}) no tiene permiso para {accion} en {modulo}.",
                    "detalle": {"modulo": modulo, "accion": accion},
                },
            )
        return usuario

    return dependencia


def requiere_admin(usuario: UsuarioSesion = Depends(usuario_actual)) -> UsuarioSesion:
    if usuario.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "solo_admin", "mensaje": "Esta acción es solo para administradores.", "detalle": {}},
        )
    return usuario


def _ip_valida(ip: str | None) -> str | None:
    """audit.evento.ip es inet: una IP no parseable (p.ej. el host de
    pruebas de TestClient, o un proxy mal configurado) no debe tumbar la
    petición completa — se guarda NULL en vez de fallar el INSERT."""
    if not ip:
        return None
    import ipaddress

    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        return None


def registrar_evento(conn: Connection, usuario_id: int | None, accion: str, recurso: str | None = None,
                      recurso_id: int | None = None, detalle: dict | None = None, ip: str | None = None) -> None:
    ip = _ip_valida(ip)
    conn.execute(
        text(
            "INSERT INTO audit.evento (usuario_id, accion, recurso, recurso_id, detalle, ip) "
            "VALUES (:usuario_id, :accion, :recurso, :recurso_id, CAST(:detalle AS jsonb), CAST(:ip AS inet))"
        ),
        {
            "usuario_id": usuario_id,
            "accion": accion,
            "recurso": recurso,
            "recurso_id": recurso_id,
            "detalle": _a_json(detalle),
            "ip": ip,
        },
    )


def _a_json(detalle: dict | None) -> str | None:
    import json

    return json.dumps(detalle) if detalle is not None else None


_intentos_recientes: dict[str, list[float]] = {}


def registrar_intento_login(correo: str, exitoso: bool) -> None:
    """Contador en memoria como respaldo del contador en base (core.usuario
    .intentos_fallidos); el de base es la fuente de verdad para el bloqueo
    porque sobrevive a un reinicio del proceso de la API."""
    ahora = time.time()
    ventana = _intentos_recientes.setdefault(correo, [])
    ventana[:] = [t for t in ventana if ahora - t < 900]
    if not exitoso:
        ventana.append(ahora)
