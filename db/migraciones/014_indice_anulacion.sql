-- El índice único de la migración 003 (ux_carga_hash_fecha) impide subir
-- dos veces el mismo archivo para la misma fecha — correcto en general,
-- pero no distingue una carga anulada: si se anula una carga por error, el
-- mismo archivo vuelve a chocar contra su propio hash y no se puede
-- recargar. Se reemplaza por un índice único PARCIAL: la restricción de
-- "no repetido" solo aplica entre cargas vigentes (anulada_en IS NULL) —
-- una carga anulada libera su hash para que el mismo archivo pueda
-- volver a subirse. Se descubrió probando el flujo real de anular +
-- recargar curvas (decisión 18).

DROP INDEX staging.ux_carga_hash_fecha;

CREATE UNIQUE INDEX ux_carga_hash_fecha
  ON staging.carga (tipo_insumo, fecha_datos, hash_sha256)
  WHERE anulada_en IS NULL;
