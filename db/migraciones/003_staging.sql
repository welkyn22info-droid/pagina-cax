-- Staging: los insumos del día tal como llegaron, con su fecha de datos y su origen.

CREATE TYPE staging.estado_carga AS ENUM ('RECIBIDO','VALIDADO','RECHAZADO');

CREATE TABLE staging.carga (
  id              bigserial PRIMARY KEY,
  tipo_insumo     text NOT NULL,        -- 'posiciones','precios','flujos_pasivo', ...
  fecha_datos     date NOT NULL,        -- la fecha DE LOS DATOS, no la de carga
  nombre_archivo  text NOT NULL,
  hash_sha256     text NOT NULL,
  filas_leidas    integer,
  filas_validas   integer,
  estado          staging.estado_carga NOT NULL DEFAULT 'RECIBIDO',
  detalle_error   jsonb,
  ruta_archivo    text,                 -- copia en disco del archivo original (sección 16)
  cargado_por     bigint NOT NULL REFERENCES core.usuario(id),
  cargado_en      timestamptz NOT NULL DEFAULT now()
);

-- Un mismo archivo no se carga dos veces para la misma fecha
CREATE UNIQUE INDEX ux_carga_hash_fecha
  ON staging.carga (tipo_insumo, fecha_datos, hash_sha256);

CREATE INDEX ix_carga_tipo_fecha_estado ON staging.carga (tipo_insumo, fecha_datos, estado, cargado_en DESC);

CREATE TABLE staging.posicion (
  id              bigserial PRIMARY KEY,
  carga_id        bigint NOT NULL REFERENCES staging.carga(id) ON DELETE CASCADE,
  fecha_datos     date NOT NULL,
  portafolio      text NOT NULL,
  instrumento_cod text NOT NULL,
  emisor_cod      text,
  contraparte_cod text,
  nominal         numeric(20,4),
  cantidad        numeric(20,6),
  costo_amortizado numeric(20,4),
  moneda          text DEFAULT 'COP',
  campos_extra    jsonb              -- columnas del archivo que aún no se modelan
);
CREATE INDEX ix_posicion_fecha ON staging.posicion (fecha_datos, portafolio);
CREATE INDEX ix_posicion_carga ON staging.posicion (carga_id);

CREATE TABLE staging.precio (
  id              bigserial PRIMARY KEY,
  carga_id        bigint NOT NULL REFERENCES staging.carga(id) ON DELETE CASCADE,
  fecha_datos     date NOT NULL,
  instrumento_cod text NOT NULL,
  precio_limpio   numeric(20,8),
  precio_sucio    numeric(20,8),
  tasa            numeric(12,6),
  fuente          text,
  campos_extra    jsonb
);
CREATE INDEX ix_precio_fecha ON staging.precio (fecha_datos, instrumento_cod);
CREATE INDEX ix_precio_carga ON staging.precio (carga_id);

CREATE TABLE staging.flujo_pasivo (
  id              bigserial PRIMARY KEY,
  carga_id        bigint NOT NULL REFERENCES staging.carga(id) ON DELETE CASCADE,
  fecha_datos     date NOT NULL,
  concepto        text,
  fecha_flujo     date NOT NULL,
  monto           numeric(20,4) NOT NULL,
  moneda          text DEFAULT 'COP',
  campos_extra    jsonb
);
CREATE INDEX ix_flujo_fecha ON staging.flujo_pasivo (fecha_datos, fecha_flujo);
CREATE INDEX ix_flujo_carga ON staging.flujo_pasivo (carga_id);
