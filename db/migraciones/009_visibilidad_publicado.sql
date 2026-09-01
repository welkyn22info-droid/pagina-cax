-- Afina la política de lectura de resultados: el rol 'consulta' según la
-- matriz de la sección 7 solo ve "publicado", no cualquier resultado con
-- permiso 'ver'. Los demás roles (admin, analista, revisor) conservan
-- acceso a todo lo que su 'puede_ver' permite, publicado o no, porque
-- necesitan revisar antes de publicar.
--
-- Se separa de la migración 006 porque depende de audit.publicacion y
-- audit.destinatario, creadas en la 007 (sección 20: "un cambio es una
-- migración nueva", nunca se edita una migración ya escrita).

CREATE FUNCTION core.puede_ver_resultado(p_modulo text, p_corrida_id bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT core.puede(p_modulo, 'ver')
     AND (
       (SELECT rol FROM core.usuario WHERE id = core.usuario_actual()) IS DISTINCT FROM 'consulta'
       OR EXISTS (
         SELECT 1
         FROM audit.publicacion pub
         JOIN audit.destinatario d ON d.publicacion_id = pub.id
         WHERE pub.corrida_id = p_corrida_id
           AND d.usuario_id = core.usuario_actual()
       )
     )
$$;

DROP POLICY ver_valoracion ON res.valoracion;
CREATE POLICY ver_valoracion ON res.valoracion FOR SELECT
  USING (core.puede_ver_resultado('valoracion', corrida_id));

DROP POLICY ver_pasivo ON res.pasivo;
CREATE POLICY ver_pasivo ON res.pasivo FOR SELECT
  USING (core.puede_ver_resultado('pasivo', corrida_id));

DROP POLICY ver_fr ON res.funding_ratio;
CREATE POLICY ver_fr ON res.funding_ratio FOR SELECT
  USING (core.puede_ver_resultado('funding_ratio', corrida_id));

DROP POLICY ver_cupos ON res.consumo_cupo;
CREATE POLICY ver_cupos ON res.consumo_cupo FOR SELECT
  USING (core.puede_ver_resultado('cupos', corrida_id));
