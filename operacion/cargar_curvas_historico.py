"""Backfill de curvas históricas (decisión 18): el archivo real de origen
viene ANCHO (una columna por fecha) porque así es como lo exporta la fuente,
pero el insumo diario normal —y la tabla— son en formato LARGO. Este script
pivotea el archivo ancho y sube un archivo por fecha contra el endpoint real
POST /cargas, para que cada día quede con su propia trazabilidad (carga_id,
hash, usuario) exactamente igual que si alguien lo hubiera subido a mano.

Uso:
    .venv/Scripts/python.exe operacion/cargar_curvas_historico.py \
        "CURVAS/agosto uvr tes.csv" --correo admin@riesgo.local --clave ... \
        [--base http://localhost:8000]
"""
from __future__ import annotations

import argparse
import io
import sys

import httpx
import pandas as pd


def pivotear(ruta_csv: str) -> dict[str, pd.DataFrame]:
    """Lee el CSV ancho (Curva;Plazo en días;<fecha1>;<fecha2>;...) y
    devuelve un DataFrame por fecha, en formato largo (curva, nodo, valor)."""
    df = pd.read_csv(ruta_csv, sep=";", encoding="utf-8")
    columnas_fecha = [c for c in df.columns if c not in ("Curva", "Plazo en días")]

    largo = df.melt(
        id_vars=["Curva", "Plazo en días"],
        value_vars=columnas_fecha,
        var_name="fecha_original",
        value_name="valor",
    )
    # ISO primero (aaaa-mm-dd), dd/mm/aaaa si no calza — con dayfirst=True
    # aplicado directo a una fecha ISO, pandas puede invertir día y mes
    # cuando ambos son ≤12 (se comprobó en vivo con columnas "2026-07-01").
    fechas = pd.to_datetime(largo["fecha_original"], format="%Y-%m-%d", errors="coerce")
    faltantes = fechas.isna()
    if faltantes.any():
        fechas.loc[faltantes] = pd.to_datetime(largo.loc[faltantes, "fecha_original"], dayfirst=True, errors="coerce")
    largo["fecha_iso"] = fechas.dt.strftime("%Y-%m-%d")

    por_fecha: dict[str, pd.DataFrame] = {}
    for fecha_iso, grupo in largo.groupby("fecha_iso"):
        salida = grupo[["Curva", "Plazo en días", "valor"]].rename(
            columns={"Curva": "curva", "Plazo en días": "nodo"}
        )
        por_fecha[fecha_iso] = salida.sort_values("nodo").reset_index(drop=True)
    return por_fecha


def subir(base: str, token: str, fecha_iso: str, df: pd.DataFrame) -> dict:
    buffer = io.StringIO()
    df.to_csv(buffer, sep=";", index=False, header=["Curva", "Nodo", "Valor"])
    contenido = buffer.getvalue().encode("utf-8")

    with httpx.Client(base_url=base, timeout=60) as cliente:
        r = cliente.post(
            "/cargas",
            headers={"Authorization": f"Bearer {token}"},
            files={"archivo": (f"curvas_{fecha_iso.replace('-', '')}.csv", contenido, "text/csv")},
            data={"tipo_insumo": "curvas", "fecha_datos": fecha_iso},
        )
        r.raise_for_status()
        return r.json()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ruta_csv")
    ap.add_argument("--correo", required=True)
    ap.add_argument("--clave", required=True)
    ap.add_argument("--base", default="http://localhost:8000")
    args = ap.parse_args()

    with httpx.Client(base_url=args.base, timeout=30) as cliente:
        r = cliente.post("/auth/login", json={"correo": args.correo, "clave": args.clave})
        r.raise_for_status()
        token = r.json()["token"]

    por_fecha = pivotear(args.ruta_csv)
    print(f"{len(por_fecha)} fechas encontradas en el archivo.")

    for fecha_iso in sorted(por_fecha):
        resultado = subir(args.base, token, fecha_iso, por_fecha[fecha_iso])
        estado = resultado.get("estado", "?")
        filas = resultado.get("filas_validas", "?")
        dup = " (ya existía)" if resultado.get("duplicado") else ""
        print(f"  {fecha_iso}: {estado} — {filas} filas{dup}")

    print("Listo.")


if __name__ == "__main__":
    sys.exit(main())
