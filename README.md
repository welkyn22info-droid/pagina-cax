# Plataforma de riesgo

Plataforma interna que reemplaza el flujo actual de hojas de cálculo,
scripts sueltos y envío de indicadores por correo: una sola carga de
insumos, ejecución trazable de valoración, pasivo, funding ratio y cupos,
y publicación de resultados con acuse de lectura.

La especificación completa está en el documento de origen del proyecto
(secciones 1 a 21). Este README cubre solo lo operativo: cómo levantar el
proyecto y correr las pruebas. Para las decisiones que se apartan o
precisan la especificación, ver **`DECISIONES.md`**.

## Estado de este repositorio

Esta es la máquina de **suscripción** (sección 18 y 21 de la
especificación): construye toda la plataforma con datos sintéticos y
funciones de cálculo simuladas, sin acceso al código Python real ni a los
datos de CAXDAC. `api/legado/` está vacío a propósito — ahí llega después
el código real desde la máquina enterprise, junto con `README_LEGADO.md` y
`contrato_datos.md`. Mientras tanto, `api/app/legado_simulado/` cumple el
mismo contrato (ver `DECISIONES.md`, decisión 1) para poder probar el
flujo completo de punta a punta.

## Estructura

```
db/migraciones/     11 migraciones SQL, numeradas e incrementales
db/semillas/         usuarios y maestros sintéticos
api/app/              FastAPI: auth, ingesta, motor de ejecución, rutas
api/app/legado_simulado/  funciones de cálculo simuladas (ver arriba)
api/legado/           vacío — código real, cuando llegue
api/pruebas/           pytest: ingesta, paridad, permisos, trazabilidad,
                        concurrencia, errores
web/                   Next.js 15 (App Router) + Tailwind 4 + TanStack Query
proxy/nginx.conf       proxy inverso para producción
operacion/             respaldo.sh, restaurar.sh, preparar_rol.sql
docker-compose.yml     los cuatro servicios (db, api, web, proxy)
```

## Desarrollo local, sin Docker

Requiere Postgres 16, Python 3.11+ y Node 22+.

### Base de datos

```bash
sudo -u postgres createdb riesgo_dev
for f in db/migraciones/*.sql; do
  sudo -u postgres psql -d riesgo_dev -v ON_ERROR_STOP=1 -f "$f"
done
sudo -u postgres psql -d riesgo_dev -f db/semillas/usuarios_iniciales.sql
sudo -u postgres psql -d riesgo_dev -f db/semillas/maestros_ejemplo.sql

# Rol de aplicación sin BYPASSRLS (sección 7 y 15):
sudo -u postgres psql -d riesgo_dev -c \
  "CREATE ROLE app_riesgo LOGIN PASSWORD 'clave_local';"
sudo -u postgres psql -d riesgo_dev -f operacion/preparar_rol.sql
```

Todos los usuarios sembrados usan la contraseña `Cambiar123456` y deben
cambiarla en el primer ingreso (`debe_cambiar_clave = true`).

### API

```bash
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.ejemplo .env  # o crear .env con DATABASE_URL apuntando a riesgo_dev
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd web
npm install
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
npm run dev
```

Abrir `http://localhost:3000`.

## Con Docker Compose (referencia para producción)

```bash
cp .env.ejemplo .env   # completar con claves reales
docker compose up -d --build
# una sola vez, contra el Postgres del contenedor:
docker compose exec -T db psql -U $DB_SUPERUSUARIO -c \
  "CREATE ROLE app_riesgo LOGIN PASSWORD '<<DB_CLAVE_APP>>';"
docker compose exec -T db psql -U $DB_SUPERUSUARIO -d riesgo \
  -f /dev/stdin < operacion/preparar_rol.sql
```

Las migraciones en `db/migraciones/` se aplican automáticamente al primer
arranque del contenedor `db` (montadas en
`/docker-entrypoint-initdb.d`), pero el rol `app_riesgo` y sus `GRANT` se
configuran aparte (sección 15 y 19: esto es tarea de la máquina enterprise
contra el servidor real).

## Pruebas

```bash
cd api
source .venv/bin/activate
python3 -m pytest        # recrea riesgo_test desde cero en cada corrida
```

Cubre ingesta (separadores, formato colombiano, columnas faltantes,
duplicados), paridad entre la plataforma y el cálculo directo, permisos
por rol (incluida una verificación a nivel de Postgres, no solo de API),
trazabilidad de insumos por corrida, concurrencia (doble ejecución
simultánea) y ausencia de filas parciales cuando un proceso falla a mitad
de camino — ver sección 17.

## Respaldos

`operacion/respaldo.sh` (diario, cron en `operacion/cron.d/respaldo`) y
`operacion/restaurar.sh`. Ver sección 16.

## Siguiente paso: máquina enterprise

Cuando el código real de CAXDAC esté documentado (`contrato_datos.md` y
`README_LEGADO.md` en `api/legado/`), sustituir en cada archivo de
`api/app/motor/procesos/` la línea de import desde
`app.legado_simulado.*` por `legado.*` (una sola línea por archivo — ver
`DECISIONES.md`, decisión 2) y correr `api/pruebas/test_paridad_legado.py`
contra datos reales.
