-- Preparación del rol de aplicación (sección 15). Se ejecuta una sola vez
-- contra el Postgres del servidor, después de las migraciones 001-011.
--
-- Los GRANT de abajo son más específicos que el borrador de la sección 15:
-- se ampliaron con lo que se descubrió necesario al probar la plataforma
-- de punta a punta contra un Postgres real (ver DECISIONES.md, decisión 8).
--
-- CREATE ROLE va aparte (fuera de este script, o descomentado abajo) porque
-- la contraseña real nunca debe quedar en un archivo versionado.

-- CREATE ROLE app_riesgo LOGIN PASSWORD 'definida_en_env';

GRANT USAGE ON SCHEMA core, staging, proc, res, audit TO app_riesgo;

GRANT SELECT ON ALL TABLES IN SCHEMA core TO app_riesgo;
-- Alta de usuarios (admin) y de límites de cupo con vigencia (admin):
GRANT INSERT, UPDATE ON core.usuario TO app_riesgo;
GRANT INSERT, UPDATE ON core.limite_cupo TO app_riesgo;

GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA staging, proc, res, audit TO app_riesgo;
-- Actualizaciones puntuales que el borrador original de la sección 15 no
-- cubría y que el flujo real sí necesita:
GRANT UPDATE ON staging.carga TO app_riesgo;         -- ruta_archivo tras guardar en disco
GRANT UPDATE ON proc.corrida TO app_riesgo;           -- EJECUTANDO -> OK/ERROR/ANULADA
GRANT UPDATE ON audit.destinatario TO app_riesgo;     -- acuse de lectura (visto_en)

GRANT USAGE ON ALL SEQUENCES IN SCHEMA core, staging, proc, res, audit TO app_riesgo;

-- Sin BYPASSRLS. Es lo que hace efectivas las políticas de las
-- migraciones 006, 009, 010 y 011 — ver sección 7, advertencia
-- "La API nunca se conecta como superusuario".
