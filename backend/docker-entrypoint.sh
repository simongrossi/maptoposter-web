#!/bin/sh
# Demarre en root uniquement pour reparer l'ownership d'un volume existant
# (par exemple osm_cache cree par l'ancienne image root), puis abandonne les
# privileges avant d'executer uvicorn ou celery.
set -e

if [ "$(id -u)" = "0" ]; then
    mkdir -p /.cache /app/.cache 2>/dev/null || true
    chown -R app:app /.cache /app/.cache 2>/dev/null || true
    exec setpriv --reuid=10001 --regid=10001 --init-groups "$@"
fi

exec "$@"
