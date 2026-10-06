#!/bin/sh
set -eu

cd /app
mkdir -p /app/staticfiles /app/media
chown -R app:app /app/staticfiles /app/media
chmod 755 /app/staticfiles /app/media

exec runuser -u app -- /app/docker/start.sh "$@"
