-- Políticas de escritura para las tablas con RLS habilitado (006/007/008).
-- Postgres, con RLS habilitado y sin política para un comando, deniega ese
-- comando por defecto — incluso con el GRANT de la sección 15 ya dado. Las
-- migraciones anteriores solo cubrían SELECT (son las que la especificación
-- muestra); sin esto, el motor de ejecución no podría insertar ni una fila
-- de resultado. Ver DECISIONES.md, decisión 8.
--
-- La autorización de fondo para cargar/ejecutar/publicar ya se comprueba en
-- la API antes de intentar la escritura (app/seguridad.py::requiere_permiso).
-- Estas políticas son la traducción mínima de esa misma regla a nivel de
-- fila, para que ninguna escritura dependa solo del código de la aplicación.

CREATE POLICY cargar_carga ON staging.carga FOR INSERT
  WITH CHECK (core.puede(
    CASE tipo_insumo
      WHEN 'posiciones' THEN 'valoracion'
      WHEN 'precios' THEN 'valoracion'
      WHEN 'flujos_pasivo' THEN 'pasivo'
      ELSE tipo_insumo
    END, 'cargar'));

CREATE POLICY actualizar_carga ON staging.carga FOR UPDATE
  USING (core.puede(
    CASE tipo_insumo
      WHEN 'posiciones' THEN 'valoracion'
      WHEN 'precios' THEN 'valoracion'
      WHEN 'flujos_pasivo' THEN 'pasivo'
      ELSE tipo_insumo
    END, 'cargar'));

CREATE POLICY ejecutar_corrida ON proc.corrida FOR INSERT
  WITH CHECK (core.puede(proceso, 'ejecutar'));

-- El propio motor marca EJECUTANDO/OK/ERROR, y el endpoint de anular marca
-- ANULADA; ambos casos ya pasaron el chequeo de permiso en la API.
CREATE POLICY actualizar_corrida ON proc.corrida FOR UPDATE
  USING (true) WITH CHECK (true);

CREATE POLICY escribir_valoracion ON res.valoracion FOR INSERT WITH CHECK (true);
CREATE POLICY escribir_pasivo ON res.pasivo FOR INSERT WITH CHECK (true);
CREATE POLICY escribir_fr ON res.funding_ratio FOR INSERT WITH CHECK (true);
CREATE POLICY escribir_cupos ON res.consumo_cupo FOR INSERT WITH CHECK (true);

CREATE POLICY crear_publicacion ON audit.publicacion FOR INSERT
  WITH CHECK (publicada_por = core.usuario_actual());

CREATE POLICY agregar_destinatario ON audit.destinatario FOR INSERT
  WITH CHECK (EXISTS (
    SELECT 1 FROM audit.publicacion p
    WHERE p.id = audit.destinatario.publicacion_id
      AND p.publicada_por = core.usuario_actual()
  ));

-- El acuse de lectura: cada quien solo puede marcar su propia fila
-- (sección 13: "Un solo registro por usuario: la primera vez que la abre").
CREATE POLICY marcar_acuse ON audit.destinatario FOR UPDATE
  USING (usuario_id = core.usuario_actual())
  WITH CHECK (usuario_id = core.usuario_actual());
