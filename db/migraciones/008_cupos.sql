-- Resultado del módulo de cupos: consumo por emisor/contraparte con semáforo.

CREATE TABLE res.consumo_cupo (
  id                bigserial PRIMARY KEY,
  corrida_id        bigint NOT NULL REFERENCES proc.corrida(id),
  fecha_datos       date NOT NULL,
  tipo              text NOT NULL,            -- 'emisor' | 'contraparte'
  entidad_id        bigint NOT NULL,
  entidad_nombre    text NOT NULL,            -- desnormalizado para la vista
  limite_id         bigint REFERENCES core.limite_cupo(id),
  valor_limite      numeric(20,4),            -- null si no hay límite parametrizado
  valor_expuesto    numeric(20,4) NOT NULL,
  utilizacion       numeric(8,6),             -- expuesto / limite; null sin límite
  estado            text NOT NULL,            -- 'OK' | 'ALERTA' | 'EXCEDIDO' | 'SIN_LIMITE'
  detalle           jsonb,
  CONSTRAINT ck_cupo_tipo CHECK (tipo IN ('emisor','contraparte')),
  CONSTRAINT ck_cupo_estado CHECK (estado IN ('OK','ALERTA','EXCEDIDO','SIN_LIMITE'))
);
CREATE INDEX ix_cupo_fecha ON res.consumo_cupo (fecha_datos, estado);
CREATE INDEX ix_cupo_corrida ON res.consumo_cupo (corrida_id);

ALTER TABLE res.consumo_cupo ENABLE ROW LEVEL SECURITY;
CREATE POLICY ver_cupos ON res.consumo_cupo FOR SELECT
  USING (core.puede('cupos','ver'));
