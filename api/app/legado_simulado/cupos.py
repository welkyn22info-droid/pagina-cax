"""Simulación de legado/cupos.py. Firma y columnas: DECISIONES.md §1.
Reglas de cálculo tomadas literalmente de la sección 14."""
import pandas as pd


def calcular_consumo_cupo(
    posiciones: pd.DataFrame, valoracion: pd.DataFrame, limites: pd.DataFrame, entidades: pd.DataFrame
) -> pd.DataFrame:
    total_portafolio = float(valoracion["valor_mercado"].sum()) if not valoracion.empty else 0.0

    val_por_instrumento = (
        valoracion.groupby("instrumento_cod")["valor_mercado"].sum() if not valoracion.empty else pd.Series(dtype=float)
    )

    exposicion_por_entidad: dict[tuple[str, str], float] = {}

    for _, pos in posiciones.iterrows():
        exposicion = float(val_por_instrumento.get(pos["instrumento_cod"], 0.0))
        for tipo, codigo in (("emisor", pos.get("emisor_cod")), ("contraparte", pos.get("contraparte_cod"))):
            if not codigo:
                continue
            clave = (tipo, codigo)
            exposicion_por_entidad[clave] = exposicion_por_entidad.get(clave, 0.0) + exposicion

    filas = []
    limites_por_entidad = {(row["tipo"], row["codigo_entidad"]): row for _, row in limites.iterrows()} if not limites.empty else {}
    entidades_por_clave = {(row["tipo"], row["codigo"]): row for _, row in entidades.iterrows()} if not entidades.empty else {}

    for clave, expuesto in exposicion_por_entidad.items():
        tipo, codigo = clave
        limite = limites_por_entidad.get(clave)
        maestro = entidades_por_clave.get(clave)

        if maestro is None:
            # El código no existe en core.emisor/contraparte: no hay id real
            # que registrar. Se reporta en el log de la corrida (sección 10)
            # en vez de insertar una fila con entidad_id inventado.
            print(f"Cupos: '{codigo}' ({tipo}) no está en el maestro; se omite de res.consumo_cupo.")
            continue

        entidad_id = int(maestro["entidad_id"])
        entidad_nombre = maestro["nombre"]

        if limite is None:
            filas.append({
                "tipo": tipo, "entidad_id": entidad_id, "entidad_nombre": entidad_nombre,
                "limite_id": None, "valor_limite": None, "valor_expuesto": round(expuesto, 4),
                "utilizacion": None, "estado": "SIN_LIMITE",
                "detalle": {"codigo_entidad": codigo},
            })
            continue

        valor_limite = float(limite["valor_limite"])
        if limite["base"] == "porcentaje_portafolio":
            valor_limite_monto = valor_limite * total_portafolio
        else:
            valor_limite_monto = valor_limite

        utilizacion = (expuesto / valor_limite_monto) if valor_limite_monto else 0.0
        umbral = float(limite["umbral_alerta"])
        if utilizacion > 1.0:
            estado = "EXCEDIDO"
        elif utilizacion >= umbral:
            estado = "ALERTA"
        else:
            estado = "OK"

        filas.append({
            "tipo": tipo, "entidad_id": entidad_id, "entidad_nombre": entidad_nombre,
            "limite_id": int(limite["limite_id"]), "valor_limite": round(valor_limite_monto, 4),
            "valor_expuesto": round(expuesto, 4), "utilizacion": round(utilizacion, 6), "estado": estado,
            "detalle": {"codigo_entidad": codigo, "base": limite["base"]},
        })

    return pd.DataFrame(filas)
