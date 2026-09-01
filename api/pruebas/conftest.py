"""Fixtures compartidas: recrean la base de prueba desde cero (migraciones
+ semillas + grants) antes de cada módulo de pruebas, para que cada archivo
de test parta de un estado conocido — igual que pide la sección 17."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[2]
MIGRACIONES = sorted((RAIZ / "db" / "migraciones").glob("*.sql"))
SEMILLAS = [
    RAIZ / "db" / "semillas" / "usuarios_iniciales.sql",
    RAIZ / "db" / "semillas" / "maestros_ejemplo.sql",
]

BASE_PRUEBA = "riesgo_test"


def _psql(base: str, args: list[str], sql: str | None = None, archivo: Path | None = None) -> None:
    cmd = ["sudo", "-u", "postgres", "psql", "-d", base, "-v", "ON_ERROR_STOP=1", *args]
    if archivo:
        cmd += ["-f", str(archivo)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    elif sql:
        cmd += ["-c", sql]
        subprocess.run(cmd, check=True, capture_output=True, text=True)


@pytest.fixture(scope="session", autouse=True)
def base_de_datos_limpia():
    subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-v", "ON_ERROR_STOP=1",
         "-c", f"DROP DATABASE IF EXISTS {BASE_PRUEBA};",
         "-c", f"CREATE DATABASE {BASE_PRUEBA};"],
        check=True, capture_output=True, text=True,
    )
    for m in MIGRACIONES:
        _psql(BASE_PRUEBA, [], archivo=m)
    for s in SEMILLAS:
        _psql(BASE_PRUEBA, [], archivo=s)

    _psql(BASE_PRUEBA, [], sql=(
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_riesgo') THEN "
        "CREATE ROLE app_riesgo LOGIN PASSWORD 'clave_prueba_local'; END IF; END $$;"
    ))
    _psql(BASE_PRUEBA, [], archivo=RAIZ / "operacion" / "preparar_rol.sql")

    yield


@pytest.fixture(scope="session")
def cliente(base_de_datos_limpia) -> TestClient:
    from app.main import app

    return TestClient(app)


def token_para(cliente: TestClient, correo: str, clave: str = "Cambiar123456") -> str:
    r = cliente.post("/auth/login", json={"correo": correo, "clave": clave})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture
def token_admin(cliente):
    return token_para(cliente, "admin@riesgo.local")


@pytest.fixture
def token_analista(cliente):
    return token_para(cliente, "analista1@riesgo.local")


@pytest.fixture
def token_revisor(cliente):
    return token_para(cliente, "revisor1@riesgo.local")


@pytest.fixture
def token_consulta(cliente):
    return token_para(cliente, "director@riesgo.local")
