#!/bin/sh
set -eu

domain=${APP_DOMAIN:-}
email=${CERTBOT_EMAIL:-}

if [ -z "$domain" ] || [ -z "$email" ]; then
  echo "certbot: APP_DOMAIN or CERTBOT_EMAIL is empty. nginx will keep serving HTTP."
  while true; do
    sleep 3600 &
    wait $!
  done
fi

case "$domain" in
  *[!A-Za-z0-9.-]*)
    echo "certbot: APP_DOMAIN must be a hostname" >&2
    exit 1
    ;;
esac

case "$email" in
  *@*.*) ;;
  *)
    echo "certbot: CERTBOT_EMAIL must be an email address" >&2
    exit 1
    ;;
esac

staging_args=""
case "${CERTBOT_STAGING:-false}" in
  1|true|yes) staging_args="--staging" ;;
esac

live="/etc/letsencrypt/live/${domain}/fullchain.pem"

echo "certbot: waiting for nginx"
ready=0
attempt=0
while [ "$attempt" -lt 60 ]; do
  if python3 - <<'PY'
import urllib.request
urllib.request.urlopen("http://nginx/nginx-health", timeout=3).read()
PY
  then
    ready=1
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  echo "certbot: nginx did not answer. Certificate requests will keep retrying." >&2
fi

while [ ! -f "$live" ]; do
  echo "certbot: requesting a certificate for ${domain}"
  # shellcheck disable=SC2086
  if certbot certonly \
    --webroot -w /var/www/certbot \
    --cert-name "$domain" \
    -d "$domain" \
    --email "$email" \
    --agree-tos \
    --no-eff-email \
    --non-interactive \
    --keep-until-expiring \
    $staging_args
  then
    break
  fi
  echo "certbot: request failed. Retrying in 60 seconds." >&2
  sleep 60
done

echo "certbot: certificate is ready"
while true; do
  # shellcheck disable=SC2086
  certbot renew --non-interactive $staging_args \
    || echo "certbot: renewal attempt failed" >&2
  sleep 43200 &
  wait $!
done
