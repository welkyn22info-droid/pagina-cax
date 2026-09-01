"""Concurrencia (sección 17): dos ejecuciones simultáneas del mismo
proceso y fecha — la segunda debe rechazarse con un mensaje claro."""
import io
from concurrent.futures import ThreadPoolExecutor


def test_doble_ejecucion_simultanea_se_rechaza(cliente, token_analista):
    for tipo, contenido in (
        ("posiciones", b"PORTAFOLIO|NEMOTECNICO|NOMINAL\nP1|TESJUL27|100,00\n"),
        ("precios", b"NEMOTECNICO|PRECIO_LIMPIO\nTESJUL27|98,50\n"),
    ):
        cliente.post(
            "/cargas", headers={"Authorization": f"Bearer {token_analista}"},
            files={"archivo": ("f.txt", io.BytesIO(contenido), "text/plain")},
            data={"tipo_insumo": tipo, "fecha_datos": "2026-08-24"},
        )

    def disparar():
        return cliente.post(
            "/corridas", headers={"Authorization": f"Bearer {token_analista}"},
            json={"proceso": "valoracion", "fecha_datos": "2026-08-24", "parametros": {}},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        r1, r2 = list(pool.map(lambda _: disparar(), range(2)))

    resultados = sorted([r1.status_code, r2.status_code])
    assert resultados == [200, 409], (r1.text, r2.text)

    rechazada = r1 if r1.status_code == 409 else r2
    assert "en curso" in rechazada.json()["mensaje"]
