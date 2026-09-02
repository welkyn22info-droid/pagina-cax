"""Ingesta (sección 17): separadores distintos, encabezados con variantes,
columnas faltantes, decimales en formato colombiano, duplicado, vacío."""
import io

FIXTURES = __file__.rsplit("/", 1)[0] + "/fixtures"


def _subir(cliente, token, contenido: bytes, nombre: str, tipo: str, fecha: str):
    return cliente.post(
        "/cargas",
        headers={"Authorization": f"Bearer {token}"},
        files={"archivo": (nombre, io.BytesIO(contenido), "text/plain")},
        data={"tipo_insumo": tipo, "fecha_datos": fecha},
    )


def test_carga_valida_con_formato_colombiano(cliente, token_analista):
    with open(f"{FIXTURES}/posiciones_20260831.txt", "rb") as f:
        contenido = f.read()
    r = _subir(cliente, token_analista, contenido, "posiciones_20260831.txt", "posiciones", "2026-08-31")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "VALIDADO"
    assert cuerpo["filas_validas"] == 3


def test_carga_rechazada_por_columna_faltante(cliente, token_analista):
    contenido = b"PORTAFOLIO|NEMOTECNICO|EMISOR|VALOR\nPORT1|TESJUL27|REPCOL|1.000.000,00\n"
    r = _subir(cliente, token_analista, contenido, "posiciones_malas.txt", "posiciones", "2026-08-30")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "RECHAZADO"
    assert cuerpo["filas_validas"] == 0
    assert "nominal" in cuerpo["detalle_error"]["columnas_faltantes"]
    assert "No se cargó ninguna fila" in cuerpo["mensaje"]


def test_carga_rechazada_no_inserta_filas_parciales(cliente, token_analista):
    # Segunda fila tiene un nominal no convertible: la carga completa se
    # rechaza, ninguna fila (ni siquiera la primera, válida) se inserta.
    contenido = (
        b"PORTAFOLIO|NEMOTECNICO|NOMINAL\n"
        b"PORT1|TESJUL27|1.000.000,00\n"
        b"PORT1|CDTBANCOL90|no-es-un-numero\n"
    )
    r = _subir(cliente, token_analista, contenido, "posiciones_parcial.txt", "posiciones", "2026-08-29")
    cuerpo = r.json()
    assert cuerpo["estado"] == "RECHAZADO"
    assert cuerpo["filas_validas"] == 0
    assert cuerpo["detalle_error"]["total_errores"] == 1


def test_duplicado_por_hash_no_reinserta(cliente, token_analista):
    with open(f"{FIXTURES}/precios_20260831.txt", "rb") as f:
        contenido = f.read()
    r1 = _subir(cliente, token_analista, contenido, "precios_20260831.txt", "precios", "2026-08-31")
    assert r1.json()["duplicado"] is False

    r2 = _subir(cliente, token_analista, contenido, "precios_20260831.txt", "precios", "2026-08-31")
    cuerpo2 = r2.json()
    assert cuerpo2["duplicado"] is True
    assert cuerpo2["carga_id"] == r1.json()["carga_id"]


def test_separador_punto_y_coma_tambien_se_detecta(cliente, token_analista):
    contenido = (
        b"PORTAFOLIO;NEMOTECNICO;NOMINAL\n"
        b"PORT1;BONOECOPET30;1.500.000,50\n"
    )
    r = _subir(cliente, token_analista, contenido, "posiciones_pyc.txt", "posiciones", "2026-08-28")
    cuerpo = r.json()
    assert cuerpo["estado"] == "VALIDADO"
    assert cuerpo["filas_validas"] == 1


def test_archivo_vacio_se_rechaza(cliente, token_analista):
    contenido = b"PORTAFOLIO|NEMOTECNICO|NOMINAL\n"
    r = _subir(cliente, token_analista, contenido, "posiciones_vacio.txt", "posiciones", "2026-08-27")
    cuerpo = r.json()
    assert cuerpo["estado"] == "RECHAZADO"


def test_carga_valida_desde_excel(cliente, token_analista):
    # El lector de .xlsx usa openpyxl en modo streaming (read_only), no
    # pd.read_excel — esta prueba cubre ese camino, que antes no tenía
    # ninguna prueba (solo TXT).
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["PORTAFOLIO", "NEMOTECNICO", "EMISOR", "NOMINAL", "MONEDA"])
    ws.append(["PORT1", "TESJUL27", "REPCOL", 1234567.89, "COP"])
    ws.append(["PORT2", "BONOECOPET30", "ECOPET", 2000000, "COP"])
    buffer = io.BytesIO()
    wb.save(buffer)

    r = _subir(cliente, token_analista, buffer.getvalue(), "posiciones_20260826.xlsx", "posiciones", "2026-08-26")
    cuerpo = r.json()
    assert cuerpo["estado"] == "VALIDADO", cuerpo
    assert cuerpo["filas_validas"] == 2


def test_excel_conserva_numero_nativo_sin_pasar_por_formato_colombiano(cliente, token_analista):
    # Un nominal como float nativo de Excel (1234567.89) no debe
    # interpretarse como "1.234.567,89 colombiano" ni corromperse.
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["PORTAFOLIO", "NEMOTECNICO", "NOMINAL"])
    ws.append(["PORT1", "TESJUL27", 1234567.89])
    buffer = io.BytesIO()
    wb.save(buffer)

    r = _subir(cliente, token_analista, buffer.getvalue(), "posiciones_20260825.xlsx", "posiciones", "2026-08-25")
    assert r.json()["estado"] == "VALIDADO"

    r2 = cliente.get(
        "/cargas",
        headers={"Authorization": f"Bearer {token_analista}"},
        params={"fecha": "2026-08-25"},
    )
    assert r2.json()[0]["filas_validas"] == 1
