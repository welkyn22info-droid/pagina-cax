-- Esquemas base y modelo de usuarios/permisos.
-- La separación en cinco esquemas (core/staging/proc/res/audit) es la que
-- hace posible la trazabilidad: insumos crudos, ejecución y resultados
-- nunca se mezclan en las mismas tablas. Ver sección 6 de la especificación.

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS proc;
CREATE SCHEMA IF NOT EXISTS res;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TYPE core.rol_usuario AS ENUM (
  'admin',      -- administra usuarios, límites y parámetros
  'analista',   -- carga insumos y ejecuta procesos
  'revisor',    -- aprueba y publica resultados
  'consulta'    -- solo lectura de lo publicado
);

CREATE TABLE core.usuario (
  id             bigserial PRIMARY KEY,
  correo         text NOT NULL UNIQUE,
  nombre         text NOT NULL,
  hash_clave     text NOT NULL,
  rol            core.rol_usuario NOT NULL,
  activo         boolean NOT NULL DEFAULT true,
  debe_cambiar_clave boolean NOT NULL DEFAULT true,
  intentos_fallidos  integer NOT NULL DEFAULT 0,
  bloqueado_hasta    timestamptz,
  creado_en      timestamptz NOT NULL DEFAULT now(),
  ultimo_acceso  timestamptz
);

-- Permiso por rol y módulo. Evita recompilar para cambiar un acceso.
CREATE TABLE core.permiso (
  rol             core.rol_usuario NOT NULL,
  modulo          text NOT NULL,   -- 'valoracion','pasivo','funding_ratio','cupos'
  puede_ver       boolean NOT NULL DEFAULT false,
  puede_cargar    boolean NOT NULL DEFAULT false,
  puede_ejecutar  boolean NOT NULL DEFAULT false,
  puede_publicar  boolean NOT NULL DEFAULT false,
  PRIMARY KEY (rol, modulo)
);
