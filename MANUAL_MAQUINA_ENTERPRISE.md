# Manual para levantar la plataforma en la máquina enterprise

Este documento es para quien (persona o Claude) reciba el repositorio en la
máquina con acceso a los datos y al código real de CAXDAC. Complementa —no
reemplaza— el mensaje oficial que ya trae la especificación
(`especificacion/especificacion-plataforma-riesgo.html`, sección final
"Mensaje para la máquina enterprise — créditos limitados, solo estas tres
tareas"). Ese mensaje sigue siendo la guía de las tres tareas grandes
(leer el código legado, crear las tablas, conectar las consultas). Este
manual da el paso a paso concreto de la Tarea 2 y 3, actualizado con todo
lo que se agregó después de que se escribió ese mensaje.

## Qué cambió desde el mensaje original de la especificación

El mensaje original dice "confirma que los cinco esquemas y todas las
tablas de la sección 6 existen". Eso ya no es todo — se agregó, a pedido
del usuario y fuera del alcance de las 21 secciones originales:

- **Confirmación de resultados antes de que sean oficiales**
  (`proc.resultado_borrador`, estado `PENDIENTE_CONFIRMACION` de una
  corrida) — el cálculo del legado ya no cae directo en `res.*`; un
  revisor lo audita y confirma. Ver `DECISIONES.md`, decisión 17.
- **Curvas de mercado** (`staging.curva_nodo`), un insumo nuevo con su
  propio panel de carga, gráfica comparativa, y columnas de auditoría
  directas en la tabla (`fecha_cargue`, `usuario_carga`, `anulado`,
  `usuario_anulado`). Ver decisiones 18 a 25.
- **Anulación de una carga** (`staging.carga.anulada_por/anulada_en/
  motivo_anulacion`), disponible para cualquier tipo de insumo, no solo
  curvas.

Todo esto ya está escrito como migraciones — no hay que construirlo a
mano, solo ejecutarlas en orden (abajo). El detalle de *por qué* cada
cosa quedó como quedó está en `DECISIONES.md` — vale la pena leerlo antes
de tocar algo si algo no calza con lo que se espera.

## Paso a paso

### 1. Traer el código

```bash
git clone https://github.com/welkyn22info-droid/pagina-cax.git
cd pagina-cax
git checkout claude/project-review-tzy6ak   # o main, si ya se hizo el merge
```

Solo el código viaja por git. **Nada de esto se sube nunca desde acá**:
`api/legado/*.py`, cualquier archivo bajo `datos/`, `CURVAS/` — todo
queda fuera por `.gitignore` a propósito (sección 18). Los datos reales
de CAXDAC se cargan *ahí*, en esta máquina, no se traen de la de
suscripción.

### 2. Postgres: rol y base de datos

Con un superusuario de Postgres:

```sql
CREATE ROLE app_riesgo LOGIN PASSWORD 'una_contraseña_propia_de_esta_máquina';
CREATE DATABASE riesgo_prod OWNER postgres;
```

**No reutilizar ninguna contraseña de la máquina de suscripción.** La que
se usó ahí (`Welkyn22`) era solo para pruebas locales con datos
sintéticos.

### 3. Migraciones — en orden, todas

```bash
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/001_esquemas_y_roles.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/002_maestros.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/003_staging.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/004_procesos_y_corridas.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/005_resultados.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/006_permisos_rls.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/007_publicacion_acuse.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/008_cupos.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/009_visibilidad_publicado.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/010_rls_escritura.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/011_publicacion_sin_recursion.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/012_resultado_borrador.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/013_curvas.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/014_indice_anulacion.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/015_curva_nodo_ajustes.sql
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f db/migraciones/016_curva_nodo_auditoria_directa.sql
```

(Revisar `db/migraciones/` por si hay archivos más nuevos que estos 16 —
este manual se escribió hasta la 016.)

### 4. Permisos del rol de aplicación

```bash
psql -U postgres -h localhost -d riesgo_prod -v ON_ERROR_STOP=1 -f operacion/preparar_rol.sql
```

Este script asume que `app_riesgo` ya existe (paso 2). Es idempotente —
correrlo de nuevo no rompe nada si ya se corrió antes.

### 5. NO cargar las semillas sintéticas

`db/semillas/usuarios_iniciales.sql` y `db/semillas/maestros_ejemplo.sql`
son **datos ficticios de prueba** — usuarios con una contraseña conocida
compartida (`Cambiar123456`) y emisores/instrumentos inventados
("Ejemplo S.A.", "ficticio"). Sirvieron para probar el flujo completo en
la máquina de suscripción sin datos reales. **No correr estos archivos
acá.**

### 6. Crear el primer usuario real (admin)

No hay una forma de crear el primer usuario por la API (`POST
/admin/usuarios` ya exige estar logueado como admin — problema del
huevo y la gallina). Se resuelve una sola vez, directo en la base:

```bash
# Generar el hash de una clave real y fuerte (no la de este ejemplo)
cd api
.venv/Scripts/python.exe -c "from app.seguridad import hash_clave; print(hash_clave('LA_CLAVE_REAL_AQUI'))"
```

Con el hash que imprime, insertar el usuario:

```sql
INSERT INTO core.usuario (correo, nombre, hash_clave, rol, activo, debe_cambiar_clave)
VALUES ('correo.real@caxdac.com.co', 'Nombre real', '<hash generado arriba>', 'admin', true, false);
```

Desde ese usuario ya se puede entrar a la aplicación y crear los demás
usuarios reales (analistas, revisor, consulta) desde el panel Usuarios,
sin volver a tocar SQL directo.

### 7. Configurar la API (`api/.env`)

```
DATABASE_URL=postgresql+psycopg://app_riesgo:<la_contraseña_del_paso_2>@localhost:5432/riesgo_prod
SECRETO_JWT=<generar uno nuevo — nunca reusar el de la máquina de suscripción>
RUTA_ARCHIVOS_ORIGINALES=<carpeta local de este servidor para los archivos originales subidos>
```

Para generar un `SECRETO_JWT` nuevo: `python -c "import secrets; print(secrets.token_hex(32))"`.

### 8. Levantar y confirmar

```bash
cd api
.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`GET http://localhost:8000/salud` debe responder `{"estado":"ok"}`. Con
eso, la API funciona exactamente igual que en la máquina de suscripción —
no hay nada en el código que dependa de dónde corre; todo lo que cambia
es la configuración de `.env` de este paso y del paso 7.

Para el frontend: `cd web && npm install && npm run build && npm run
start` (modo producción — más estable para dejar corriendo que `npm run
dev`, que solo conviene mientras se está editando código activamente).

### 9. Cargar los datos reales

Todo insumo real (posiciones, precios, flujos de pasivo, curvas de
mercado) se carga **desde el panel web** (`/cargas`), con el usuario real
creado en el paso 6 — igual que se probó en la máquina de suscripción con
datos sintéticos, pero acá con archivos reales de CAXDAC. Los maestros
(emisores, contrapartes, instrumentos, límites de cupo) se cargan desde
los formularios de administración del panel, o por lote directo a
`core.*` si el volumen inicial es grande — eso es una decisión de quien
opera la plataforma ahí, no algo que este manual deba prescribir.

### 10. Cuando llegue el código Python real

Sigue la Tarea 1 y 3 del mensaje de la especificación: el código va en
`api/legado/{valoracion,pasivo,funding,cupos}.py`, con las firmas exactas
descritas en `DECISIONES.md` (decisión 1). El cambio en el resto del
código es una sola línea de import por archivo, en cada
`api/app/motor/procesos/*.py` — de `app.legado_simulado.X` a `legado.X`.
Nada más debería necesitar tocarse.

## Resumen de lo que sí viaja y lo que no

| Qué | ¿Viaja por git? |
|---|---|
| Código (`api/app`, `web/`, migraciones, este manual) | Sí |
| `DECISIONES.md`, especificación | Sí |
| Datos reales de CAXDAC, código legado real | No — nunca, `.gitignore` lo impide |
| Base de datos de la máquina de suscripción | No — ni falta que hace, las migraciones la reconstruyen desde cero |
| Contraseñas, `SECRETO_JWT`, cualquier `.env` | No — cada máquina tiene los suyos |
