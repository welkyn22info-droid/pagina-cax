-- Usuarios sintéticos para desarrollo y pruebas. NO usar en producción.
--
-- Contraseña para todos: Cambiar123456
-- (cumple el mínimo de 12 caracteres de la sección 7; hash con bcrypt,
-- costo 12, generado fuera de la aplicación solo para poblar esta semilla)
-- debe_cambiar_clave = true fuerza el cambio en el primer ingreso.

INSERT INTO core.usuario (correo, nombre, hash_clave, rol, activo, debe_cambiar_clave) VALUES
  ('admin@riesgo.local',    'Administrador de la plataforma', '$2b$12$GbtmK7OIeWxaAH5KJj9pQOIdLqgN7EVxtMyKROKmcDz6xTKAiVXLS', 'admin',    true, true),
  ('analista1@riesgo.local','Analista de riesgo — carga y ejecuta', '$2b$12$GbtmK7OIeWxaAH5KJj9pQOIdLqgN7EVxtMyKROKmcDz6xTKAiVXLS', 'analista', true, true),
  ('analista2@riesgo.local','Analista de riesgo — suplente',        '$2b$12$GbtmK7OIeWxaAH5KJj9pQOIdLqgN7EVxtMyKROKmcDz6xTKAiVXLS', 'analista', true, true),
  ('revisor1@riesgo.local', 'Revisor — aprueba y publica',          '$2b$12$GbtmK7OIeWxaAH5KJj9pQOIdLqgN7EVxtMyKROKmcDz6xTKAiVXLS', 'revisor',  true, true),
  ('director@riesgo.local', 'Dirección de riesgo — solo lectura',   '$2b$12$GbtmK7OIeWxaAH5KJj9pQOIdLqgN7EVxtMyKROKmcDz6xTKAiVXLS', 'consulta', true, true),
  ('comite@riesgo.local',   'Comité de riesgo — solo lectura',      '$2b$12$GbtmK7OIeWxaAH5KJj9pQOIdLqgN7EVxtMyKROKmcDz6xTKAiVXLS', 'consulta', true, true);
