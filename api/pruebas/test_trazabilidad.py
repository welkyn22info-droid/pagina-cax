"""Trazabilidad (sección 17): dada una corrida, reconstruir exactamente
qué cargas usó y verificar que los hashes coinciden con los archivos."""
import hashlib
import io


def test_corrida_registra_las_cargas_exactas_que_uso(cliente, token_analista):
    posiciones = b"PORTAFOLIO|NEMOTECNICO|NOMINAL\nP1|TESJUL27|123.456,00\n"
    precios = b"NEMOTECNICO|PRECIO_LIMPIO\nTESJUL27|98,50\n"

    r1 = cliente.post(
        "/cargas", headers={"Authorization": f"Bearer {token_analista}"},
        files={"archivo": ("pos.txt", io.BytesIO(posiciones), "text/plain")},
        data={"tipo_insumo": "posiciones", "fecha_datos": "2026-08-23"},
    )
    r2 = cliente.post(
        "/cargas", headers={"Authorization": f"Bearer {token_analista}"},
        files={"archivo": ("pre.txt", io.BytesIO(precios), "text/plain")},
        data={"tipo_insumo": "precios", "fecha_datos": "2026-08-23"},
    )
    carga_pos_id = r1.json()["carga_id"]
    carga_pre_id = r2.json()["carga_id"]

    r = cliente.post(
        "/corridas", headers={"Authorization": f"Bearer {token_analista}"},
        json={"proceso": "valoracion", "fecha_datos": "2026-08-23", "parametros": {}},
    )
    corrida_id = r.json()["corrida_id"]

    import time
    for _ in range(50):
        detalle = cliente.get(f"/corridas/{corrida_id}", headers={"Authorization": f"Bearer {token_analista}"}).json()
        if detalle["estado"] in ("OK", "ERROR"):
            break
        time.sleep(0.1)

    assert detalle["estado"] == "OK"
    cargas_usadas = {i["carga_id"] for i in detalle["insumos"] if i["carga_id"] is not None}
    assert cargas_usadas == {carga_pos_id, carga_pre_id}

    # El hash registrado en cada carga debe coincidir con el hash real del
    # contenido subido — es lo que permite reconstruir con qué insumo
    # exacto se produjo el número, incluso meses después.
    for insumo in detalle["insumos"]:
        esperado = hashlib.sha256(posiciones if insumo["carga_id"] == carga_pos_id else precios).hexdigest()
        assert insumo["hash_sha256"] == esperado
