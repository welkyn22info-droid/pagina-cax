-- Publicación y acuse de lectura. Reemplaza el correo como canal de
-- entrega: el dato vive en la plataforma y el acuse solo se registra al
-- abrirlo ahí (sección 13).

CREATE TABLE audit.publicacion (
  id              bigserial PRIMARY KEY,
  corrida_id      bigint NOT NULL REFERENCES proc.corrida(id),
  titulo          text NOT NULL,
  comentario      text,
  publicada_por   bigint NOT NULL REFERENCES core.usuario(id),
  publicada_en    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_publicacion_corrida ON audit.publicacion (corrida_id);

CREATE TABLE audit.destinatario (
  publicacion_id  bigint NOT NULL REFERENCES audit.publicacion(id) ON DELETE CASCADE,
  usuario_id      bigint NOT NULL REFERENCES core.usuario(id),
  visto_en        timestamptz,
  PRIMARY KEY (publicacion_id, usuario_id)
);
CREATE INDEX ix_destinatario_usuario_pendiente ON audit.destinatario (usuario_id) WHERE visto_en IS NULL;

CREATE TABLE audit.evento (
  id              bigserial PRIMARY KEY,
  usuario_id      bigint REFERENCES core.usuario(id),
  accion          text NOT NULL,     -- 'ingreso','cierre_sesion','carga','ejecucion',
                                     -- 'publicacion','acuse','exportacion','cambio_limite'
  recurso         text,
  recurso_id      bigint,
  detalle         jsonb,
  ip              inet,
  ocurrido_en     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_evento_fecha ON audit.evento (ocurrido_en DESC);
CREATE INDEX ix_evento_usuario ON audit.evento (usuario_id, ocurrido_en DESC);

ALTER TABLE audit.publicacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY ver_publicacion ON audit.publicacion FOR SELECT
  USING (
    publicada_por = core.usuario_actual()
    OR EXISTS (
      SELECT 1 FROM audit.destinatario d
      WHERE d.publicacion_id = audit.publicacion.id
        AND d.usuario_id = core.usuario_actual()
    )
  );

ALTER TABLE audit.destinatario ENABLE ROW LEVEL SECURITY;
CREATE POLICY ver_destinatario ON audit.destinatario FOR SELECT
  USING (
    usuario_id = core.usuario_actual()
    OR EXISTS (
      SELECT 1 FROM audit.publicacion p
      WHERE p.id = audit.destinatario.publicacion_id
        AND p.publicada_por = core.usuario_actual()
    )
  );
