-- Ajustes pedidos tras revisar la tabla en pgAdmin: quitar campos_extra
-- (no se usa — las 3 columnas de curvas ya están mapeadas explícitamente,
-- a diferencia de posiciones/precios/flujos_pasivo, que sí dejan cosas sin
-- mapear ahí) y exponer en una sola vista quién cargó, cuándo, y si esa
-- carga está anulada — sin tener que escribir el JOIN a mano cada vez.
--
-- La anulación sigue viviendo en staging.carga, no en cada fila de
-- curva_nodo: se anula el día completo (una carga = un archivo = un día),
-- no nodo por nodo. La vista solo lo hace visible sin JOIN.

ALTER TABLE staging.curva_nodo DROP COLUMN campos_extra;

CREATE VIEW staging.curva_nodo_auditoria AS
SELECT
  cn.id,
  cn.carga_id,
  cn.tipo_curva,
  cn.nodo,
  cn.valor,
  cn.fecha_datos,
  c.cargado_en                                   AS fecha_cargue,
  uc.nombre                                       AS usuario_carga,
  CASE WHEN c.anulada_en IS NOT NULL THEN 'Sí' ELSE 'No' END AS anulado,
  ua.nombre                                       AS usuario_anulado
FROM staging.curva_nodo cn
JOIN staging.carga c       ON c.id = cn.carga_id
JOIN core.usuario uc       ON uc.id = c.cargado_por
LEFT JOIN core.usuario ua  ON ua.id = c.anulada_por;

-- Una vista normal (no SECURITY DEFINER) respeta el RLS de las tablas de
-- abajo según quién consulta — no hace falta política propia. El GRANT
-- vive en operacion/preparar_rol.sql, junto con los demás.
