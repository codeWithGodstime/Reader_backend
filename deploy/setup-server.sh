#!/usr/bin/env bash
# Install the Reader API on Ubuntu or Debian.
#
# Packages, a local Postgres database (unless DATABASE_URL is set), an nginx
# reverse proxy, a single Daphne service, and a firewall that allows SSH,
# HTTP, and HTTPS. Daphne binds to 127.0.0.1 only. The env file is
# $APP_DIR/.env (default /opt/reader-api/.env). Re-running the script updates
# the app code, dependencies, and migrations, and fills env keys that are
# missing or empty. Existing values are left in place. An old
# /etc/reader-api.env is copied across once when the app env file is absent.
#
#   sudo ./deploy/setup-server.sh
#
# Optional environment. CORS origins and Google client IDs are prompted on a
# terminal when still empty. The hostname and certificate email are prompted
# only while the env file does not exist yet.
#   APP_DOMAIN               public hostname; empty serves HTTP for any host
#   CERTBOT_EMAIL            Let's Encrypt email; with APP_DOMAIN, requests a cert
#   CORS_ALLOWED_ORIGINS     comma-separated browser origins
#   GOOGLE_OAUTH_CLIENT_IDS  comma-separated Google OAuth client IDs
#   ALLOWED_HOSTS            comma-separated hosts; default is the domain, IP, localhost
#   DATABASE_URL             remote Postgres URL; skips the local database
#   DB_NAME, DB_USER         local database name and role (default: reader)
#   DB_PASSWORD              local role password; generated and stored in the env file
#   SECRET_KEY               generated when omitted
#   APP_DIR                  install path (default: /opt/reader-api)
#   DAPHNE_PORT              localhost port (default: 8001)
#   SSH_PORT                 SSH port to allow, when it is not 22
#   SEED=1                   load the sample catalog and reader account

set -euo pipefail

trap 'printf "error: setup failed at line %s\n" "$LINENO" >&2' ERR

APP_USER=reader
LEGACY_ENV_FILE=/etc/reader-api.env
APP_DIR=${APP_DIR:-/opt/reader-api}
DAPHNE_PORT=${DAPHNE_PORT:-}
DB_NAME=${DB_NAME:-reader}
DB_USER=${DB_USER:-reader}
APP_DOMAIN=${APP_DOMAIN:-}
CERTBOT_EMAIL=${CERTBOT_EMAIL:-}
CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:-}
GOOGLE_OAUTH_CLIENT_IDS=${GOOGLE_OAUTH_CLIENT_IDS:-}
ALLOWED_HOSTS=${ALLOWED_HOSTS:-}
DATABASE_URL=${DATABASE_URL:-}
DB_PASSWORD=${DB_PASSWORD:-}
SECRET_KEY=${SECRET_KEY:-}
SSH_PORT=${SSH_PORT:-}
SEED=${SEED:-}
CREATE_LOCAL_DB=0

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

log() {
  printf '\n==> %s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

usage() {
  awk 'NR == 1 { next } /^[^#]/ { exit } { sub(/^# ?/, ""); print }' "$0"
}

read_env_key() {
  local key=$1
  local line
  [[ -f "$ENV_FILE" ]] || return 0
  line=$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)
  line=${line#*=}
  line=${line#\"}
  line=${line%\"}
  printf '%s' "$line"
}

database_is_local() {
  local url=$1
  [[ -z "$url" ]] && return 0
  [[ "$url" =~ @(127\.0\.0\.1|localhost|\[::1\])([:/]|$) ]]
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ $# -gt 0 ]]; then
  usage >&2
  die "This script takes no arguments."
fi

if [[ "$(id -u)" -ne 0 ]]; then
  die "Run as root: sudo $0"
fi

if [[ ! -r /etc/os-release ]]; then
  die "Cannot detect the operating system."
fi
# shellcheck disable=SC1091
source /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) die "This script supports Ubuntu and Debian (found ${ID:-unknown})." ;;
esac

if ! command -v systemctl >/dev/null 2>&1; then
  die "systemd is required."
fi

APP_DIR=$(realpath -m "$APP_DIR")
REPO_DIR=$(realpath -m "$REPO_DIR")
ENV_FILE="$APP_DIR/.env"
case "$APP_DIR" in
  /|/usr|/etc|/var|/bin|/sbin|/root|/home|/opt)
    die "Refusing APP_DIR=$APP_DIR"
    ;;
esac
if [[ "$APP_DIR" != /* ]]; then
  die "APP_DIR must be an absolute path."
fi
if [[ -n "$APP_DOMAIN" && ! "$APP_DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]]; then
  die "APP_DOMAIN must be a hostname."
fi
if [[ -n "$SSH_PORT" && ! "$SSH_PORT" =~ ^[0-9]+$ ]]; then
  die "SSH_PORT must be a TCP port."
fi
if [[ ! "$DB_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
  die "DB_NAME must be a Postgres identifier."
fi
if [[ ! "$DB_USER" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
  die "DB_USER must be a Postgres identifier."
fi

# A saved value wins. Shell values fill keys that are still empty.
use_saved() {
  local var_name=$1
  local key=$2
  local saved
  saved=$(read_env_key "$key")
  if [[ -n "$saved" ]]; then
    printf -v "$var_name" '%s' "$saved"
  fi
}

if [[ ! -f "$ENV_FILE" && -f "$LEGACY_ENV_FILE" ]]; then
  mkdir -p "$APP_DIR"
  cp "$LEGACY_ENV_FILE" "$ENV_FILE"
  log "Copied $LEGACY_ENV_FILE to $ENV_FILE"
fi

use_saved APP_DOMAIN APP_DOMAIN
use_saved DATABASE_URL DATABASE_URL
use_saved SECRET_KEY SECRET_KEY
use_saved ALLOWED_HOSTS ALLOWED_HOSTS
use_saved CORS_ALLOWED_ORIGINS CORS_ALLOWED_ORIGINS
use_saved GOOGLE_OAUTH_CLIENT_IDS GOOGLE_OAUTH_CLIENT_IDS
use_saved DAPHNE_PORT PORT
DAPHNE_PORT=${DAPHNE_PORT:-8001}
if [[ ! "$DAPHNE_PORT" =~ ^[0-9]+$ ]] || [[ "$DAPHNE_PORT" -lt 1 || "$DAPHNE_PORT" -gt 65535 ]]; then
  die "DAPHNE_PORT must be a TCP port."
fi

prompt() {
  local var_name=$1
  local label=$2
  if [[ -n "${!var_name}" || ! -t 0 ]]; then
    return
  fi
  local answer
  read -r -p "$label" answer || true
  printf -v "$var_name" '%s' "$answer"
}

if [[ ! -f "$ENV_FILE" ]]; then
  prompt APP_DOMAIN "Public hostname (empty for HTTP on any host): "
  if [[ -n "$APP_DOMAIN" ]]; then
    prompt CERTBOT_EMAIL "Let's Encrypt email (empty to skip HTTPS): "
  fi
fi
prompt CORS_ALLOWED_ORIGINS "CORS origins, comma-separated: "
prompt GOOGLE_OAUTH_CLIENT_IDS "Google OAuth client IDs, comma-separated: "

ensure_openssl() {
  if ! command -v openssl >/dev/null 2>&1; then
    apt-get update
    apt-get install -y openssl
  fi
}

if [[ -z "$DATABASE_URL" ]]; then
  ensure_openssl
  : "${DB_PASSWORD:=$(openssl rand -hex 24)}"
  DATABASE_URL="postgres://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}"
  CREATE_LOCAL_DB=1
fi
if [[ -z "$SECRET_KEY" ]]; then
  ensure_openssl
  SECRET_KEY=$(openssl rand -hex 48)
fi
if [[ -z "$ALLOWED_HOSTS" ]]; then
  hosts=()
  add_host() {
    local value=$1
    local existing
    [[ -z "$value" ]] && return
    for existing in "${hosts[@]:-}"; do
      [[ "$existing" == "$value" ]] && return
    done
    hosts+=("$value")
  }
  add_host "$APP_DOMAIN"
  add_host "127.0.0.1"
  add_host "localhost"
  for candidate in $(hostname -I 2>/dev/null || true); do
    if [[ "$candidate" =~ ^[0-9]+(\.[0-9]+){3}$ ]]; then
      add_host "$candidate"
      break
    fi
  done
  ALLOWED_HOSTS=$(IFS=,; printf '%s' "${hosts[*]}")
fi

if [[ -n "$APP_DOMAIN" && ! "$APP_DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]]; then
  die "APP_DOMAIN must be a hostname."
fi

export DEBIAN_FRONTEND=noninteractive

log "Installing packages"
packages=(
  python3
  python3-venv
  python3-dev
  build-essential
  libpq-dev
  nginx
  ufw
  rsync
  curl
  ca-certificates
  openssl
  certbot
  python3-certbot-nginx
)
if database_is_local "$DATABASE_URL"; then
  USE_LOCAL_POSTGRES=1
  packages+=(postgresql postgresql-contrib)
else
  USE_LOCAL_POSTGRES=0
fi
apt-get update
apt-get install -y "${packages[@]}"

log "Creating service user"
if ! getent group "$APP_USER" >/dev/null; then
  groupadd --system "$APP_USER"
fi
if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd \
    --system \
    --gid "$APP_USER" \
    --home-dir "/var/lib/${APP_USER}" \
    --create-home \
    --shell /usr/sbin/nologin \
    "$APP_USER"
fi
usermod -a -G "$APP_USER" "$APP_USER"

log "Configuring the firewall"
if [[ -n "$SSH_PORT" ]]; then
  ufw allow "${SSH_PORT}/tcp" comment 'SSH'
elif ufw app info OpenSSH >/dev/null 2>&1; then
  ufw allow OpenSSH
else
  ufw allow 22/tcp comment 'SSH'
fi
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

if [[ "$USE_LOCAL_POSTGRES" -eq 1 ]]; then
  log "Starting PostgreSQL"
  systemctl enable --now postgresql
  ready=0
  for _ in $(seq 1 30); do
    if runuser -u postgres -- pg_isready -q; then
      ready=1
      break
    fi
    sleep 1
  done
  [[ "$ready" -eq 1 ]] || die "PostgreSQL did not become ready."
fi

if [[ "$USE_LOCAL_POSTGRES" -eq 1 && "$CREATE_LOCAL_DB" -eq 1 ]]; then
  log "Creating the Postgres role and database"
  db_identity=$(mktemp)
  chmod 600 "$db_identity"
  DATABASE_URL="$DATABASE_URL" python3 - > "$db_identity" <<'PY'
import os
import shlex
from urllib.parse import urlparse

parsed = urlparse(os.environ["DATABASE_URL"])
name = (parsed.path or "/").lstrip("/").split("?", 1)[0]
print(f"DB_USER={shlex.quote(parsed.username or '')}")
print(f"DB_PASSWORD={shlex.quote(parsed.password or '')}")
print(f"DB_NAME={shlex.quote(name)}")
PY
  # shellcheck disable=SC1090
  source "$db_identity"
  rm -f "$db_identity"
  [[ -n "$DB_PASSWORD" ]] || die "DATABASE_URL is missing a password."
  if [[ ! "$DB_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]*$ || ! "$DB_USER" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    die "The database name and user in DATABASE_URL must be Postgres identifiers."
  fi
  # psql's \if treats the boolean text "f" as true, so these flags are 0 or 1.
  runuser -u postgres -- psql -v ON_ERROR_STOP=1 \
    --set=role_name="$DB_USER" \
    --set=role_password="$DB_PASSWORD" \
    --set=db_name="$DB_NAME" <<'SQL'
SELECT CASE WHEN EXISTS(SELECT 1 FROM pg_roles WHERE rolname = :'role_name') THEN 1 ELSE 0 END AS role_exists \gset
\if :role_exists
ALTER ROLE :"role_name" WITH LOGIN PASSWORD :'role_password';
\else
CREATE ROLE :"role_name" LOGIN PASSWORD :'role_password';
\endif
SELECT CASE WHEN EXISTS(SELECT 1 FROM pg_database WHERE datname = :'db_name') THEN 1 ELSE 0 END AS db_exists \gset
\if :db_exists
\else
CREATE DATABASE :"db_name" OWNER :"role_name";
\endif
SQL
  runuser -u postgres -- psql -v ON_ERROR_STOP=1 -d "$DB_NAME" \
    --set=role_name="$DB_USER" <<'SQL'
ALTER SCHEMA public OWNER TO :"role_name";
SQL
fi

persist_env() {
  local force_behind=$1
  local behind=$2
  if [[ -f "$ENV_FILE" ]]; then
    log "Updating $ENV_FILE"
  else
    log "Writing $ENV_FILE"
  fi
  SECRET_KEY="$SECRET_KEY" \
  ALLOWED_HOSTS="$ALLOWED_HOSTS" \
  DATABASE_URL="$DATABASE_URL" \
  CORS_ALLOWED_ORIGINS="$CORS_ALLOWED_ORIGINS" \
  GOOGLE_OAUTH_CLIENT_IDS="$GOOGLE_OAUTH_CLIENT_IDS" \
  APP_DOMAIN="$APP_DOMAIN" \
  DAPHNE_PORT="$DAPHNE_PORT" \
  BEHIND_HTTPS_PROXY="$behind" \
  FORCE_BEHIND="$force_behind" \
  ENV_FILE="$ENV_FILE" \
  python3 - <<'PY'
import os
from pathlib import Path

def quote(value):
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'

def unquote(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        body = raw[1:-1]
        return body.replace('\\"', '"').replace("\\\\", "\\")
    return raw

def last_index(lines, key):
    prefix = f"{key}="
    found = None
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            found = index
    return found

def fill(lines, key, value, quoted=True, force=False):
    index = last_index(lines, key)
    rendered = f"{key}={quote(value) if quoted else value}"
    if index is None:
        if value == "" and key == "APP_DOMAIN":
            return
        lines.append(rendered)
        return
    current = unquote(lines[index].split("=", 1)[1])
    if force or current.strip() == "":
        if value == "" and not force:
            return
        lines[index] = rendered

path = Path(os.environ["ENV_FILE"])
lines = path.read_text().splitlines() if path.is_file() else []
if not any(line.startswith("# Reader API") for line in lines):
    lines = [
        "# Reader API. Edit this file, then re-run deploy/setup-server.sh.",
        "# The channel layer is in-memory: run one Daphne process.",
        *lines,
    ]

fill(lines, "DJANGO_SETTINGS_MODULE", "config.settings.production", quoted=False)
fill(lines, "SECRET_KEY", os.environ["SECRET_KEY"])
fill(lines, "ALLOWED_HOSTS", os.environ["ALLOWED_HOSTS"])
fill(lines, "DATABASE_URL", os.environ["DATABASE_URL"])
fill(lines, "CORS_ALLOWED_ORIGINS", os.environ["CORS_ALLOWED_ORIGINS"])
fill(lines, "GOOGLE_OAUTH_CLIENT_IDS", os.environ["GOOGLE_OAUTH_CLIENT_IDS"])
fill(lines, "PORT", os.environ["DAPHNE_PORT"], quoted=False)
fill(lines, "APP_DOMAIN", os.environ.get("APP_DOMAIN", ""))
fill(lines, "SECURE_HSTS_SECONDS", "0", quoted=False)
fill(lines, "SECURE_HSTS_INCLUDE_SUBDOMAINS", "false", quoted=False)
fill(
    lines,
    "BEHIND_HTTPS_PROXY",
    os.environ["BEHIND_HTTPS_PROXY"],
    quoted=False,
    force=os.environ.get("FORCE_BEHIND") == "1",
)

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(lines) + "\n")
PY
  chown "root:${APP_USER}" "$ENV_FILE"
  chmod 640 "$ENV_FILE"
}

persist_env 0 false

log "Installing the application"
if [[ "$REPO_DIR" != "$APP_DIR" ]]; then
  mkdir -p "$APP_DIR"
  rsync -a --delete \
    --exclude '.venv/' \
    --exclude '.env' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude 'db.sqlite3' \
    --exclude 'staticfiles/' \
    --exclude 'media/' \
    --exclude '.git/' \
    "$REPO_DIR/" "$APP_DIR/"
fi
chown -R "${APP_USER}:${APP_USER}" "$APP_DIR"
chmod 755 "$APP_DIR"
if [[ -f "$ENV_FILE" ]]; then
  chown "root:${APP_USER}" "$ENV_FILE"
  chmod 640 "$ENV_FILE"
fi
install -d -o "$APP_USER" -g "$APP_USER" -m 755 "$APP_DIR/media" "$APP_DIR/staticfiles"
if ! runuser -u "$APP_USER" -- test -r "$APP_DIR/manage.py"; then
  die "User ${APP_USER} cannot read ${APP_DIR}. Use a path under /opt."
fi
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  runuser -u "$APP_USER" -- python3 -m venv "$APP_DIR/.venv"
fi
runuser -u "$APP_USER" -- "$APP_DIR/.venv/bin/pip" install --upgrade pip
runuser -u "$APP_USER" -- "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

log "Configuring nginx"
python3 - "$SCRIPT_DIR/nginx/reader-api.conf" /etc/nginx/sites-available/reader-api \
  "$APP_DIR" "${APP_DOMAIN:-_}" "$DAPHNE_PORT" <<'PY'
import pathlib, sys
src, dest, app_dir, server_name, port = sys.argv[1:]
text = pathlib.Path(src).read_text()
text = text.replace("/opt/reader-api", app_dir)
text = text.replace("server_name _;", f"server_name {server_name};")
text = text.replace("127.0.0.1:8001", f"127.0.0.1:{port}")
path = pathlib.Path(dest)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(text)
PY
if [[ ! -e /proc/net/if_inet6 ]]; then
  sed -i '/listen \[::\]:80;/d' /etc/nginx/sites-available/reader-api
fi
ln -sfn /etc/nginx/sites-available/reader-api /etc/nginx/sites-enabled/reader-api
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
if systemctl is-active --quiet nginx; then
  systemctl reload nginx
else
  systemctl start nginx
fi

TLS=0
if [[ -n "$APP_DOMAIN" && -f "/etc/letsencrypt/live/${APP_DOMAIN}/fullchain.pem" ]]; then
  log "Installing the existing certificate into nginx"
  if certbot install --cert-name "$APP_DOMAIN" --nginx --redirect --non-interactive; then
    TLS=1
  else
    printf 'warning: could not install the certificate into nginx. The API stays on HTTP.\n' >&2
  fi
elif [[ -n "$APP_DOMAIN" && -n "$CERTBOT_EMAIL" ]]; then
  log "Requesting a Let's Encrypt certificate"
  if certbot --nginx -d "$APP_DOMAIN" --non-interactive --agree-tos \
      -m "$CERTBOT_EMAIL" --redirect; then
    TLS=1
  else
    printf 'warning: certbot failed. The API stays on HTTP until DNS points here and you re-run this script.\n' >&2
  fi
fi

proxy_flag=false
if [[ "$TLS" -eq 1 ]]; then
  proxy_flag=true
fi

persist_env 1 "$proxy_flag"

log "Installing the systemd service"
python3 - "$SCRIPT_DIR/reader-api.service" /etc/systemd/system/reader-api.service \
  "$APP_DIR" "$DAPHNE_PORT" <<'PY'
import pathlib, sys
src, dest, app_dir, port = sys.argv[1:]
text = pathlib.Path(src).read_text()
text = text.replace("/opt/reader-api", app_dir)
text = text.replace("-p 8001", f"-p {port}")
pathlib.Path(dest).write_text(text)
PY
systemctl daemon-reload

manage() {
  local quoted=()
  local arg
  for arg in "$@"; do
    quoted+=("$(printf '%q' "$arg")")
  done
  runuser -u "$APP_USER" -- bash --noprofile --norc -c "
    set -euo pipefail
    set -a
    source $(printf '%q' "$ENV_FILE")
    set +a
    cd $(printf '%q' "$APP_DIR")
    exec $(printf '%q' "$APP_DIR/.venv/bin/python") manage.py ${quoted[*]}
  "
}

env_value() {
  read_env_key "$1"
}

missing=()
for key in SECRET_KEY ALLOWED_HOSTS DATABASE_URL CORS_ALLOWED_ORIGINS GOOGLE_OAUTH_CLIENT_IDS; do
  if [[ -z "$(env_value "$key")" ]]; then
    missing+=("$key")
  fi
done

if [[ ${#missing[@]} -eq 0 ]]; then
  log "Applying migrations"
  manage migrate --noinput
  manage collectstatic --noinput
  chmod -R a+rX "$APP_DIR/staticfiles" "$APP_DIR/media"
  if [[ "$SEED" == "1" ]]; then
    log "Loading the sample catalog"
    manage seed_reader
  fi
  systemctl enable reader-api
  systemctl restart reader-api
else
  systemctl disable --now reader-api >/dev/null 2>&1 || true
  printf 'warning: not starting the API. Set these in %s and re-run: %s\n' \
    "$ENV_FILE" "${missing[*]}" >&2
fi

if [[ ${#missing[@]} -eq 0 ]]; then
  scheme=http
  smoke_host=127.0.0.1
  if [[ "$TLS" -eq 1 ]]; then
    scheme=https
    smoke_host=$APP_DOMAIN
  fi
  ok=0
  for _ in $(seq 1 30); do
    if curl -fsS -o /dev/null --max-time 2 "${scheme}://${smoke_host}/api/schema/"; then
      ok=1
      break
    fi
    sleep 1
  done
  if [[ "$ok" -ne 1 ]]; then
    printf 'warning: %s://%s/api/schema/ did not respond. Check journalctl -u reader-api.\n' \
      "$scheme" "$smoke_host" >&2
  fi
fi

cat <<EOF

Reader API setup finished.
  App        ${APP_DIR}
  Env        ${ENV_FILE}
  Service    systemctl status reader-api
  Nginx      /etc/nginx/sites-available/reader-api
  Firewall   ufw status
EOF
if [[ -n "$APP_DOMAIN" ]]; then
  public_scheme=http
  if [[ "$TLS" -eq 1 ]]; then
    public_scheme=https
  fi
  printf '  URL        %s://%s/\n' "$public_scheme" "$APP_DOMAIN"
fi
printf 'Daphne listens on 127.0.0.1:%s. That port and Postgres are not open on the firewall.\n' "$DAPHNE_PORT"
