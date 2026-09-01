-- Maestros sintéticos mínimos para poder cargar datos de prueba y correr
-- los procesos con el legado simulado. Nombres y códigos ficticios.

INSERT INTO core.emisor (codigo, nombre, nit, sector, calificacion, pais) VALUES
  ('REPCOL', 'República de Colombia (ficticio)', '899999999-1', 'Soberano',    'AAA', 'CO'),
  ('BANCOL', 'Banco Colombia Ejemplo S.A.',       '890900001-1', 'Financiero',  'AAA', 'CO'),
  ('ECOPET', 'Ecopetrol Ejemplo S.A.',            '899999068-1', 'Energía',     'AA+', 'CO');

INSERT INTO core.contraparte (codigo, nombre, nit, tipo, calificacion) VALUES
  ('FIDUCOL',  'Fiduciaria Colombia Ejemplo S.A.', '860000001-1', 'fiduciaria',   'AAA'),
  ('COMISBOL', 'Comisionista Bolsa Ejemplo S.A.',  '860000002-1', 'comisionista', 'AA+'),
  ('BANDAV',   'Banco Davivienda Ejemplo S.A.',    '860000003-1', 'banco',        'AAA');

INSERT INTO core.instrumento (codigo, isin, emisor_id, tipo, moneda, fecha_emision, fecha_vencimiento, tasa_facial, periodicidad) VALUES
  ('TESJUL27',      'COB07CB00456', (SELECT id FROM core.emisor WHERE codigo='REPCOL'), 'TES',  'COP', '2017-07-24', '2027-07-24', 7.500000, 'anual'),
  ('CDTBANCOL90',   NULL,           (SELECT id FROM core.emisor WHERE codigo='BANCOL'), 'CDT',  'COP', '2026-06-01', '2026-08-30', 9.800000, 'al vencimiento'),
  ('BONOECOPET30',  'COB27CB00789', (SELECT id FROM core.emisor WHERE codigo='ECOPET'), 'bono', 'COP', '2020-11-18', '2030-11-18', 8.200000, 'semestral');

-- Límites de cupo vigentes desde el inicio del año en curso.
INSERT INTO core.limite_cupo (tipo, entidad_id, base, valor_limite, umbral_alerta, vigente_desde, creado_por) VALUES
  ('emisor',      (SELECT id FROM core.emisor WHERE codigo='BANCOL'),      'monto',                50000000000, 0.80, '2026-01-01', (SELECT id FROM core.usuario WHERE correo='admin@riesgo.local')),
  ('emisor',      (SELECT id FROM core.emisor WHERE codigo='ECOPET'),      'monto',                20000000000, 0.75, '2026-01-01', (SELECT id FROM core.usuario WHERE correo='admin@riesgo.local')),
  ('contraparte', (SELECT id FROM core.contraparte WHERE codigo='FIDUCOL'),'porcentaje_portafolio', 0.30,        0.80, '2026-01-01', (SELECT id FROM core.usuario WHERE correo='admin@riesgo.local'));
-- Nota: REPCOL (deuda soberana) y COMISBOL/BANDAV quedan deliberadamente sin
-- límite parametrizado, para ejercitar el estado SIN_LIMITE de la sección 14.
