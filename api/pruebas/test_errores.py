"""Errores (sección 17): un proceso que lanza excepción a mitad de camino
no debe dejar filas parciales en res."""
import io
import time

import pandas as pd
import psycopg

from app.config import config


def test_error_a_mitad_de_camino_no_deja_filas_parciales(cliente, token_analista, monkeypatch):
    from app.motor.procesos import pasivo as modulo_pasivo

    def calculo_con_fila_invalida(flujos, tasa_descuento, fecha_valoracion):
        # La segunda fila tiene un valor no numérico en una columna numeric:
        # falla al escribir, después de que la primera ya se preparó para
        # insertarse en el mismo lote.
        return pd.DataFrame([
            {"concepto": "A", "valor_presente": 1000.0, "duracion": 1.0, "tasa_descuento": tasa_descuento, "metricas_extra": None},
            {"concepto": "B", "valor_presente": "no-es-un-numero", "duracion": 1.0, "tasa_descuento": tasa_descuento, "metricas_extra": None},
        ])

    monkeypatch.setattr(modulo_pasivo, "calcular_pasivo", calculo_con_fila_invalida)

    cliente.post(
        "/cargas", headers={"Authorization": f"Bearer {token_analista}"},
        files={"archivo": ("f.txt", io.BytesIO(b"CONCEPTO|FECHA_FLUJO|MONTO\nA|2026-09-30|100.000,00\n"), "text/plain")},
        data={"tipo_insumo": "flujos_pasivo", "fecha_datos": "2026-08-25"},
    )

    r = cliente.post(
        "/corridas", headers={"Authorization": f"Bearer {token_analista}"},
        json={"proceso": "pasivo", "fecha_datos": "2026-08-25", "parametros": {}},
    )
    corrida_id = r.json()["corrida_id"]

    detalle = None
    for _ in range(50):
        detalle = cliente.get(f"/corridas/{corrida_id}", headers={"Authorization": f"Bearer {token_analista}"}).json()
        if detalle["estado"] in ("OK", "ERROR"):
            break
        time.sleep(0.1)

    assert detalle["estado"] == "ERROR"
    assert detalle["mensaje_error"]

    dsn = config.database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM res.pasivo WHERE corrida_id = %s", (corrida_id,))
        assert cur.fetchone()[0] == 0
