-- Maestros estables: emisores, contrapartes, instrumentos, límites de cupo.

CREATE TABLE core.emisor (
  id              bigserial PRIMARY KEY,
  codigo          text NOT NULL UNIQUE,      -- código con el que llega en los archivos
  nombre          text NOT NULL,
  nit             text,
  sector          text,
  calificacion    text,
  pais            text DEFAULT 'CO',
  activo          boolean NOT NULL DEFAULT true,
  creado_en       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.contraparte (
  id              bigserial PRIMARY KEY,
  codigo          text NOT NULL UNIQUE,
  nombre          text NOT NULL,
  nit             text,
  tipo            text,                      -- banco, comisionista, fiduciaria
  calificacion    text,
  activo          boolean NOT NULL DEFAULT true,
  creado_en       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.instrumento (
  id              bigserial PRIMARY KEY,
  codigo          text NOT NULL UNIQUE,      -- nemotécnico o ISIN
  isin            text,
  emisor_id       bigint REFERENCES core.emisor(id),
  tipo            text NOT NULL,             -- TES, CDT, bono, acción, derivado
  moneda          text NOT NULL DEFAULT 'COP',
  fecha_emision   date,
  fecha_vencimiento date,
  tasa_facial     numeric(12,6),
  periodicidad    text,
  activo          boolean NOT NULL DEFAULT true
);

-- Límites de cupo. Parametrizables desde la interfaz, con vigencia.
CREATE TABLE core.limite_cupo (
  id              bigserial PRIMARY KEY,
  tipo            text NOT NULL,             -- 'emisor' | 'contraparte'
  entidad_id      bigint NOT NULL,           -- apunta a emisor.id o contraparte.id
  base            text NOT NULL,             -- 'monto' | 'porcentaje_portafolio'
  valor_limite    numeric(20,4) NOT NULL,
  umbral_alerta   numeric(5,4) NOT NULL DEFAULT 0.80,   -- 80% enciende ámbar
  vigente_desde   date NOT NULL,
  vigente_hasta   date,
  creado_por      bigint REFERENCES core.usuario(id),
  creado_en       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_limite_tipo CHECK (tipo IN ('emisor','contraparte')),
  CONSTRAINT ck_limite_base CHECK (base IN ('monto','porcentaje_portafolio'))
);

CREATE INDEX ix_limite_vigencia ON core.limite_cupo (tipo, entidad_id, vigente_desde DESC);
