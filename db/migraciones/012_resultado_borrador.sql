-- Estado intermedio entre "el Python ya calculó" y "el resultado es oficial
-- en res.*" (ver DECISIONES.md, decisión 17). El cálculo cae primero en
-- proc.resultado_borrador; un revisor lo audita (pantalla o exportado) y
-- decide confirmar (recién ahí se escribe en res.*) o descartar.

ALTER TYPE proc.estado_corrida ADD VALUE 'PENDIENTE_CONFIRMACION' AFTER 'EJECUTANDO';

CREATE TABLE proc.resultado_borrador (
  id            bigserial PRIMARY KEY,
  corrida_id    bigint NOT NULL UNIQUE REFERENCES proc.corrida(id) ON DELETE CASCADE,
  tabla_destino text NOT NULL,   -- 'res.valoracion' | 'res.pasivo' | 'res.funding_ratio' | 'res.consumo_cupo'
  datos         jsonb NOT NULL,  -- filas calculadas, mismas columnas que la tabla destino
  filas         integer NOT NULL,
  creado_en     timestamptz NOT NULL DEFAULT now(),
  aplicado_en   timestamptz     -- se estampa al confirmar; evita aplicar dos veces el mismo borrador
);

ALTER TABLE proc.corrida ADD COLUMN confirmada_por bigint REFERENCES core.usuario(id);
ALTER TABLE proc.corrida ADD COLUMN confirmada_en  timestamptz;

-- RLS: mismo criterio que proc.corrida (ver_corrida, migración 006) — se ve
-- el borrador de lo que se puede ver. Escritura y borrado permisivos porque
-- solo los toca el motor (guardar) y el endpoint de confirmar/anular
-- (aplicar/descartar), ambos ya validados en la API — mismo patrón que
-- proc.corrida en la migración 010 (decisión 8).
ALTER TABLE proc.resultado_borrador ENABLE ROW LEVEL SECURITY;

CREATE POLICY ver_resultado_borrador ON proc.resultado_borrador FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM proc.corrida c
    WHERE c.id = proc.resultado_borrador.corrida_id
      AND core.puede(c.proceso, 'ver')
  ));

CREATE POLICY guardar_resultado_borrador ON proc.resultado_borrador FOR INSERT
  WITH CHECK (true);

CREATE POLICY actualizar_resultado_borrador ON proc.resultado_borrador FOR UPDATE
  USING (true) WITH CHECK (true);

CREATE POLICY borrar_resultado_borrador ON proc.resultado_borrador FOR DELETE
  USING (true);
