-- Curvas de mercado (TES UVR, etc.). Se cargan como insumo — igual patrón
-- que posiciones/precios/flujos_pasivo: no hay cálculo Python, se guardan
-- tal cual y se consultan directo para graficar. Formato largo (una fila
-- por tipo_curva+fecha+nodo), no ancho por fecha: con ~13.500 nodos por
-- curva, un archivo mensual ya son ~400.000 filas y Postgres los indexa
-- sin esfuerzo — una columna por fecha habría sido un esquema que cambia
-- todos los días, imposible de indexar o filtrar bien.

CREATE TABLE staging.curva_nodo (
  id            bigserial PRIMARY KEY,
  carga_id      bigint NOT NULL REFERENCES staging.carga(id) ON DELETE CASCADE,
  fecha_datos   date NOT NULL,
  tipo_curva    text NOT NULL,
  nodo          integer NOT NULL,      -- plazo en días
  valor         numeric(14,6) NOT NULL,
  campos_extra  jsonb
);
CREATE INDEX ix_curva_nodo_carga ON staging.curva_nodo (carga_id);
-- El índice que importa: graficar una curva en una o varias fechas es
-- "dame los nodos de este tipo_curva en estas fechas, ordenados por nodo".
CREATE INDEX ix_curva_nodo_consulta ON staging.curva_nodo (tipo_curva, fecha_datos, nodo);

-- Anulación genérica de una carga (pedido explícito para curvas, pero es
-- el mismo patrón que proc.corrida ya usa para anular una corrida — se
-- deja disponible para cualquier tipo_insumo, no solo curvas).
ALTER TABLE staging.carga ADD COLUMN anulada_por bigint REFERENCES core.usuario(id);
ALTER TABLE staging.carga ADD COLUMN anulada_en timestamptz;
ALTER TABLE staging.carga ADD COLUMN motivo_anulacion text;

-- RLS: mismo criterio que el resto de staging.* — ver_carga/cargar_carga
-- (migraciones 006/010) ya cubren 'curvas' automáticamente porque su CASE
-- cae al ELSE tipo_insumo, y tipo_insumo='curvas' coincide con el módulo
-- nuevo de abajo. Solo hace falta la política de la tabla nueva.
ALTER TABLE staging.curva_nodo ENABLE ROW LEVEL SECURITY;

-- El argumento de core.puede() aquí es literal ('curvas', 'ver'), no
-- depende de ninguna columna de la fila — a diferencia de staging.carga o
-- proc.corrida, donde el módulo varía por fila (tipo_insumo/proceso) y por
-- lo tanto core.puede() debe re-evaluarse fila por fila de todas formas.
-- Postgres NO deduce solo por ser STABLE que puede evaluar la función una
-- sola vez: sin el (SELECT ...) de abajo, la aplica como Filter dentro del
-- Index Scan, una vez por cada fila leída. Con ~420.000 filas por mes esto
-- se midió en 12,6s por consulta (EXPLAIN ANALYZE); envuelta en SELECT,
-- Postgres la trata como InitPlan (se evalúa una sola vez) y baja a
-- milisegundos. Ver DECISIONES.md, decisión 18.
CREATE POLICY ver_curva_nodo ON staging.curva_nodo FOR SELECT
  USING ((SELECT core.puede('curvas', 'ver')));

CREATE POLICY cargar_curva_nodo ON staging.curva_nodo FOR INSERT
  WITH CHECK ((SELECT core.puede('curvas', 'cargar')));

-- Módulo nuevo en la matriz de permisos (sección 7): mismo criterio que
-- los demás insumos — quien puede cargar valoración/pasivo puede cargar
-- curvas; consulta y revisor solo ven.
INSERT INTO core.permiso (rol, modulo, puede_ver, puede_cargar, puede_ejecutar, puede_publicar) VALUES
  ('admin',    'curvas', true, true,  false, false),
  ('analista', 'curvas', true, true,  false, false),
  ('revisor',  'curvas', true, false, false, false),
  ('consulta', 'curvas', true, false, false, false);
