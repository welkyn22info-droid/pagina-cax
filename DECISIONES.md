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

## 17. Estado `PENDIENTE_CONFIRMACION`: el resultado del legado no cae directo en `res.*`

Pedido explícito del usuario, más allá de las 21 secciones originales: el
código real de CAXDAC puede llegar como notebooks de Jupyter en vez de
funciones `.py` limpias, y aunque se envuelva con la misma firma del
contrato (decisión 1), el resultado de una corrida debe poder auditarse
**antes** de que quede como oficial en `res.*` — no basta con verlo en
pantalla después de que ya se escribió.

**Decisión:** el envoltorio de cada proceso (`app/motor/procesos/*.py`) ya
no llama `escribir_resultado` directo. Llama `guardar_borrador`
(`app/motor/io.py`), que guarda las filas calculadas como JSON en la
tabla nueva `proc.resultado_borrador` (migración 012). El motor deja la
corrida en el estado nuevo `PENDIENTE_CONFIRMACION` (no en `OK`) — un
valor agregado a `proc.estado_corrida` con `ALTER TYPE ... ADD VALUE`.
`GET /corridas/{id}` expone ese borrador para que la interfaz lo muestre
como vista previa. `POST /corridas/{id}/confirmar` es el paso nuevo: llama
`aplicar_borrador`, que recién ahí escribe en `res.*` reutilizando
`escribir_resultado` sin modificarla, y pasa la corrida a `OK`
(`confirmada_por`/`confirmada_en`, columnas nuevas en `proc.corrida`).
`POST /corridas/{id}/anular` ahora también acepta descartar una corrida en
`PENDIENTE_CONFIRMACION` — nunca llegó a `res.*`, así que anularla es solo
marcarla `ANULADA` sin nada que revertir.

El permiso para confirmar reutiliza `puede_publicar` (no se agrega una
columna de permiso nueva): el rol que hoy puede dar por oficial un
resultado ante otros (`revisor`, `admin`) es el mismo que debe poder darlo
por oficial en la base. `Publicar` (sección 13, con acuse de lectura)
sigue siendo un paso aparte y posterior — confirmar hace que el resultado
exista en `res.*`; publicar lo hace visible para el rol `consulta`.

Para procesos que no necesitan legado (los maestros de `core.*` —
emisores, instrumentos, contrapartes, límites de cupo — sección 11), este
estado no aplica: se siguen cargando directo a su tabla vía los
formularios de administración, sin pasar por `proc.corrida` en absoluto.

## 18. Curvas de mercado: formato largo, no una columna por fecha, y anulación genérica de cargas

Pedido explícito del usuario, tampoco previsto en las 21 secciones
originales: cargar curvas de mercado (TES UVR, `CECUVR`) y poder graficarlas
por nodo (plazo en días) comparando varias fechas a la vez.

**Formato de la tabla:** el archivo real de origen viene *ancho* (una
columna por fecha, `Curva;Plazo en días;1/08/2026;2/08/2026;...`), pero con
~13.500 nodos por curva eso son ~13.500 columnas-fecha si se guardara tal
cual — inviable en SQL (esquema que cambia cada día, imposible de indexar
o filtrar). Se guarda en formato *largo*: `staging.curva_nodo(carga_id,
fecha_datos, tipo_curva, nodo, valor)`, una fila por combinación. Un mes
son ~13.500 × ~21 días hábiles ≈ 280.000 filas — trivial para Postgres con
el índice `(tipo_curva, fecha_datos, nodo)`; un año de historia son unos
pocos millones de filas, siguen siendo triviales. El panel de carga diaria
(hacia adelante) recibe el archivo ya en este formato largo (3 columnas:
curva, nodo, valor, para una `fecha_datos` elegida en el formulario) — el
archivo ancho de backfill histórico se pivotea aparte
(`operacion/cargar_curvas_historico.py`) y se carga día por día contra el
mismo endpoint `POST /cargas`, así cada día queda con su propia trazabilidad
(carga_id, hash, usuario) igual que cualquier otro insumo.

Es un insumo más (mismo patrón que `posiciones`/`precios`/`flujos_pasivo`):
vive en `staging`, no en `res.*`, porque no hay cálculo que lo transforme —
se sube y se consulta directo para graficar (`GET /curvas`).

**Anulación genérica de `staging.carga`:** el usuario pidió explícitamente
poder anular una carga de curvas (con quién la anula y por qué). En vez de
un mecanismo aparte solo para curvas, se agregan `anulada_por/anulada_en/
motivo_anulacion` a `staging.carga` en general — mismo patrón que ya usa
`proc.corrida` para anular una corrida (decisión previa, sección 17) — y un
endpoint `POST /cargas/{id}/anular`, reutilizable para cualquier tipo de
insumo. `leer_insumo` (`app/motor/io.py`) se ajusta para excluir cargas
anuladas al resolver "la última carga vigente de esta fecha", igual que ya
excluye las no `VALIDADO`.

**Permisos:** módulo nuevo `curvas` en `core.permiso`, con la misma
distribución que los demás insumos (`analista`/`admin` cargan, todos ven).

## 19. `core.puede(...)` sin envolver en una política RLS de una tabla grande es 12,6s; envuelto en `(SELECT ...)`, 150ms

Se midió probando `staging.curva_nodo` en vivo (418.655 filas, la carga real
de un mes): `GET /curvas/tipos` tardaba tanto que la petición nunca volvía
—se comprobó con `EXPLAIN ANALYZE` conectado como `app_riesgo` con
`app.usuario_id` fijado, replicando exactamente la sesión de la API—.
El plan mostraba `core.puede('curvas','ver')` aplicado como `Filter` dentro
del `Index Scan`, **evaluado una vez por cada fila leída** (418.655 veces),
aunque sus dos argumentos son literales y no dependen de ninguna columna de
`curva_nodo`. Postgres no deduce eso solo porque la función sea `STABLE`:
sin ayuda, no la trata como una constante precomputable.

**Arreglo:** envolver la llamada en un `SELECT` escalar —
`USING ((SELECT core.puede('curvas','ver')))` en vez de
`USING (core.puede('curvas','ver'))`. Eso hace que Postgres la evalúe como
un `InitPlan` (una sola vez, `loops=1`) en vez de un filtro por fila. Mismo
`EXPLAIN ANALYZE`, mismos datos: de 12.609ms a 150ms — 84 veces más rápido.

Se aplica solo a `ver_curva_nodo`/`cargar_curva_nodo` (migración 013), que
son el único caso del sistema con argumentos 100% literales — las demás
políticas existentes (`ver_carga`, `ver_corrida`, etc.) usan un `CASE` sobre
una columna de la fila (`tipo_insumo`, `proceso`), así que de todas formas
deben re-evaluarse por fila; no tienen este problema, y hoy sus tablas son
chicas (decenas de filas) así que el costo es insignificante. Si una de esas
tablas crece a un volumen comparable, aplicar el mismo patrón `(SELECT ...)`
donde el argumento de `core.puede()` deje de depender de la fila.

## 20. Índice único de `staging.carga` no distinguía carga anulada: bloqueaba recargar el mismo archivo

Se descubrió probando el flujo real de anular + volver a cargar (decisión
18): `ux_carga_hash_fecha` (migración 003) es
`UNIQUE (tipo_insumo, fecha_datos, hash_sha256)` sin condición — una carga
anulada sigue ocupando esa combinación, así que el mismo archivo no se
puede volver a subir para esa fecha aunque la carga original ya no cuente
para nada (`leer_insumo` y las consultas de curvas ya la ignoran vía
`anulada_en IS NULL`). Se comprobó en vivo: recargar el archivo de curvas
del 31/08 tras anularlo fallaba con `UniqueViolation`.

Se agrega la migración 014, que reemplaza el índice por uno **parcial**
(`WHERE anulada_en IS NULL`): la restricción de "no repetir el mismo
archivo para esa fecha" sigue vigente entre cargas no anuladas, pero una
anulada libera el hash. De paso, `crear_carga` (`app/rutas/cargas.py`)
ajusta su chequeo previo de duplicado para ignorar cargas anuladas
también — antes solo miraba `tipo_insumo + fecha_datos + hash`.

## 21. `staging.curva_nodo`: se quita `campos_extra`, se agrega una vista de auditoría en vez de columnas repetidas

Pedido del usuario tras revisar la tabla en pgAdmin: quitar `campos_extra`
(no se usa — las 3 columnas de curvas ya están mapeadas explícitamente) y
poder ver junto a cada fila quién la cargó, cuándo, si esa carga está
anulada y quién la anuló.

**`campos_extra` fuera de la tabla, no solo sin usar:** `leer_archivo`
(`app/ingesta/lector.py`) agrega esa columna al DataFrame *siempre*, sin
mirar si la tabla destino la tiene — así que quitarla de la tabla sin
ajustar nada más rompía la carga (`INSERT` a una columna inexistente). Se
corrige `_insertar_filas` (`app/rutas/cargas.py`) para reflejar las
columnas reales de la tabla destino (mismo patrón que ya usa
`escribir_resultado` en `app/motor/io.py`) y descartar del `INSERT`
cualquier columna del DataFrame que la tabla no tenga — no solo
`campos_extra`, cualquier caso futuro igual.

**Vista, no columnas denormalizadas:** el usuario pidió columnas de
"fecha de cargue", "usuario que carga", "anulado" y "usuario que anula"
directamente en la tabla. Guardarlas ahí significaría repetir el mismo
dato ~13.500 veces por carga (una vez por nodo) y que pudieran
desincronizarse del original en `staging.carga`. Se crea la vista
`staging.curva_nodo_auditoria` (`JOIN` a `staging.carga` y `core.usuario`)
que expone exactamente esas columnas — `anulado` como texto `'Sí'/'No'`,
tal como se pidió — sin duplicar el dato ni arriesgar que quede
desactualizado. La anulación sigue siendo por carga completa (un día), no
por nodo individual — es del archivo entero que se equivocó, no de un
nodo suelto.
