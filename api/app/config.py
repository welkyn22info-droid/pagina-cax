from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://app_riesgo:clave_prueba_local@localhost:5432/riesgo_test"
    secreto_jwt: str = "cambiar-en-produccion-nunca-usar-este-valor"
    jwt_horas_vigencia: int = 8
    zona_horaria: str = "America/Bogota"

    clave_min_longitud: int = 12
    intentos_max_fallidos: int = 5
    bloqueo_minutos: int = 15
    sesion_inactividad_minutos: int = 30

    corrida_timeout_minutos: int = 30

    ruta_archivos_originales: str = "/datos/originales"


config = Configuracion()
