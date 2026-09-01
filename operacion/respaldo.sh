#!/bin/bash
# Respaldo diario de la base y verificación mínima de que el dump no está
# vacío. Un solo servidor es un solo punto de falla (sección 16): esto se
# implementa y se prueba antes de que exista el primer resultado real.
set -euo pipefail

FECHA=$(date +%Y%m%d_%H%M)
DESTINO_LOCAL="/respaldos"
DESTINO_RED="/mnt/red/respaldos-riesgo"    # carpeta de red que provea sistemas

ARCHIVO="$DESTINO_LOCAL/riesgo_$FECHA.dump"

docker compose exec -T db pg_dump -U "$DB_SUPERUSUARIO" -Fc riesgo > "$ARCHIVO"

if [ ! -s "$ARCHIVO" ]; then
  echo "ERROR: el dump quedó vacío. No se continúa con la compresión ni la copia." >&2
  rm -f "$ARCHIVO"
  exit 1
fi

gzip "$ARCHIVO"

# Copia fuera del servidor
if [ -d "$DESTINO_RED" ]; then
  cp "$ARCHIVO.gz" "$DESTINO_RED/" || echo "ADVERTENCIA: falló la copia a red"
else
  echo "ADVERTENCIA: $DESTINO_RED no está montado. El respaldo solo quedó en el servidor." >&2
fi

# Retención: 30 días local, 6 meses en red
find "$DESTINO_LOCAL" -name "riesgo_*.dump.gz" -mtime +30 -delete
if [ -d "$DESTINO_RED" ]; then
  find "$DESTINO_RED" -name "riesgo_*.dump.gz" -mtime +180 -delete
fi

echo "Respaldo completado: riesgo_$FECHA.dump.gz"
