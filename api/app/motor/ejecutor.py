"""Ciclo de vida de una corrida (sección 10): valida requisitos, crea la
corrida, la marca EJECUTANDO y confirma para que la interfaz la vea, y
dispara la ejecución real del envoltorio en segundo plano."""
from __future__ import annotations

import io
import json
import subprocess
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import config
from app.db import conexion_con_usuario, engine

# "Un solo worker con cola interna" (sección 4) — no hace falta un
# orquestador de tareas con este volumen (sección 10).
_EJECUTOR_SEGUNDO_PLANO = ThreadPoolExecutor(max_workers=2)


def _version_codigo() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "sin-git"


_VERSION_CODIGO = _version_codigo()


class ErrorRequisitos(ValueError):
    """El mensaje ya nombra exactamente qué falta — la interfaz lo muestra
    tal cual junto al botón de ejecutar deshabilitado (sección 12)."""


def corrida_vigente(conn: Connection, proceso: str, fecha_datos) -> int | None:
    """La corrida OK más reciente de ese proceso y fecha. Una corrida
    ANULADA nunca cuenta como vigente (sección 6, regla de inmutabilidad)."""
    return conn.execute(
        text(
            "SELECT id FROM proc.corrida WHERE proceso = :proceso AND fecha_datos = :fecha "
            "AND estado = 'OK' ORDER BY iniciada_en DESC LIMIT 1"
        ),
        {"proceso": proceso, "fecha": fecha_datos},
    ).scalar()


def _validar_requisitos(conn: Connection, proceso: str, fecha_datos) -> tuple[list[int], list[int]]:
    requisitos = conn.execute(
        text("SELECT tipo_insumo, proceso_previo, obligatorio FROM proc.requisito WHERE proceso = :proceso"),
        {"proceso": proceso},
    ).mappings().all()

    faltantes: list[str] = []
    cargas_a_registrar: list[int] = []
    corridas_a_registrar: list[int] = []

    for r in requisitos:
        if r["tipo_insumo"]:
            carga_id = conn.execute(
                text(
                    "SELECT id FROM staging.carga WHERE tipo_insumo = :tipo AND fecha_datos = :fecha "
                    "AND estado = 'VALIDADO' ORDER BY cargado_en DESC LIMIT 1"
                ),
                {"tipo": r["tipo_insumo"], "fecha": fecha_datos},
            ).scalar()
            if carga_id is None:
                if r["obligatorio"]:
                    faltantes.append(f"insumo {r['tipo_insumo']} del {fecha_datos}")
            else:
                cargas_a_registrar.append(carga_id)
        if r["proceso_previo"]:
            corrida_id = corrida_vigente(conn, r["proceso_previo"], fecha_datos)
            if corrida_id is None:
                if r["obligatorio"]:
                    faltantes.append(f"proceso {r['proceso_previo']} ejecutado para el {fecha_datos}")
            else:
                corridas_a_registrar.append(corrida_id)

    if faltantes:
        raise ErrorRequisitos("Faltan insumos o procesos previos: " + "; ".join(faltantes))

    return cargas_a_registrar, corridas_a_registrar


def iniciar_corrida(usuario_id: int, proceso: str, fecha_datos, parametros: dict) -> int:
    from app.motor.registro import PROCESOS  # import diferido: evita ciclo con procesos/*.py

    if proceso not in PROCESOS:
        raise ValueError(f"'{proceso}' no es un proceso registrado.")

    with conexion_con_usuario(usuario_id) as conn:
        # Serializa por proceso+fecha: la segunda ejecución simultánea del
        # mismo proceso y fecha se rechaza con mensaje claro (sección 17).
        clave_lock = f"{proceso}|{fecha_datos}"
        obtuvo_lock = conn.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:clave, 0))"),
            {"clave": clave_lock},
        ).scalar()
        if not obtuvo_lock:
            raise ErrorRequisitos(f"Ya hay una ejecución de {proceso} en curso para el {fecha_datos}.")

        en_curso = conn.execute(
            text(
                "SELECT id FROM proc.corrida WHERE proceso = :proceso AND fecha_datos = :fecha "
                "AND estado IN ('PENDIENTE','EJECUTANDO') LIMIT 1"
            ),
            {"proceso": proceso, "fecha": fecha_datos},
        ).scalar()
        if en_curso:
            raise ErrorRequisitos(f"Ya hay una ejecución de {proceso} en curso para el {fecha_datos}.")

        cargas_a_registrar, corridas_a_registrar = _validar_requisitos(conn, proceso, fecha_datos)

        corrida_id = conn.execute(
            text(
                "INSERT INTO proc.corrida (proceso, fecha_datos, estado, parametros, version_codigo, disparada_por) "
                "VALUES (:proceso, :fecha, 'PENDIENTE', CAST(:parametros AS jsonb), :version, :usuario_id) "
                "RETURNING id"
            ),
            {
                "proceso": proceso, "fecha": fecha_datos, "parametros": json.dumps(parametros or {}),
                "version": _VERSION_CODIGO, "usuario_id": usuario_id,
            },
        ).scalar_one()

        for carga_id in cargas_a_registrar:
            conn.execute(
                text("INSERT INTO proc.corrida_insumo (corrida_id, carga_id) VALUES (:cid, :carga_id)"),
                {"cid": corrida_id, "carga_id": carga_id},
            )
        for corrida_origen in corridas_a_registrar:
            conn.execute(
                text("INSERT INTO proc.corrida_insumo (corrida_id, corrida_origen) VALUES (:cid, :origen)"),
                {"cid": corrida_id, "origen": corrida_origen},
            )

        conn.execute(text("UPDATE proc.corrida SET estado = 'EJECUTANDO' WHERE id = :id"), {"id": corrida_id})
        # El "with" confirma la transacción al salir de este bloque: la
        # interfaz ya puede ver la corrida EJECUTANDO antes de que termine.

    _EJECUTOR_SEGUNDO_PLANO.submit(_ejecutar_en_segundo_plano, usuario_id, proceso, fecha_datos, corrida_id, parametros)
    return corrida_id


def _ejecutar_en_segundo_plano(usuario_id: int, proceso: str, fecha_datos, corrida_id: int, parametros: dict) -> None:
    from app.motor.registro import PROCESOS

    captura = io.StringIO()
    inicio = time.monotonic()

    try:
        with conexion_con_usuario(usuario_id) as conn:
            with redirect_stdout(captura):
                filas = PROCESOS[proceso]["ejecutar"](conn, fecha_datos, corrida_id, parametros)
            duracion_ms = int((time.monotonic() - inicio) * 1000)
            conn.execute(
                text(
                    "UPDATE proc.corrida SET estado = 'OK', finalizada_en = now(), duracion_ms = :dur, "
                    "filas_resultado = :filas, log_ejecucion = :log WHERE id = :id"
                ),
                {"dur": duracion_ms, "filas": filas, "log": captura.getvalue() or None, "id": corrida_id},
            )
            # Si algo de lo anterior lanza, el "with" hace rollback: la
            # corrida no queda en OK con filas a medio escribir (sección 17).
    except Exception as exc:
        duracion_ms = int((time.monotonic() - inicio) * 1000)
        traza = traceback.format_exc()
        with conexion_con_usuario(usuario_id) as conn:
            conn.execute(
                text(
                    "UPDATE proc.corrida SET estado = 'ERROR', finalizada_en = now(), duracion_ms = :dur, "
                    "mensaje_error = :msg, traza_error = :traza, log_ejecucion = :log WHERE id = :id"
                ),
                {"dur": duracion_ms, "msg": str(exc), "traza": traza, "log": captura.getvalue() or None, "id": corrida_id},
            )


def anular_corrida(usuario_id: int, corrida_id: int, motivo: str) -> bool:
    with conexion_con_usuario(usuario_id) as conn:
        resultado = conn.execute(
            text(
                "UPDATE proc.corrida SET estado = 'ANULADA', anulada_por = :uid, anulada_en = now(), "
                "motivo_anulacion = :motivo WHERE id = :id AND estado IN ('OK','ERROR')"
            ),
            {"uid": usuario_id, "motivo": motivo, "id": corrida_id},
        )
        return resultado.rowcount > 0


def marcar_corridas_colgadas() -> int:
    """Toda corrida en EJECUTANDO por más de corrida_timeout_minutos se
    marca ERROR. Se llama al arranque del servicio (sección 10)."""
    with engine.begin() as conn:
        resultado = conn.execute(
            text(
                "UPDATE proc.corrida SET estado = 'ERROR', finalizada_en = now(), "
                "mensaje_error = 'Marcada como error por exceder el tiempo máximo de ejecución.' "
                "WHERE estado = 'EJECUTANDO' "
                "AND iniciada_en < now() - make_interval(mins => :minutos)"
            ),
            {"minutos": config.corrida_timeout_minutos},
        )
        return resultado.rowcount
