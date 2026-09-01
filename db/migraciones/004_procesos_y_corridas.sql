-- Corridas: la trazabilidad. Toda ejecución queda amarrada a los insumos
-- exactos que consumió, sin excepción.

CREATE TYPE proc.estado_corrida AS ENUM ('PENDIENTE','EJECUTANDO','OK','ERROR','ANULADA');

CREATE TABLE proc.corrida (
  id              bigserial PRIMARY KEY,
  proceso         text NOT NULL,          -- 'valoracion','pasivo','funding_ratio','cupos'
  fecha_datos     date NOT NULL,
  estado          proc.estado_corrida NOT NULL DEFAULT 'PENDIENTE',
  parametros      jsonb NOT NULL DEFAULT '{}',
  version_codigo  text,                   -- hash git del código al momento de correr
  disparada_por   bigint NOT NULL REFERENCES core.usuario(id),
  iniciada_en     timestamptz NOT NULL DEFAULT now(),
  finalizada_en   timestamptz,
  duracion_ms     integer,
  filas_resultado integer,
  mensaje_error   text,
  traza_error     text,
  log_ejecucion   text,                   -- captura de stdout del código legado
  anulada_por     bigint REFERENCES core.usuario(id),
  anulada_en      timestamptz,
  motivo_anulacion text
);
CREATE INDEX ix_corrida_proceso_fecha ON proc.corrida (proceso, fecha_datos, iniciada_en DESC);
CREATE INDEX ix_corrida_estado ON proc.corrida (estado);

-- Qué cargas exactas consumió esta corrida. Sin esto no hay reconstrucción posible.
-- Nota: Postgres no admite expresiones en PRIMARY KEY, así que la unicidad
-- se hace con un índice por expresión sobre un id propio (ver DECISIONES.md).
CREATE TABLE proc.corrida_insumo (
  id              bigserial PRIMARY KEY,
  corrida_id      bigint NOT NULL REFERENCES proc.corrida(id) ON DELETE CASCADE,
  carga_id        bigint REFERENCES staging.carga(id),
  corrida_origen  bigint REFERENCES proc.corrida(id),   -- si el insumo es otro resultado
  CONSTRAINT ck_corrida_insumo_uno CHECK (
    (carga_id IS NOT NULL)::int + (corrida_origen IS NOT NULL)::int = 1
  )
);
CREATE UNIQUE INDEX ux_corrida_insumo
  ON proc.corrida_insumo (corrida_id, COALESCE(carga_id,0), COALESCE(corrida_origen,0));
CREATE INDEX ix_corrida_insumo_carga ON proc.corrida_insumo (carga_id);
CREATE INDEX ix_corrida_insumo_origen ON proc.corrida_insumo (corrida_origen);

-- Insumos declarados por proceso. El motor valida contra esta tabla antes de arrancar.
CREATE TABLE proc.requisito (
  proceso         text NOT NULL,
  tipo_insumo     text,                   -- carga requerida
  proceso_previo  text,                   -- o resultado de otro proceso
  obligatorio     boolean NOT NULL DEFAULT true
);

INSERT INTO proc.requisito (proceso, tipo_insumo, proceso_previo) VALUES
  ('valoracion',    'posiciones',    NULL),
  ('valoracion',    'precios',       NULL),
  ('pasivo',        'flujos_pasivo', NULL),
  ('funding_ratio', NULL,            'valoracion'),
  ('funding_ratio', NULL,            'pasivo'),
  ('cupos',         'posiciones',    NULL),
  ('cupos',         NULL,            'valoracion');
