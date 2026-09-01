"""Catálogo de procesos disponibles. Agregar un módulo nuevo (IRL, expo-
sición crediticia...) es agregar una entrada aquí y su envoltorio — nada
más cambia en el motor (sección 2, advertencia "Diseñar para lo que viene")."""
from app.motor.procesos import cupos, funding_ratio, pasivo, valoracion

PROCESOS = {
    "valoracion": {
        "nombre": "Valoración de activos",
        "modulo": "valoracion",
        "ejecutar": valoracion.ejecutar,
        "tabla_resultado": "res.valoracion",
    },
    "pasivo": {
        "nombre": "Cálculo de pasivo",
        "modulo": "pasivo",
        "ejecutar": pasivo.ejecutar,
        "tabla_resultado": "res.pasivo",
    },
    "funding_ratio": {
        "nombre": "Funding ratio",
        "modulo": "funding_ratio",
        "ejecutar": funding_ratio.ejecutar,
        "tabla_resultado": "res.funding_ratio",
    },
    "cupos": {
        "nombre": "Cupos de emisor y contraparte",
        "modulo": "cupos",
        "ejecutar": cupos.ejecutar,
        "tabla_resultado": "res.consumo_cupo",
    },
}
