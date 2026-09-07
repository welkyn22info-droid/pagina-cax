-- El usuario prefiere las columnas de auditoría directo en staging.curva_nodo
-- en vez de una vista aparte (la de la migración 015) — no quiere tener que
-- acordarse de consultar otro objeto. Se reemplaza la vista por columnas
-- reales.

DROP VIEW staging.curva_nodo_auditoria;

ALTER TABLE staging.curva_nodo ADD COLUMN fecha_cargue    timestamptz NOT NULL DEFAULT now();
ALTER TABLE staging.curva_nodo ADD COLUMN usuario_carga   bigint REFERENCES core.usuario(id);
ALTER TABLE staging.curva_nodo ADD COLUMN anulado         boolean NOT NULL DEFAULT false;
ALTER TABLE staging.curva_nodo ADD COLUMN usuario_anulado bigint REFERENCES core.usuario(id);

-- Backfill de las filas que ya existían: sin esto quedarían con
-- fecha_cargue = ahora mismo y usuario_carga = NULL, que no reflejan la
-- realidad de cuándo/quién las cargó — el dato real ya vive en staging.carga.
UPDATE staging.curva_nodo cn
SET fecha_cargue    = c.cargado_en,
    usuario_carga   = c.cargado_por,
    anulado         = (c.anulada_en IS NOT NULL),
    usuario_anulado = c.anulada_por
FROM staging.carga c
WHERE c.id = cn.carga_id;

ALTER TABLE staging.curva_nodo ALTER COLUMN usuario_carga SET NOT NULL;

-- Con esto, staging.curva_nodo queda con una copia de fecha_cargue/
-- usuario_carga/anulado/usuario_anulado que puede desincronizarse de
-- staging.carga si algo las actualiza en un lado y no en el otro. El único
-- punto de escritura de "anulado" es POST /cargas/{id}/anular
-- (app/rutas/cargas.py), que ahora actualiza las dos tablas en la misma
-- transacción — no hay otro camino de escritura.
--
-- Política de UPDATE nueva: hoy solo había SELECT e INSERT en
-- staging.curva_nodo (migración 013). anular_carga necesita poder marcar
-- anulado/usuario_anulado — mismo patrón permisivo que
-- proc.corrida.actualizar_corrida (decisión 8): el permiso de fondo ya se
-- comprobó en la API antes de llegar aquí.
CREATE POLICY anular_curva_nodo ON staging.curva_nodo FOR UPDATE
  USING (true) WITH CHECK (true);
