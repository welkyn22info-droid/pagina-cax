import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.rutas import admin, auth, cargas, corridas, cupos, publicaciones, resultados

logging.basicConfig(level=logging.INFO, format='{"nivel":"%(levelname)s","modulo":"%(name)s","mensaje":"%(message)s"}')


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    from app.motor.ejecutor import marcar_corridas_colgadas

    marcados = marcar_corridas_colgadas()
    if marcados:
        logging.getLogger("arranque").info(f"{marcados} corridas colgadas marcadas como ERROR al arrancar.")
    yield


app = FastAPI(title="Plataforma de riesgo — API", version="0.1.0", lifespan=ciclo_de_vida)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def manejador_http(request: Request, exc: HTTPException):
    detalle = exc.detail
    if isinstance(detalle, dict) and "error" in detalle:
        cuerpo = detalle
    else:
        cuerpo = {"error": "error", "mensaje": str(detalle), "detalle": {}}
    return JSONResponse(status_code=exc.status_code, content=cuerpo)


@app.exception_handler(RequestValidationError)
async def manejador_validacion(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "datos_invalidos",
            "mensaje": "Los datos enviados no son válidos.",
            "detalle": {"errores": exc.errors()},
        },
    )


@app.get("/salud")
def salud():
    return {"estado": "ok"}


app.include_router(auth.router)
app.include_router(cargas.router)
app.include_router(corridas.router)
app.include_router(corridas.procesos_router)
app.include_router(resultados.router)
app.include_router(cupos.router)
app.include_router(publicaciones.router)
app.include_router(admin.router)
