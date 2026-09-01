"""Conexión y sesión. La API se conecta siempre con el rol app_riesgo, que
no tiene BYPASSRLS — las políticas de la sección 6 son las que de verdad
controlan el acceso, no el código de aquí (ver advertencia de la sección 7:
"La API nunca se conecta como superusuario").
"""
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from app.config import config

engine = create_engine(config.database_url, pool_pre_ping=True, future=True)


@contextmanager
def conexion_con_usuario(usuario_id: int | None) -> Generator[Connection, None, None]:
    """Abre una conexión y fija app.usuario_id para la transacción, que es
    lo que las políticas RLS de core.usuario_actual() leen. Sin esto, todas
    las políticas de la sección 6 devuelven cero filas."""
    with engine.connect() as conn:
        with conn.begin():
            if usuario_id is not None:
                # SET LOCAL no admite parámetros; set_config(..., true) es
                # su equivalente parametrizable, con el mismo alcance de
                # transacción (sección 6: "SET LOCAL app.usuario_id = '42'").
                conn.execute(text("SELECT set_config('app.usuario_id', :uid, true)"), {"uid": str(usuario_id)})
            yield conn


@contextmanager
def obtener_conexion_sin_usuario() -> Generator[Connection, None, None]:
    """Solo para el flujo de login, antes de tener un usuario autenticado.
    Postgres seguirá aplicando RLS; core.usuario_actual() será NULL y las
    políticas basadas en core.puede(...) devolverán false, pero login lee
    core.usuario directamente por correo, tabla sin RLS habilitado."""
    with engine.connect() as conn:
        with conn.begin():
            yield conn
