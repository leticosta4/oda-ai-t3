#!/bin/bash
set -e

CONTAINER="ia-t3"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-oda_db}"
DUMP="backup.sql"

if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER$"; then
  echo "Erro: Container '$CONTAINER' não está rodando."
  echo "Execute 'docker compose up -d postgres' primeiro."
  exit 1
fi

if [ ! -f "$DUMP" ]; then
  echo "Erro: Arquivo '$DUMP' não encontrado na raiz do projeto."
  exit 1
fi

echo "Copiando $DUMP para dentro do container..."
docker cp "$DUMP" "$CONTAINER:/tmp/$DUMP"

TOTAL_TABLES=$(docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc "
  SELECT count(*) FROM information_schema.tables
  WHERE table_schema = 'public';
" 2>/dev/null || echo "0")

if [ "$TOTAL_TABLES" -gt 0 ]; then
  echo "Banco '$DB_NAME' já contém $TOTAL_TABLES tabelas. Restore ignorado."
  echo "Se quiser forçar o restore, use: pg_restore --clean --if-exists"
else
  echo "Banco vazio. Executando pg_restore..."
  docker exec "$CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" "/tmp/$DUMP"
  echo "Restore concluído com sucesso."
fi

docker exec "$CONTAINER" rm "/tmp/$DUMP"
