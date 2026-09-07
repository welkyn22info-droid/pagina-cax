"""Ingesta de archivos (sección 9) — un solo punto de entrada para todo
insumo. El motor de ejecución (sección 10) solo lee de staging; nunca de
un archivo directamente."""
from __future__ import annotations

import hashlib
import os
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text

from app.config import config
from app.db import conexion_con_usuario
from app.ingesta.curvas_ancho import es_formato_ancho, pivotear_curvas_ancho
from app.ingesta.esquemas import ESQUEMAS
from app.ingesta.lector import _detectar_separador, _parsear_numero_colombiano, leer_archivo
from app.ingesta.validador import validar
from app.seguridad import UsuarioSesion, registrar_evento, requiere_permiso, usuario_actual

router = APIRouter(prefix="/cargas", tags=["cargas"])

# A qué módulo (para permisos y RLS) pertenece cada tipo de insumo.
# Debe coincidir con el CASE de la política ver_carga en la migración 006.
MODULO_POR_TIPO = {
    "posiciones": "valoracion",
    "precios": "valoracion",
    "flujos_pasivo": "pasivo",
    "curvas": "curvas",
}


def _error(codigo: int, error: str, mensaje: str, detalle: dict | None = None) -> HTTPException:
    return HTTPException(status_code=codigo, detail={"error": error, "mensaje": mensaje, "detalle": detalle or {}})


def _parsear_numero_seguro(valor):
    """Como _parsear_numero_colombiano, pero devuelve None en vez de lanzar
    — para poder vectorizar con .apply() y contar inválidos con .isna()
    en vez de un try/except por fila."""
    try:
        return _parsear_numero_colombiano(valor)
    except ValueError:
        return None


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
                "WHERE tipo_insumo = :tipo AND fecha_datos = :fecha AND hash_sha256 = :hash "
                "AND anulada_en IS NULL"
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
            _insertar_filas(conn, esquema.tabla, resultado.df_validado, carga_id, fecha_datos, usuario.id)

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


@router.post("/curvas-multiples")
async def cargar_curvas_multiples(archivo: UploadFile = File(...), usuario: UsuarioSesion = Depends(usuario_actual)):
    """Carga un archivo ANCHO de curvas (una columna por fecha, como llega
    de la fuente) — crea una carga por cada fecha que trae, igual que si
    se hubiera subido un archivo por día (decisión 22). Para un solo día
    (3 columnas: curva, nodo, valor) se usa POST /cargas normal."""
    _verificar_permiso_cargar(usuario, "curvas")

    contenido = await archivo.read()
    separador = _detectar_separador(contenido)
    primera_linea = contenido.decode("utf-8-sig", errors="ignore").splitlines()[0] if contenido else ""
    encabezados = primera_linea.split(separador) if primera_linea else []

    if not es_formato_ancho(encabezados):
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "formato_no_reconocido",
            "El archivo no parece tener el formato ancho esperado: una columna 'Curva', una 'Nodo'/'Plazo' "
            "y al menos dos columnas más con fechas.",
        )

    por_fecha = pivotear_curvas_ancho(contenido)
    if not por_fecha:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "sin_fechas", "No se reconoció ninguna fecha en el archivo.")

    ruta_original = None
    resultados = []
    with conexion_con_usuario(usuario.id) as conn:
        for fecha_iso in sorted(por_fecha):
            fecha_datos = date.fromisoformat(fecha_iso)
            df = por_fecha[fecha_iso].copy()

            # .apply() en vez de .at[idx, col] fila por fila: con ~13.500
            # filas por fecha, el indexado escalar repetido de pandas es el
            # cuello de botella real (se midió con el archivo de agosto
            # completo — 418.655 filas en total).
            nodos = df["nodo"].apply(_parsear_numero_seguro)
            valores = df["valor"].apply(_parsear_numero_seguro)
            filas_invalidas = int(nodos.isna().sum() + valores.isna().sum())

            if filas_invalidas:
                resultados.append({
                    "fecha_datos": fecha_iso, "carga_id": None, "estado": "RECHAZADO", "duplicado": False,
                    "filas_validas": 0, "mensaje": f"{filas_invalidas} filas con nodo o valor no numérico.",
                })
                continue

            df["nodo"] = nodos.astype(int)
            df["valor"] = valores
            df["tipo_curva"] = df["tipo_curva"].astype(str).str.strip()

            hash_fecha = hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()
            existente = conn.execute(
                text(
                    "SELECT id, estado::text FROM staging.carga WHERE tipo_insumo = 'curvas' "
                    "AND fecha_datos = :fecha AND hash_sha256 = :hash AND anulada_en IS NULL"
                ),
                {"fecha": fecha_datos, "hash": hash_fecha},
            ).mappings().first()
            if existente is not None:
                resultados.append({
                    "fecha_datos": fecha_iso, "carga_id": existente["id"], "estado": existente["estado"],
                    "duplicado": True, "filas_validas": 0, "mensaje": "Ya se había cargado para esta fecha.",
                })
                continue

            carga_id = conn.execute(
                text(
                    "INSERT INTO staging.carga "
                    "(tipo_insumo, fecha_datos, nombre_archivo, hash_sha256, filas_leidas, filas_validas, "
                    " estado, cargado_por) "
                    "VALUES ('curvas', :fecha, :nombre, :hash, :filas, :filas, 'VALIDADO', :usuario_id) "
                    "RETURNING id"
                ),
                {
                    "fecha": fecha_datos, "nombre": f"{archivo.filename} — {fecha_iso}", "hash": hash_fecha,
                    "filas": len(df), "usuario_id": usuario.id,
                },
            ).scalar_one()

            if ruta_original is None:
                ruta_original = _guardar_archivo_original(contenido, "curvas", fecha_datos, carga_id, archivo.filename)
            if ruta_original:
                conn.execute(
                    text("UPDATE staging.carga SET ruta_archivo = :ruta WHERE id = :id"),
                    {"ruta": ruta_original, "id": carga_id},
                )

            _insertar_filas(conn, "staging.curva_nodo", df, carga_id, fecha_datos, usuario.id)
            registrar_evento(
                conn, usuario.id, "carga", "staging.carga", carga_id,
                {"tipo_insumo": "curvas", "fecha_datos": fecha_iso, "origen": "carga_multiple"},
            )
            resultados.append({
                "fecha_datos": fecha_iso, "carga_id": carga_id, "estado": "VALIDADO", "duplicado": False,
                "filas_validas": len(df), "mensaje": f"{len(df)} filas válidas.",
            })

    return {"archivo": archivo.filename, "fechas_procesadas": len(resultados), "resultados": resultados}


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


def _insertar_filas(conn, tabla: str, df, carga_id: int, fecha_datos: date, usuario_id: int | None = None) -> None:
    import json

    from sqlalchemy import inspect

    # leer_archivo (ingesta/lector.py) siempre agrega "campos_extra" al
    # DataFrame, tenga la tabla destino esa columna o no (staging.curva_nodo
    # no la tiene). Se descarta aquí lo que la tabla real no admite, en vez
    # de asumir que el DataFrame ya viene exacto.
    esquema, nombre = tabla.split(".")
    columnas_tabla = {c["name"] for c in inspect(conn).get_columns(nombre, schema=esquema)}

    df = df.copy()
    # usuario_carga (staging.curva_nodo, decisión 23) no tiene un valor
    # sensato por defecto — se completa aquí si la tabla lo tiene y el
    # DataFrame no lo trae ya. fecha_cargue y anulado si tienen default en
    # la propia columna (now() / false) y no hace falta pasarlos.
    if usuario_id is not None and "usuario_carga" in columnas_tabla and "usuario_carga" not in df.columns:
        df["usuario_carga"] = usuario_id

    columnas = [c for c in df.columns if c in columnas_tabla]
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
    # Un solo execute con la lista completa (executemany real) en vez de un
    # roundtrip por fila — con insumos grandes (curvas: ~13.500 filas por
    # carga) un execute por fila es minutos; en lote son segundos.
    conn.execute(sql, filas)


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
                f"estado::text, cargado_por, cargado_en, anulada_por, anulada_en, motivo_anulacion "
                f"FROM staging.carga {where} "
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
                        "AND estado = 'VALIDADO' AND anulada_en IS NULL LIMIT 1"
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
                "filas_validas, estado::text, detalle_error, cargado_por, cargado_en, "
                "anulada_por, anulada_en, motivo_anulacion "
                "FROM staging.carga WHERE id = :id"
            ),
            {"id": carga_id},
        ).mappings().first()
    if fila is None:
        raise _error(status.HTTP_404_NOT_FOUND, "no_encontrada", "La carga no existe o no tiene permiso para verla.")
    return dict(fila)


class AnularCargaEntrada(BaseModel):
    motivo: str


@router.post("/{carga_id}/anular")
def anular_carga(carga_id: int, entrada: AnularCargaEntrada, usuario: UsuarioSesion = Depends(usuario_actual)):
    """Anula una carga ya hecha (decisión 18) — no borra las filas (nunca se
    borra un insumo, sección 17), solo la marca para que se sepa que ya no
    es válida y quede fuera de lo que se muestra por defecto."""
    if not entrada.motivo or not entrada.motivo.strip():
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "motivo_requerido", "Debe indicar el motivo de la anulación.")

    with conexion_con_usuario(usuario.id) as conn:
        fila = conn.execute(
            text("SELECT tipo_insumo, anulada_en FROM staging.carga WHERE id = :id"), {"id": carga_id}
        ).mappings().first()
        if fila is None:
            raise _error(status.HTTP_404_NOT_FOUND, "no_encontrada", "La carga no existe o no tiene permiso para verla.")
        if fila["anulada_en"] is not None:
            raise _error(status.HTTP_409_CONFLICT, "ya_anulada", "Esta carga ya estaba anulada.")

        modulo = MODULO_POR_TIPO.get(fila["tipo_insumo"], fila["tipo_insumo"])
        _verificar_permiso_cargar(usuario, modulo)

        conn.execute(
            text(
                "UPDATE staging.carga SET anulada_por = :uid, anulada_en = now(), motivo_anulacion = :motivo "
                "WHERE id = :id"
            ),
            {"uid": usuario.id, "motivo": entrada.motivo, "id": carga_id},
        )

        # staging.curva_nodo guarda su propia copia de anulado/usuario_anulado
        # (decisión 23) — se actualiza en la misma transacción para que
        # nunca quede desincronizada de staging.carga.
        if fila["tipo_insumo"] == "curvas":
            conn.execute(
                text("UPDATE staging.curva_nodo SET anulado = true, usuario_anulado = :uid WHERE carga_id = :id"),
                {"uid": usuario.id, "id": carga_id},
            )

        registrar_evento(conn, usuario.id, "anulacion_carga", "staging.carga", carga_id, {"motivo": entrada.motivo})

    return {"mensaje": "Carga anulada."}
