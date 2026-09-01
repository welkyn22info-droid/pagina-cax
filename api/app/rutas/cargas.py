"""Ingesta de archivos (sección 9) — un solo punto de entrada para todo
insumo. El motor de ejecución (sección 10) solo lee de staging; nunca de
un archivo directamente."""
from __future__ import annotations

import hashlib
import os
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import text

from app.config import config
from app.db import conexion_con_usuario
from app.ingesta.esquemas import ESQUEMAS
from app.ingesta.lector import leer_archivo
from app.ingesta.validador import validar
from app.seguridad import UsuarioSesion, registrar_evento, requiere_permiso, usuario_actual

router = APIRouter(prefix="/cargas", tags=["cargas"])

# A qué módulo (para permisos y RLS) pertenece cada tipo de insumo.
# Debe coincidir con el CASE de la política ver_carga en la migración 006.
MODULO_POR_TIPO = {
    "posiciones": "valoracion",
    "precios": "valoracion",
    "flujos_pasivo": "pasivo",
}


def _error(codigo: int, error: str, mensaje: str, detalle: dict | None = None) -> HTTPException:
    return HTTPException(status_code=codigo, detail={"error": error, "mensaje": mensaje, "detalle": detalle or {}})


@router.post("")
async def crear_carga(
    request: Request,
    archivo: UploadFile = File(...),
    tipo_insumo: str = Form(...),
    fecha_datos: date = Form(...),
    usuario: UsuarioSesion = Depends(usuario_actual),
):
    esquema = ESQUEMAS.get(tipo_insumo)
    if esquema is None:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "tipo_insumo_desconocido",
            f"'{tipo_insumo}' no es un tipo de insumo reconocido.",
            {"tipos_validos": list(ESQUEMAS.keys())},
        )

    modulo = MODULO_POR_TIPO[tipo_insumo]
    _verificar_permiso_cargar(usuario, modulo)

    contenido = await archivo.read()
    hash_sha256 = hashlib.sha256(contenido).hexdigest()

    with conexion_con_usuario(usuario.id) as conn:
        existente = conn.execute(
            text(
                "SELECT id, estado::text FROM staging.carga "
                "WHERE tipo_insumo = :tipo AND fecha_datos = :fecha AND hash_sha256 = :hash"
            ),
            {"tipo": tipo_insumo, "fecha": fecha_datos, "hash": hash_sha256},
        ).mappings().first()
        if existente is not None:
            return {
                "duplicado": True,
                "carga_id": existente["id"],
                "estado": existente["estado"],
                "mensaje": "Este archivo ya se había cargado para esta fecha. No se volvió a insertar.",
            }

        lectura = leer_archivo(archivo.filename, contenido, esquema)
        resultado = validar(lectura, esquema)

        estado = "VALIDADO" if resultado.aceptado else "RECHAZADO"
        carga_id = conn.execute(
            text(
                "INSERT INTO staging.carga "
                "(tipo_insumo, fecha_datos, nombre_archivo, hash_sha256, filas_leidas, filas_validas, "
                " estado, detalle_error, ruta_archivo, cargado_por) "
                "VALUES (:tipo, :fecha, :nombre, :hash, :leidas, :validas, :estado, "
                " CAST(:detalle AS jsonb), :ruta, :usuario_id) RETURNING id"
            ),
            {
                "tipo": tipo_insumo,
                "fecha": fecha_datos,
                "nombre": archivo.filename,
                "hash": hash_sha256,
                "leidas": lectura.filas_leidas,
                "validas": resultado.filas_validas,
                "estado": estado,
                "detalle": _json_o_none(resultado.detalle_error()),
                "ruta": None,
                "usuario_id": usuario.id,
            },
        ).scalar_one()

        ruta_guardada = _guardar_archivo_original(contenido, tipo_insumo, fecha_datos, carga_id, archivo.filename)
        if ruta_guardada:
            conn.execute(
                text("UPDATE staging.carga SET ruta_archivo = :ruta WHERE id = :id"),
                {"ruta": ruta_guardada, "id": carga_id},
            )

        if resultado.aceptado:
            _insertar_filas(conn, esquema.tabla, resultado.df_validado, carga_id, fecha_datos)

        registrar_evento(
            conn, usuario.id, "carga", "staging.carga", carga_id,
            {"tipo_insumo": tipo_insumo, "fecha_datos": str(fecha_datos), "estado": estado},
        )

        return {
            "duplicado": False,
            "carga_id": carga_id,
            "estado": estado,
            "filas_leidas": lectura.filas_leidas,
            "filas_validas": resultado.filas_validas,
            "mensaje": resultado.mensaje(archivo.filename, lectura.encabezados_originales),
            "detalle_error": resultado.detalle_error(),
        }


def _verificar_permiso_cargar(usuario: UsuarioSesion, modulo: str) -> None:
    with conexion_con_usuario(usuario.id) as conn:
        permitido = conn.execute(
            text("SELECT puede_cargar FROM core.permiso WHERE rol = :rol AND modulo = :modulo"),
            {"rol": usuario.rol, "modulo": modulo},
        ).scalar()
    if not permitido:
        raise _error(
            status.HTTP_403_FORBIDDEN, "sin_permiso",
            f"Su rol ({usuario.rol}) no tiene permiso para cargar insumos de {modulo}.",
        )


def _guardar_archivo_original(contenido: bytes, tipo_insumo: str, fecha_datos: date, carga_id: int, nombre: str) -> str | None:
    try:
        carpeta = os.path.join(config.ruta_archivos_originales, tipo_insumo, fecha_datos.isoformat())
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f"{carga_id}_{nombre}")
        with open(ruta, "wb") as f:
            f.write(contenido)
        return ruta
    except OSError:
        # No bloquea la carga: el respaldo de la base ya tiene las filas.
        # Se deja para que operación investigue por qué el disco no está disponible.
        return None


def _insertar_filas(conn, tabla: str, df, carga_id: int, fecha_datos: date) -> None:
    import json

    columnas = list(df.columns)
    marcadores = []
    for c in columnas:
        marcadores.append(f"CAST(:{c} AS jsonb)" if c == "campos_extra" else f":{c}")
    columnas_sql = ", ".join(columnas + ["carga_id", "fecha_datos"])
    sql = text(f"INSERT INTO {tabla} ({columnas_sql}) VALUES ({', '.join(marcadores)}, :carga_id, :fecha_datos)")

    filas = df.to_dict(orient="records")
    for fila in filas:
        if "campos_extra" in fila:
            fila["campos_extra"] = json.dumps(fila["campos_extra"])
        fila["carga_id"] = carga_id
        fila["fecha_datos"] = fecha_datos
        conn.execute(sql, fila)


def _json_o_none(detalle: dict | None) -> str | None:
    import json

    return json.dumps(detalle) if detalle is not None else None


@router.get("")
def listar_cargas(
    tipo_insumo: str | None = None,
    fecha: date | None = None,
    estado: str | None = None,
    usuario: UsuarioSesion = Depends(usuario_actual),
):
    condiciones = []
    parametros: dict = {}
    if tipo_insumo:
        condiciones.append("tipo_insumo = :tipo")
        parametros["tipo"] = tipo_insumo
    if fecha:
        condiciones.append("fecha_datos = :fecha")
        parametros["fecha"] = fecha
    if estado:
        condiciones.append("estado = :estado")
        parametros["estado"] = estado
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    with conexion_con_usuario(usuario.id) as conn:
        filas = conn.execute(
            text(
                f"SELECT id, tipo_insumo, fecha_datos, nombre_archivo, filas_leidas, filas_validas, "
                f"estado::text, cargado_por, cargado_en FROM staging.carga {where} "
                f"ORDER BY cargado_en DESC LIMIT 200"
            ),
            parametros,
        ).mappings().all()
    return [dict(f) for f in filas]


@router.get("/faltantes")
def cargas_faltantes(fecha: date, usuario: UsuarioSesion = Depends(usuario_actual)):
    """Qué insumos faltan para poder ejecutar cada proceso ese día
    (usado por la página de Cargas y por el botón de ejecutar en Procesos)."""
    with conexion_con_usuario(usuario.id) as conn:
        requisitos = conn.execute(
            text("SELECT proceso, tipo_insumo, proceso_previo FROM proc.requisito WHERE obligatorio")
        ).mappings().all()

        resultado: dict[str, list[str]] = {}
        for r in requisitos:
            faltantes = resultado.setdefault(r["proceso"], [])
            if r["tipo_insumo"]:
                existe = conn.execute(
                    text(
                        "SELECT 1 FROM staging.carga WHERE tipo_insumo = :tipo AND fecha_datos = :fecha "
                        "AND estado = 'VALIDADO' LIMIT 1"
                    ),
                    {"tipo": r["tipo_insumo"], "fecha": fecha},
                ).first()
                if not existe:
                    faltantes.append(f"insumo:{r['tipo_insumo']}")
            if r["proceso_previo"]:
                existe = conn.execute(
                    text(
                        "SELECT 1 FROM proc.corrida WHERE proceso = :proceso AND fecha_datos = :fecha "
                        "AND estado = 'OK' LIMIT 1"
                    ),
                    {"proceso": r["proceso_previo"], "fecha": fecha},
                ).first()
                if not existe:
                    faltantes.append(f"proceso:{r['proceso_previo']}")

    return {"fecha": str(fecha), "faltantes": resultado}


@router.get("/{carga_id}")
def detalle_carga(carga_id: int, usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        fila = conn.execute(
            text(
                "SELECT id, tipo_insumo, fecha_datos, nombre_archivo, hash_sha256, filas_leidas, "
                "filas_validas, estado::text, detalle_error, cargado_por, cargado_en "
                "FROM staging.carga WHERE id = :id"
            ),
            {"id": carga_id},
        ).mappings().first()
    if fila is None:
        raise _error(status.HTTP_404_NOT_FOUND, "no_encontrada", "La carga no existe o no tiene permiso para verla.")
    return dict(fila)
