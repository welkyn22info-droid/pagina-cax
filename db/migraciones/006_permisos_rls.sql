-- Seguridad a nivel de fila. El control vive en Postgres, no en la interfaz.
-- La API fija la identidad del usuario en una variable de sesión de la
-- transacción (SET LOCAL app.usuario_id = '<id>') y las políticas deciden
-- qué filas son visibles.

CREATE FUNCTION core.usuario_actual() RETURNS bigint
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.usuario_id', true), '')::bigint
$$;

CREATE FUNCTION core.puede(p_modulo text, p_accion text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT COALESCE((
    SELECT CASE p_accion
             WHEN 'ver'      THEN p.puede_ver
             WHEN 'cargar'   THEN p.puede_cargar
             WHEN 'ejecutar' THEN p.puede_ejecutar
             WHEN 'publicar' THEN p.puede_publicar
           END
    FROM core.permiso p
    JOIN core.usuario u ON u.rol = p.rol
    WHERE u.id = core.usuario_actual()
      AND u.activo
      AND p.modulo = p_modulo
  ), false)
$$;

-- Nota: la regla "consulta solo ve lo publicado" (sección 7) se agrega en
-- la migración 009, una vez existen las tablas de audit.publicacion — no
-- puede resolverse aquí porque esta migración corre antes que la 007.

ALTER TABLE res.valoracion ENABLE ROW LEVEL SECURITY;
CREATE POLICY ver_valoracion ON res.valoracion FOR SELECT
  USING (core.puede('valoracion','ver'));

ALTER TABLE res.pasivo ENABLE ROW LEVEL SECURITY;
CREATE POLICY ver_pasivo ON res.pasivo FOR SELECT
  USING (core.puede('pasivo','ver'));

ALTER TABLE res.funding_ratio ENABLE ROW LEVEL SECURITY;
CREATE POLICY ver_fr ON res.funding_ratio FOR SELECT
  USING (core.puede('funding_ratio','ver'));

ALTER TABLE staging.carga ENABLE ROW LEVEL SECURITY;
CREATE POLICY ver_carga ON staging.carga FOR SELECT
  USING (core.puede(
    CASE tipo_insumo
      WHEN 'posiciones' THEN 'valoracion'
      WHEN 'precios' THEN 'valoracion'
      WHEN 'flujos_pasivo' THEN 'pasivo'
      ELSE tipo_insumo
    END, 'ver'));

ALTER TABLE proc.corrida ENABLE ROW LEVEL SECURITY;
CREATE POLICY ver_corrida ON proc.corrida FOR SELECT
  USING (core.puede(proceso, 'ver'));

-- Matriz de permisos inicial (sección 7).
INSERT INTO core.permiso (rol, modulo, puede_ver, puede_cargar, puede_ejecutar, puede_publicar) VALUES
  ('admin',    'valoracion',    true, true,  true,  true),
  ('admin',    'pasivo',        true, true,  true,  true),
  ('admin',    'funding_ratio', true, true,  true,  true),
  ('admin',    'cupos',         true, true,  true,  true),
  ('analista', 'valoracion',    true, true,  true,  false),
  ('analista', 'pasivo',        true, true,  true,  false),
  ('analista', 'funding_ratio', true, true,  true,  false),
  ('analista', 'cupos',         true, true,  true,  false),
  ('revisor',  'valoracion',    true, false, false, true),
  ('revisor',  'pasivo',        true, false, false, true),
  ('revisor',  'funding_ratio', true, false, false, true),
  ('revisor',  'cupos',         true, false, false, true),
  ('consulta', 'valoracion',    true, false, false, false),
  ('consulta', 'pasivo',        true, false, false, false),
  ('consulta', 'funding_ratio', true, false, false, false),
  ('consulta', 'cupos',         true, false, false, false);
