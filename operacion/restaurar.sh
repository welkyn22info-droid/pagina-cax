#!/bin/bash
# Restaura un respaldo en una base limpia. Pensado para que alguien de
# sistemas lo pueda seguir sin conocer el proyecto (sección 16).
#
# Uso:
#   ./restaurar.sh /respaldos/riesgo_20260830_2000.dump.gz [nombre_base_destino]
#
# Por defecto restaura en una base nueva "riesgo_restaurada" para no tocar
# la base en producción por error. Para restaurar sobre la base real,
# pasar explícitamente "riesgo" como segundo argumento y confirmar que
# se entiende que esto reemplaza los datos actuales.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: $0 <archivo.dump.gz> [base_destino]" >&2
  exit 1
fi

ARCHIVO_GZ="$1"
BASE_DESTINO="${2:-riesgo_restaurada}"

if [ ! -f "$ARCHIVO_GZ" ]; then
  echo "ERROR: no existe el archivo $ARCHIVO_GZ" >&2
  exit 1
fi

echo "Esto va a crear/reemplazar la base '$BASE_DESTINO' con el contenido de $ARCHIVO_GZ."
read -p "¿Continuar? (escriba 'si' para confirmar) " CONFIRMACION
if [ "$CONFIRMACION" != "si" ]; then
  echo "Cancelado."
  exit 1
fi

ARCHIVO_DUMP="${ARCHIVO_GZ%.gz}"
gunzip -k "$ARCHIVO_GZ"

docker compose exec -T db psql -U "$DB_SUPERUSUARIO" -c "DROP DATABASE IF EXISTS $BASE_DESTINO;"
docker compose exec -T db psql -U "$DB_SUPERUSUARIO" -c "CREATE DATABASE $BASE_DESTINO;"
docker compose exec -T db pg_restore -U "$DB_SUPERUSUARIO" -d "$BASE_DESTINO" < "$ARCHIVO_DUMP"

rm -f "$ARCHIVO_DUMP"

echo "Restauración completada en la base '$BASE_DESTINO'."
echo "Verificar antes de usarla en producción:"
echo "  docker compose exec -T db psql -U \$DB_SUPERUSUARIO -d $BASE_DESTINO -c \"SELECT count(*) FROM proc.corrida;\""
echo "  docker compose exec -T db psql -U \$DB_SUPERUSUARIO -d $BASE_DESTINO -c \"SELECT count(*) FROM res.valoracion;\""
