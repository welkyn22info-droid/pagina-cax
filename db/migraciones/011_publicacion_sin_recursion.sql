-- Corrige recursión infinita entre las políticas de audit.publicacion y
-- audit.destinatario (migración 007): cada una consulta la otra tabla
-- dentro de su USING, y ambas tienen RLS habilitado, así que Postgres
-- entra en un ciclo al evaluar cualquiera de las dos. Ver DECISIONES.md,
-- decisión 10.
--
-- La solución es la misma que ya usa core.puede_ver_resultado (migración
-- 009): envolver la referencia cruzada en una función SECURITY DEFINER.
-- Como el dueño de la función es quien corrió las migraciones (dueño de
-- las tablas), la consulta interna de la función no vuelve a pasar por
-- RLS — se rompe el ciclo sin abrir ningún acceso nuevo.

CREATE FUNCTION core.es_destinatario_de(p_publicacion_id bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT EXISTS (
    SELECT 1 FROM audit.destinatario d
    WHERE d.publicacion_id = p_publicacion_id AND d.usuario_id = core.usuario_actual()
  )
$$;

CREATE FUNCTION core.es_publicador_de(p_publicacion_id bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT EXISTS (
    SELECT 1 FROM audit.publicacion p
    WHERE p.id = p_publicacion_id AND p.publicada_por = core.usuario_actual()
  )
$$;

DROP POLICY ver_publicacion ON audit.publicacion;
CREATE POLICY ver_publicacion ON audit.publicacion FOR SELECT
  USING (publicada_por = core.usuario_actual() OR core.es_destinatario_de(id));

DROP POLICY ver_destinatario ON audit.destinatario;
CREATE POLICY ver_destinatario ON audit.destinatario FOR SELECT
  USING (usuario_id = core.usuario_actual() OR core.es_publicador_de(publicacion_id));

DROP POLICY agregar_destinatario ON audit.destinatario;
CREATE POLICY agregar_destinatario ON audit.destinatario FOR INSERT
  WITH CHECK (core.es_publicador_de(publicacion_id));
