#!/bin/sh
set -e

cd /app

# Verifica se a tabela alembic_version já existe
HAS_ALEMBIC=$(python3 -c "
import sqlite3, os
db = 'data/cv_tailor.db'
if not os.path.exists(db):
    print('no')
else:
    conn = sqlite3.connect(db)
    cur = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'\")
    print('yes' if cur.fetchone() else 'no')
    conn.close()
")

if [ \"$HAS_ALEMBIC\" = \"no\" ]; then
    # Verifica se as tabelas já existem (banco de produção sem alembic)
    HAS_TABLES=$(python3 -c "
import sqlite3, os
db = 'data/cv_tailor.db'
if not os.path.exists(db):
    print('no')
else:
    conn = sqlite3.connect(db)
    cur = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='users'\")
    print('yes' if cur.fetchone() else 'no')
    conn.close()
")

    if [ \"$HAS_TABLES\" = \"yes\" ]; then
        echo '[entrypoint] Banco existente sem Alembic — aplicando baseline 0001...'
        alembic stamp 0001
    fi
fi

echo '[entrypoint] Rodando migrations...'
alembic upgrade head

echo '[entrypoint] Iniciando servidor...'
exec uvicorn app.main:app --host 0.0.0.0 --port 8000