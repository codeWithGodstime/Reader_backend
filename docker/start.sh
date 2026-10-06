#!/bin/sh
set -eu

cd /app
umask 022

eval "$(python - <<'PY'
import os
import sys
from urllib.parse import quote


def sh_quote(value):
    return "'" + value.replace("'", "'\\''") + "'"


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"Set {name}.")
    return value


user = quote(required("POSTGRES_USER"), safe="")
password = quote(required("POSTGRES_PASSWORD"), safe="")
name = quote(required("POSTGRES_DB"), safe="")
host = os.environ.get("POSTGRES_HOST", "db").strip() or "db"
port = os.environ.get("POSTGRES_PORT", "5432").strip() or "5432"
if any(char in host for char in " \t/?#@"):
    sys.exit("POSTGRES_HOST is invalid.")

secret = os.environ.get("SECRET_KEY", "")
if secret in {
    "",
    "dev-only-change-me",
    "dev-only-reader-secret-key-not-for-production",
}:
    sys.exit("Set SECRET_KEY to a long random value.")

domain = os.environ.get("APP_DOMAIN", "").strip()
hosts = [
    item.strip()
    for item in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if item.strip()
]
if domain and domain not in hosts:
    hosts.append(domain)
if not hosts:
    sys.exit("Set ALLOWED_HOSTS.")

url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
print(f"export DATABASE_URL={sh_quote(url)}")
print(f"export ALLOWED_HOSTS={sh_quote(','.join(hosts))}")
PY
)"

# Local .env sets BEHIND_HTTPS_PROXY=false for runserver. This stack decides
# from the certificate instead: nginx is the TLS endpoint.
domain=${APP_DOMAIN:-}
email=${CERTBOT_EMAIL:-}
cert=""
if [ -n "$domain" ]; then
  cert="/etc/letsencrypt/live/${domain}/fullchain.pem"
fi
if [ -n "$cert" ] && [ -n "$email" ] && [ ! -f "$cert" ]; then
  echo "waiting up to 3 minutes for a TLS certificate"
  i=0
  while [ "$i" -lt 90 ]; do
    if [ -f "$cert" ]; then
      break
    fi
    i=$((i + 1))
    sleep 2
  done
fi
if [ -n "$cert" ] && [ -f "$cert" ]; then
  export BEHIND_HTTPS_PROXY=true
  echo "TLS certificate found"
else
  export BEHIND_HTTPS_PROXY=false
  if [ -n "$domain" ] && [ -n "$email" ]; then
    echo "TLS certificate is not ready. Starting on HTTP." >&2
    echo "After certbot finishes, recreate api so Django trusts HTTPS." >&2
  fi
fi

python - <<'PY'
import os
import sys
import time

import psycopg

url = os.environ["DATABASE_URL"]
error = "not attempted"
for _ in range(60):
    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        sys.exit(0)
    except Exception as exc:
        error = exc
        time.sleep(1)
sys.exit(f"Postgres is not ready: {error}")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput
chmod -R a+rX /app/staticfiles /app/media

case "${SEED:-0}" in
  1|true|yes)
    python manage.py seed_reader
    chmod -R a+rX /app/media
    ;;
esac

exec "$@"
