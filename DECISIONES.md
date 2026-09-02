# Decisiones que se apartan o precisan la especificación

Registro exigido por la sección 21 de `especificacion-plataforma-riesgo.html`:
"Toda decisión que se aparte de esta especificación se registra en un archivo
`DECISIONES.md` con la razón."

---

## 1. No existe `contrato_datos.md` real todavía

La especificación (sección 18 y 21) asume que esta máquina de suscripción
recibe `contrato_datos.md` y `README_LEGADO.md` ya producidos por la máquina
enterprise a partir del código Python real de CAXDAC. Esa tarea (Tarea 1 de
la sección 21) no se ha ejecutado — este repositorio nace vacío.

**Decisión:** construir igualmente toda la plataforma (secciones 1 a 17)
usando un contrato inferido directamente de los ejemplos que la propia
especificación ya deja explícitos en las secciones 6 (modelo de datos),
8 (envoltorios de ejemplo para `valoracion` y `funding_ratio`), 9 (esquema
declarativo de `posiciones`) y 14 (reglas de cupos). Ese contrato se deja
escrito abajo. Cuando llegue el `contrato_datos.md` real desde la máquina
enterprise, se compara contra esta sección y se ajustan solo las diferencias
— la estructura de envoltorios (sección 8, `motor/io.py`) no debería cambiar.

### Contrato inferido por proceso

**`valoracion.calcular_valoracion(posiciones, precios) -> DataFrame`**
- `posiciones`: `portafolio, instrumento_cod, emisor_cod, contraparte_cod, nominal, cantidad, costo_amortizado, moneda`
- `precios`: `instrumento_cod, precio_limpio, precio_sucio, tasa, fuente`
- devuelve: `portafolio, instrumento_cod, emisor_cod, nominal, precio_usado, valor_mercado, valor_causado, duracion, moneda, metricas_extra`
  (columnas de `res.valoracion`, sección 6)

**`pasivo.calcular_pasivo(flujos, tasa_descuento) -> DataFrame`**
- `flujos`: `concepto, fecha_flujo, monto, moneda`
- `tasa_descuento`: parámetro de la corrida (sección 14: "la tasa o curva de
  descuento debe poder pasarse como parámetro de la corrida")
- devuelve: `concepto, valor_presente, duracion, tasa_descuento, metricas_extra`
  (columnas de `res.pasivo`)

**`funding.calcular_funding_ratio(activos, pasivos) -> (ratio, superavit_deficit)`**
- firma tomada literalmente del ejemplo de la sección 8.

**`cupos.calcular_consumo_cupo(posiciones, valoracion, limites, entidades) -> DataFrame`**
- `limites`: filas de `core.limite_cupo` vigentes a `fecha_datos`
- `entidades`: maestro de emisores y contrapartes (`tipo, entidad_id, codigo, nombre`)
  — necesario para que una entidad **sin** límite parametrizado igual tenga
  un `entidad_id` real que registrar (`res.consumo_cupo.entidad_id` es
  `NOT NULL`); sin este insumo no hay forma de resolver ese id cuando no
  existe fila en `core.limite_cupo` para esa entidad.
- devuelve: `tipo, entidad_id, entidad_nombre, limite_id, valor_limite, valor_expuesto, utilizacion, estado, detalle`
  (columnas de `res.consumo_cupo`), respetando las reglas de la sección 14:
  exposición sobre valor de mercado, límite vigente a la fecha de datos,
  entidad sin límite se reporta igual, estado `OK/ALERTA/EXCEDIDO/SIN_LIMITE`.
  Una posición con `emisor_cod`/`contraparte_cod` que no existe en
  `core.emisor`/`core.contraparte` se omite del resultado con una línea en
  el log de la corrida — no hay id real que registrar para ella.

## 2. Ubicación del código simulado: `api/app/legado_simulado/`, no `api/legado/`

La instrucción de la sección 21 para esta máquina es explícita: *"No crees
nada dentro de `api/legado/`: esa carpeta llega después, desde la otra
máquina, con el código real."* Por eso las funciones de cálculo simuladas
para poder probar el flujo completo **no viven en `api/legado/`** — esa
carpeta queda vacía (solo con `LEEME.md`, que no es código) — sino en
`api/app/legado_simulado/`, con exactamente los mismos nombres de función y
firmas del contrato de arriba.

Cada envoltorio en `api/app/motor/procesos/` importa hoy desde
`app.legado_simulado.*`. El cambio para producción, tal como pide la
sección 21 ("sustituir una sola línea de import"), es cambiar esa única
línea en cada envoltorio a `from legado.<modulo> import <funcion>` una vez
`api/legado/` reciba el código real. Ningún otro archivo debe cambiar.

## 3. `api/legado/*.py` y `datos/` reales, excluidos por `.gitignore`

Tal como exige la sección 18, `api/legado/*.py` y cualquier archivo bajo
`datos/` quedan en `.gitignore` desde el primer commit, aunque hoy no exista
ningún archivo real ahí — para que el día que la máquina enterprise coloque
el código real, nunca se suba por accidente a este repositorio compartido.

## 4. Estado `SIN_LIMITE` en `res.consumo_cupo`

La sección 6 enumera los estados de cupo como `'OK' | 'ALERTA' | 'EXCEDIDO'`,
pero la sección 14 exige explícitamente que una entidad sin límite
parametrizado "aparece en la vista con la exposición calculada y la marca de
'sin límite parametrizado'. No se omite." Esas dos frases son incompatibles
si el estado solo admite tres valores y `valor_limite`/`utilizacion` no
pueden ser nulos. Se agrega un cuarto estado, `SIN_LIMITE`, y se permite que
`valor_limite` y `utilizacion` sean `NULL` en ese caso, para poder cumplir la
regla de la sección 14 sin omitir la fila.

## 5. `proc.corrida_insumo`: llave primaria no era válida en Postgres

El SQL literal de la sección 6 define
`PRIMARY KEY (corrida_id, COALESCE(carga_id,0), COALESCE(corrida_origen,0))`,
que Postgres rechaza: una `PRIMARY KEY` no admite expresiones, solo columnas.
Se cambia a un `id bigserial PRIMARY KEY` propio más un índice único por
expresión (`ux_corrida_insumo`) que preserva exactamente la misma regla de
unicidad que buscaba el diseño original, y un `CHECK` que exige que cada fila
tenga exactamente uno de `carga_id` / `corrida_origen` (nunca los dos ni
ninguno), que es lo que el comentario de la tabla ya daba por sentado.

## 6. `res.*.puede_ver` no distinguía "consulta = solo publicado"

La sección 6 muestra políticas RLS de ejemplo (`ver_valoracion`, `ver_fr`,
`ver_cupos`) que solo comprueban `core.puede('modulo','ver')`. Pero la matriz
de permisos de la sección 7 dice, para el rol `consulta`, "Ver: Solo
publicado" — distinto del resto de roles, que ven todo lo que su permiso
`puede_ver` cubre (necesitan verlo antes de publicarlo). Las políticas
literales del ejemplo no alcanzan a expresar esa distinción. Se agrega la
migración 009 (después de que existen las tablas de publicación) con
`core.puede_ver_resultado`, que aplica la restricción de publicación
únicamente al rol `consulta`.

## 7. RLS de escritura: la especificación solo mostraba políticas de `SELECT`

Las secciones 6 y 7 solo dan ejemplos de políticas `FOR SELECT`. Con RLS
habilitado, Postgres deniega por defecto cualquier comando (`INSERT`,
`UPDATE`) sobre una tabla si no existe una política que lo cubra —
incluso teniendo el `GRANT` de la sección 15. Sin esto, el motor de
ejecución no podría escribir ni una fila en `res.*`, ni la ingesta en
`staging.carga`, ni la publicación en `audit.publicacion/destinatario`.
Se agrega la migración 010 con las políticas de escritura que faltaban.
La autorización de fondo (quién puede cargar/ejecutar/publicar) ya se
comprueba en la API (`app/seguridad.py::requiere_permiso`) antes de
intentar la escritura; estas políticas son la traducción de esa misma
regla a nivel de fila, salvo en las tablas de resultados (`res.*`) y en
la actualización de `proc.corrida`, donde se dejan permisivas
(`WITH CHECK (true)`) porque solo las escribe el propio motor tras haber
pasado ya el chequeo de permiso — nunca directamente el usuario.

## 8. `GRANT` de la sección 15 no alcanzaba para crear usuarios, límites ni acuses

El script de la sección 15 solo otorga `SELECT` sobre el esquema `core`
para `app_riesgo`, más `UPDATE` puntual en `core.usuario`, y en el resto de
esquemas únicamente `SELECT, INSERT` — nunca `UPDATE`. Se comprobaron tres
huecos en vivo:
- Falta `INSERT` en `core.usuario` (alta de usuarios, sección 11) y en
  `core.limite_cupo` (`POST /cupos/limites`, sección 11).
- Falta `UPDATE` en `audit.destinatario`: sin él, `POST
  /publicaciones/{id}/acuse` falla con `permission denied for table
  destinatario` — no es RLS (eso daría cero filas afectadas, no un error),
  es la ausencia total del privilegio a nivel de tabla.

Se agregan esos `GRANT` en el script de preparación del rol de aplicación
(sección 15 / `operacion/preparar_rol.sql`).

## 9. Base de datos de prueba local

La especificación reserva la ejecución contra Postgres real para la máquina
enterprise (Tarea 2/3, sección 18 y 21). En esta máquina las migraciones se
prueban contra una instancia de Postgres 16 local (no contenedorizada, por
falta de daemon Docker en este entorno), usada exclusivamente para verificar
que las migraciones corren sin error y que las políticas RLS se comportan
como se espera. No contiene datos reales de CAXDAC en ningún momento.

## 10. Recursión infinita entre las políticas de publicación y destinatario

`audit.publicacion` y `audit.destinatario` tienen RLS habilitado (migración
007) y cada política de `SELECT` consulta la tabla contraria dentro de su
propio `USING` (`ver_publicacion` mira `audit.destinatario`, `ver_destinatario`
mira `audit.publicacion`). Postgres detecta esto como recursión infinita al
evaluar cualquiera de las dos — se comprobó en vivo: `POST /publicaciones`
fallaba con `infinite recursion detected in policy for relation
"publicacion"` al hacer el `RETURNING id` del `INSERT`, que dispara la
política de `SELECT` sobre la fila insertada. Se agrega la migración 011,
que envuelve cada referencia cruzada en una función `SECURITY DEFINER`
(`core.es_destinatario_de`, `core.es_publicador_de`) — el mismo patrón que
ya usa `core.puede_ver_resultado` (decisión 6) para el mismo problema
estructural: la consulta interna de una función `SECURITY DEFINER` corre
con los privilegios de quien la creó (dueño de las tablas), así que no
vuelve a pasar por RLS y el ciclo se rompe sin abrir ningún acceso nuevo.

## 11. `separador` del esquema no debe anular la autodetección

El ejemplo de `EsquemaInsumo` en la sección 9 fija `separador="|"` para
posiciones/precios/flujos_pasivo. Tomado literalmente, eso hace que el
lector ignore el contenido real del archivo y siempre intente partir por
`|` — exactamente lo que la misma sección 9 dice que no debe pasar dos
párrafos después: *"Un .txt puede venir separado por pipe, tabulación,
punto y coma o ancho fijo: detectar el separador leyendo las primeras
líneas."* Se comprobó con una prueba real: un archivo de posiciones
separado por `;` se rechazaba igual, porque el lector insistía en partir
por `|`. La autodetección (`_detectar_separador`) ahora corre siempre para
TXT, sin importar lo que declare el esquema; el campo `separador` queda
como documentación de cuál es el formato habitual de ese insumo, no como
un valor que se use para parsear.

## 12. Tablas de resultados: paginación del lado del cliente, no del servidor

La sección 12 pide tablas "paginada[s] del lado del servidor". Esta primera
versión del frontend implementa orden, filtro y búsqueda en el cliente
sobre el arreglo que ya devuelve `GET /resultados/*` (que trae hasta 5000
filas por corrida). Es razonable para los volúmenes actuales — un
portafolio real cabe holgadamente en eso — pero no es paginación de
servidor. Antes de un volumen de posiciones mucho mayor, hay que agregar
`offset`/`limit` a los endpoints de resultados y mover el filtrado ahí.
Documentado en vez de implementado en silencio para que quede claro qué
falta cuando el volumen real lo exija.

## 13. Falta un endpoint no-admin para elegir destinatarios al publicar

La sección 13 dice que al publicar el usuario "selecciona destinatarios,
con listas predefinidas por módulo". La única fuente de la lista de
usuarios en la tabla de endpoints (sección 11) es `GET /admin/usuarios`,
restringida a `admin`. Pero según la matriz de permisos (sección 7), quien
publica es el rol `revisor`, no necesariamente `admin` — un revisor no
podría ver a quién puede enviarle la publicación. Se agrega
`GET /usuarios`, un directorio mínimo (id, nombre, correo, rol) sin datos
sensibles, accesible a cualquier usuario autenticado, separado de
`/admin/usuarios` que sigue siendo solo-admin y trae más detalle
(actividad, si debe cambiar clave, etc.).

## 14. Falta un endpoint para elegir la entidad al crear un límite de cupo

`POST /cupos/limites` (sección 11) recibe `entidad_id`, pero la única
lectura de emisores/contrapartes en la tabla de endpoints es
`GET /cupos/limites`, que solo trae entidades que **ya tienen** un límite
— inútil para elegir una entidad que todavía no tiene ninguno, que es
justamente el caso de uso principal del formulario de creación. Se agrega
`GET /cupos/entidades?tipo=emisor|contraparte`, solo-admin, que lista
todos los emisores o contrapartes activos desde `core.emisor`/
`core.contraparte`.

## 15. Vulnerabilidad `postcss` (alta) que solo se corrige subiendo a Next 16

`npm audit` reporta una vulnerabilidad alta en `postcss`, arrastrada por la
copia interna que usa `next` en su propia tubería de build (no la versión
de `postcss`/`@tailwindcss/postcss` que este proyecto declara). El único
arreglo automático (`npm audit fix --force`) sube a `next@16`, lo que
rompe la sección 4 ("Next.js 15, App Router"). Se deja sin corregir por
ahora: es una dependencia de herramienta de build (procesa el CSS propio
del proyecto en `next build`/`next dev`, no CSS de terceros ni tráfico de
red), en un servidor de red interna. Revisar cuando exista un parche de
`postcss` compatible con Next 15, o al planear la migración a Next 16.

## 16. Lectura de `.xlsx` en streaming (`openpyxl read_only`) en vez de `pd.read_excel`

Mejora aplicada a partir de una guía externa de arquitectura que el
usuario compartió (Next.js + Postgres + Python), en la sección "Excel
grandes: leer solo lo necesario". `app/ingesta/lector.py` usaba
`pd.read_excel(..., dtype=str)`, que materializa todo el libro en memoria
de una sola vez y fuerza cada celda a texto — con archivos de decenas de
miles de filas eso es el pico de memoria más alto posible, y de paso hace
pasar números y fechas que Excel ya trae tipados por el parser de texto
colombiano sin necesidad.

Se cambia a `openpyxl.load_workbook(..., read_only=True)` con
`iter_rows()`, que itera fila por fila en vez de construir el árbol
completo del libro, y conserva el tipo nativo de cada celda (un
`datetime` de Excel llega como `datetime`, no como texto a reparsear).
`_parsear_fecha` se ajustó para aceptar `datetime`/`date` nativos
directamente. El formato legado `.xls` (binario, no soportado por
openpyxl) sigue usando `pd.read_excel` sin streaming — es un formato en
extinción y no vale la pena una segunda implementación para él. Probado
con un archivo sintético de 50.000 filas (`api/pruebas/test_ingesta.py`).
