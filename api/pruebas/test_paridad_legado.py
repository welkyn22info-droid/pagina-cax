"""Paridad (sección 8 y 17): compara el resultado que produce la
plataforma —subida vía API, ejecución del motor, lectura del resultado—
contra llamar la función de cálculo directamente sobre los mismos datos.

Hoy la función de cálculo es la simulada en app/legado_simulado (no hay
acceso al código real de CAXDAC en esta máquina — ver DECISIONES.md,
decisión 1). La estructura de esta prueba no cambia cuando la máquina
enterprise sustituya el import: seguirá comparando "lo que entrega la
plataforma" contra "lo que entrega la función de cálculo", con tolerancia
1e-9, sobre las mismas fechas fijadas aquí (incluye un cierre de mes:
2026-07-31, y un caso atípico: 2026-08-15 tiene una posición sin precio).
"""
import io
from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FECHAS = ["2026-07-31", "2026-08-15", "2026-08-31"]
TOLERANCIA = 1e-9


def _subir_y_ejecutar(cliente, token, fecha_compacta: str, fecha_iso: str):
    for tipo, prefijo in (("posiciones", "posiciones"), ("precios", "precios")):
        ruta = FIXTURES / f"{prefijo}_{fecha_compacta}.txt"
        with open(ruta, "rb") as f:
            r = cliente.post(
                "/cargas",
                headers={"Authorization": f"Bearer {token}"},
                files={"archivo": (ruta.name, io.BytesIO(f.read()), "text/plain")},
                data={"tipo_insumo": tipo, "fecha_datos": fecha_iso},
            )
            assert r.status_code == 200 and r.json()["estado"] == "VALIDADO", r.text

    r = cliente.post(
        "/corridas",
        headers={"Authorization": f"Bearer {token}"},
        json={"proceso": "valoracion", "fecha_datos": fecha_iso, "parametros": {}},
    )
    assert r.status_code == 200, r.text
    corrida_id = r.json()["corrida_id"]

    import time

    for _ in range(50):
        detalle = cliente.get(f"/corridas/{corrida_id}", headers={"Authorization": f"Bearer {token}"}).json()
        if detalle["estado"] in ("OK", "ERROR"):
            break
        time.sleep(0.1)
    assert detalle["estado"] == "OK", detalle.get("mensaje_error")
    return corrida_id


def _calcular_directo(fecha_compacta: str) -> pd.DataFrame:
    """Reconstruye los mismos DataFrames de entrada leyendo los fixtures
    tal cual los leería la ingesta, y llama la función de cálculo
    directamente — sin pasar por la base de datos."""
    from app.ingesta.esquemas import ESQUEMAS
    from app.ingesta.lector import leer_archivo
    from app.ingesta.validador import validar
    from app.legado_simulado.valoracion import calcular_valoracion

    dataframes = {}
    for tipo in ("posiciones", "precios"):
        ruta = FIXTURES / f"{tipo}_{fecha_compacta}.txt"
        with open(ruta, "rb") as f:
            lectura = leer_archivo(ruta.name, f.read(), ESQUEMAS[tipo])
        resultado = validar(lectura, ESQUEMAS[tipo])
        assert resultado.aceptado
        dataframes[tipo] = resultado.df_validado

    return calcular_valoracion(dataframes["posiciones"], dataframes["precios"])


@pytest.mark.parametrize("fecha_iso", FECHAS)
def test_paridad_valoracion(cliente, token_analista, fecha_iso):
    fecha_compacta = fecha_iso.replace("-", "")  # '2026-07-31' -> '20260731', nombre de los fixtures

    esperado = _calcular_directo(fecha_compacta)

    _subir_y_ejecutar(cliente, token_analista, fecha_compacta, fecha_iso)

    r = cliente.get(f"/resultados/valoracion?fecha={fecha_iso}", headers={"Authorization": f"Bearer {token_analista}"})
    assert r.status_code == 200
    obtenido = pd.DataFrame(r.json()["filas"])

    assert len(obtenido) == len(esperado), "número de filas distinto entre plataforma y cálculo directo"

    esperado_ord = esperado.sort_values(["portafolio", "instrumento_cod"]).reset_index(drop=True)
    obtenido_ord = obtenido.sort_values(["portafolio", "instrumento_cod"]).reset_index(drop=True)

    for columna in ("valor_mercado", "valor_causado", "nominal", "precio_usado"):
        diferencia = (esperado_ord[columna].astype(float) - obtenido_ord[columna].astype(float)).abs()
        base = esperado_ord[columna].astype(float).abs().clip(lower=1e-9)
        diferencia_relativa = (diferencia / base).max()
        assert diferencia_relativa < TOLERANCIA, f"{columna}: diferencia relativa {diferencia_relativa} en {fecha_iso}"
