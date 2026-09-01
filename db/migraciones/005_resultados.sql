-- Resultados calculados, siempre amarrados a una corrida. Ninguna fila se
-- actualiza ni se borra desde la aplicación (ver nota de inmutabilidad).

CREATE TABLE res.valoracion (
  id                bigserial PRIMARY KEY,
  corrida_id        bigint NOT NULL REFERENCES proc.corrida(id),
  fecha_datos       date NOT NULL,
  portafolio        text NOT NULL,
  instrumento_cod   text NOT NULL,
  emisor_cod        text,
  nominal           numeric(20,4),
  precio_usado      numeric(20,8),
  valor_mercado     numeric(20,4) NOT NULL,
  valor_causado     numeric(20,4),
  duracion          numeric(12,6),
  moneda            text DEFAULT 'COP',
  metricas_extra    jsonb
);
CREATE INDEX ix_val_corrida ON res.valoracion (corrida_id);
CREATE INDEX ix_val_fecha ON res.valoracion (fecha_datos, portafolio);

CREATE TABLE res.pasivo (
  id                bigserial PRIMARY KEY,
  corrida_id        bigint NOT NULL REFERENCES proc.corrida(id),
  fecha_datos       date NOT NULL,
  concepto          text,
  valor_presente    numeric(20,4) NOT NULL,
  duracion          numeric(12,6),
  tasa_descuento    numeric(12,6),
  metricas_extra    jsonb
);
CREATE INDEX ix_pas_fecha ON res.pasivo (fecha_datos);
CREATE INDEX ix_pas_corrida ON res.pasivo (corrida_id);

CREATE TABLE res.funding_ratio (
  id                bigserial PRIMARY KEY,
  corrida_id        bigint NOT NULL REFERENCES proc.corrida(id),
  fecha_datos       date NOT NULL,
  valor_activos     numeric(20,4) NOT NULL,
  valor_pasivos     numeric(20,4) NOT NULL,
  ratio             numeric(12,6) NOT NULL,
  superavit_deficit numeric(20,4) NOT NULL,
  corrida_activos   bigint REFERENCES proc.corrida(id),
  corrida_pasivos   bigint REFERENCES proc.corrida(id),
  metricas_extra    jsonb
);
CREATE UNIQUE INDEX ux_fr_corrida ON res.funding_ratio (corrida_id);
CREATE INDEX ix_fr_fecha ON res.funding_ratio (fecha_datos);
