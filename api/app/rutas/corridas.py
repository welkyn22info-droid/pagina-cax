from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.db import conexion_con_usuario
from app.motor.ejecutor import ErrorRequisitos, anular_corrida, iniciar_corrida
from app.motor.registro import PROCESOS
from app.seguridad import UsuarioSesion, registrar_evento, usuario_actual

router = APIRouter(prefix="/corridas", tags=["corridas"])


def _error(codigo: int, error: str, mensaje: str, detalle: dict | None = None) -> HTTPException:
    return HTTPException(status_code=codigo, detail={"error": error, "mensaje": mensaje, "detalle": detalle or {}})


class DispararCorridaEntrada(BaseModel):
    proceso: str
    fecha_datos: date
    parametros: dict = {}


@router.post("")
def disparar_corrida(entrada: DispararCorridaEntrada, usuario: UsuarioSesion = Depends(usuario_actual)):
    if entrada.proceso not in PROCESOS:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "proceso_desconocido",
            f"'{entrada.proceso}' no es un proceso registrado.", {"procesos_validos": list(PROCESOS.keys())},
        )
    modulo = PROCESOS[entrada.proceso]["modulo"]

    with conexion_con_usuario(usuario.id) as conn:
        puede = conn.execute(
            text("SELECT puede_ejecutar FROM core.permiso WHERE rol = :rol AND modulo = :modulo"),
            {"rol": usuario.rol, "modulo": modulo},
        ).scalar()
    if not puede:
        raise _error(
            status.HTTP_403_FORBIDDEN, "sin_permiso",
            f"Su rol ({usuario.rol}) no tiene permiso para ejecutar {entrada.proceso}.",
        )

    try:
        corrida_id = iniciar_corrida(usuario.id, entrada.proceso, entrada.fecha_datos, entrada.parametros)
    except ErrorRequisitos as exc:
        raise _error(status.HTTP_409_CONFLICT, "requisitos_incompletos", str(exc))

    with conexion_con_usuario(usuario.id) as conn:
        registrar_evento(
            conn, usuario.id, "ejecucion", "proc.corrida", corrida_id,
            {"proceso": entrada.proceso, "fecha_datos": str(entrada.fecha_datos)},
        )

    return {"corrida_id": corrida_id, "estado": "EJECUTANDO"}


@router.get("/{corrida_id}")
def detalle_corrida(corrida_id: int, usuario: UsuarioSesion = Depends(usuario_actual)):
    with conexion_con_usuario(usuario.id) as conn:
        fila = conn.execute(
            text(
                "SELECT id, proceso, fecha_datos, estado::text, parametros, version_codigo, "
                "disparada_por, iniciada_en, finalizada_en, duracion_ms, filas_resultado, "
                "mensaje_error, traza_error, log_ejecucion, anulada_por, anulada_en, motivo_anulacion "
                "FROM proc.corrida WHERE id = :id"
            ),
            {"id": corrida_id},
        ).mappings().first()
        if fila is None:
            raise _error(status.HTTP_404_NOT_FOUND, "no_encontrada", "La corrida no existe o no tiene permiso para verla.")

        insumos = conn.execute(
            text(
                "SELECT ci.carga_id, c.tipo_insumo, c.nombre_archivo, c.hash_sha256, "
                "       ci.corrida_origen, co.proceso AS proceso_origen "
                "FROM proc.corrida_insumo ci "
                "LEFT JOIN staging.carga c ON c.id = ci.carga_id "
                "LEFT JOIN proc.corrida co ON co.id = ci.corrida_origen "
                "WHERE ci.corrida_id = :id"
            ),
            {"id": corrida_id},
        ).mappings().all()

    resultado = dict(fila)
    resultado["insumos"] = [dict(i) for i in insumos]
    return resultado


@router.get("")
def listar_corridas(
    proceso: str | None = None,
    fecha: date | None = None,
    estado: str | None = None,
    usuario: UsuarioSesion = Depends(usuario_actual),
):
    condiciones = []
    parametros: dict = {}
    if proceso:
        condiciones.append("proceso = :proceso")
        parametros["proceso"] = proceso
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
                f"SELECT id, proceso, fecha_datos, estado::text, disparada_por, iniciada_en, "
                f"finalizada_en, duracion_ms, filas_resultado, mensaje_error "
                f"FROM proc.corrida {where} ORDER BY iniciada_en DESC LIMIT 200"
            ),
            parametros,
        ).mappings().all()
    return [dict(f) for f in filas]


class AnularEntrada(BaseModel):
    motivo: str


@router.post("/{corrida_id}/anular")
def anular(corrida_id: int, entrada: AnularEntrada, usuario: UsuarioSesion = Depends(usuario_actual)):
    if not entrada.motivo or not entrada.motivo.strip():
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "motivo_requerido", "Debe indicar el motivo de la anulación.")

    if usuario.rol not in ("admin", "revisor"):
        raise _error(status.HTTP_403_FORBIDDEN, "sin_permiso", "Solo un revisor o administrador puede anular una corrida.")

    anulada = anular_corrida(usuario.id, corrida_id, entrada.motivo)
    if not anulada:
        raise _error(
            status.HTTP_409_CONFLICT, "no_anulable",
            "La corrida no existe, no tiene permiso para verla, o no está en estado OK/ERROR.",
        )

    with conexion_con_usuario(usuario.id) as conn:
        registrar_evento(conn, usuario.id, "anulacion", "proc.corrida", corrida_id, {"motivo": entrada.motivo})

    return {"mensaje": "Corrida anulada."}


procesos_router = APIRouter(prefix="/procesos", tags=["procesos"])


@procesos_router.get("")
def catalogo_procesos(fecha: date, usuario: UsuarioSesion = Depends(usuario_actual)):
    """Catálogo con requisitos y estado del día (sección 11)."""
    with conexion_con_usuario(usuario.id) as conn:
        resultado = []
        for clave, definicion in PROCESOS.items():
            ultima = conn.execute(
                text(
                    "SELECT id, estado::text, iniciada_en, finalizada_en, duracion_ms, disparada_por "
                    "FROM proc.corrida WHERE proceso = :proceso AND fecha_datos = :fecha "
                    "ORDER BY iniciada_en DESC LIMIT 1"
                ),
                {"proceso": clave, "fecha": fecha},
            ).mappings().first()
            requisitos = conn.execute(
                text("SELECT tipo_insumo, proceso_previo FROM proc.requisito WHERE proceso = :proceso"),
                {"proceso": clave},
            ).mappings().all()
            resultado.append({
                "proceso": clave,
                "nombre": definicion["nombre"],
                "modulo": definicion["modulo"],
                "requisitos": [dict(r) for r in requisitos],
                "ultima_corrida": dict(ultima) if ultima else None,
            })
    return resultado
