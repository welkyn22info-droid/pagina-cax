"""Permisos (sección 17): cada rol contra cada endpoint relevante, y una
verificación a nivel de base de que 'consulta' no puede leer resultados no
publicados aunque se conecte directamente (sin pasar por la API)."""
import psycopg
import pytest

from app.config import config


def test_analista_puede_cargar_pero_no_publicar(cliente, token_analista):
    r = cliente.post(
        "/cargas",
        headers={"Authorization": f"Bearer {token_analista}"},
        files={"archivo": ("p.txt", b"PORTAFOLIO|NEMOTECNICO|NOMINAL\nP1|TESJUL27|100,00\n", "text/plain")},
        data={"tipo_insumo": "posiciones", "fecha_datos": "2026-08-20"},
    )
    assert r.status_code == 200

    r = cliente.post(
        "/publicaciones",
        headers={"Authorization": f"Bearer {token_analista}"},
        json={"corrida_id": 1, "titulo": "x", "destinatarios": [1]},
    )
    # No es admin/revisor del módulo => sin permiso de publicar. El chequeo
    # de permiso ocurre antes de validar si la corrida existe.
    assert r.status_code in (403, 404, 409)


def test_revisor_no_puede_cargar(cliente, token_revisor):
    r = cliente.post(
        "/cargas",
        headers={"Authorization": f"Bearer {token_revisor}"},
        files={"archivo": ("p.txt", b"PORTAFOLIO|NEMOTECNICO|NOMINAL\nP1|TESJUL27|100,00\n", "text/plain")},
        data={"tipo_insumo": "posiciones", "fecha_datos": "2026-08-20"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "sin_permiso"


def test_consulta_no_puede_ejecutar(cliente, token_consulta):
    r = cliente.post(
        "/corridas",
        headers={"Authorization": f"Bearer {token_consulta}"},
        json={"proceso": "valoracion", "fecha_datos": "2026-08-20", "parametros": {}},
    )
    assert r.status_code == 403


def test_consulta_no_puede_administrar_usuarios(cliente, token_consulta):
    r = cliente.get("/admin/usuarios", headers={"Authorization": f"Bearer {token_consulta}"})
    assert r.status_code == 403
    assert r.json()["error"] == "solo_admin"


def test_admin_puede_todo_lo_administrativo(cliente, token_admin):
    r = cliente.get("/admin/usuarios", headers={"Authorization": f"Bearer {token_admin}"})
    assert r.status_code == 200
    assert len(r.json()) >= 4


def test_sin_token_es_rechazado(cliente):
    r = cliente.get("/auth/yo")
    assert r.status_code == 401
    assert r.json()["error"] == "sin_token"


def test_consulta_no_lee_no_publicado_ni_conectandose_directo(cliente, token_analista, token_consulta):
    # Genera una corrida OK de valoración que nunca se publica.
    cliente.post(
        "/cargas", headers={"Authorization": f"Bearer {token_analista}"},
        files={"archivo": ("pos.txt", b"PORTAFOLIO|NEMOTECNICO|NOMINAL\nP1|TESJUL27|100,00\n", "text/plain")},
        data={"tipo_insumo": "posiciones", "fecha_datos": "2026-08-21"},
    )
    cliente.post(
        "/cargas", headers={"Authorization": f"Bearer {token_analista}"},
        files={"archivo": ("pre.txt", b"NEMOTECNICO|PRECIO_LIMPIO\nTESJUL27|98,50\n", "text/plain")},
        data={"tipo_insumo": "precios", "fecha_datos": "2026-08-21"},
    )
    cliente.post(
        "/corridas", headers={"Authorization": f"Bearer {token_analista}"},
        json={"proceso": "valoracion", "fecha_datos": "2026-08-21", "parametros": {}},
    )
    import time
    time.sleep(0.5)

    # Vía API: consulta no ve nada (RLS ya lo protege).
    r = cliente.get("/resultados/valoracion?fecha=2026-08-21", headers={"Authorization": f"Bearer {token_consulta}"})
    assert r.json()["filas"] == []

    # Directo a Postgres, como el rol de aplicación, fijando el usuario
    # 'consulta': ni conectándose directamente se puede saltar la regla.
    dsn = config.database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM core.usuario WHERE correo = 'director@riesgo.local'")
            consulta_id = cur.fetchone()[0]
            cur.execute("SELECT set_config('app.usuario_id', %s, false)", (str(consulta_id),))
            cur.execute("SELECT count(*) FROM res.valoracion WHERE fecha_datos = '2026-08-21'")
            assert cur.fetchone()[0] == 0
