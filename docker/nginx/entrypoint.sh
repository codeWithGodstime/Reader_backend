#!/bin/sh
set -eu

templates=/opt/nginx
conf=/etc/nginx/conf.d/reader.conf
domain=${APP_DOMAIN:-}

case "$domain" in
  "")
    server_name=_
    ;;
  *[!A-Za-z0-9.-]*)
    echo "nginx: APP_DOMAIN must be a hostname" >&2
    exit 1
    ;;
  *)
    server_name=$domain
    ;;
esac

cert_path=""
if [ -n "$domain" ]; then
  cert_path="/etc/letsencrypt/live/${domain}/fullchain.pem"
fi

fingerprint() {
  if [ -n "$cert_path" ] && [ -f "$cert_path" ]; then
    sha256sum "$cert_path" | awk '{print $1}'
  else
    printf '%s' none
  fi
}

write_config() {
  mode=$1
  tmp=${conf}.tmp
  if [ "$mode" = "none" ]; then
    sed "s/__SERVER_NAME__/${server_name}/g" "$templates/http.conf" > "$tmp"
  else
    {
      sed "s/__SERVER_NAME__/${server_name}/g" "$templates/redirect.conf"
      sed \
        -e "s/__SERVER_NAME__/${server_name}/g" \
        -e "s/__DOMAIN__/${domain}/g" \
        "$templates/https.conf"
    } > "$tmp"
  fi
  mv "$tmp" "$conf"
}

apply_config() {
  mode=$1
  previous=${conf}.prev
  if [ -f "$conf" ]; then
    cp "$conf" "$previous"
  fi
  write_config "$mode"
  if nginx -t; then
    return 0
  fi
  echo "nginx: configuration test failed" >&2
  if [ -f "$previous" ]; then
    cp "$previous" "$conf"
  fi
  return 1
}

rm -f /etc/nginx/conf.d/default.conf
mkdir -p /etc/nginx/conf.d /var/www/certbot

current=$(fingerprint)
if ! apply_config "$current"; then
  exit 1
fi

nginx -g 'daemon off;' &
nginx_pid=$!

shutdown() {
  if [ -n "${sleep_pid:-}" ]; then
    kill "$sleep_pid" 2>/dev/null || true
  fi
  nginx -s quit 2>/dev/null || true
  wait "$nginx_pid" 2>/dev/null || true
  exit 0
}
trap shutdown TERM INT

sleep_pid=
while kill -0 "$nginx_pid" 2>/dev/null; do
  sleep 10 &
  sleep_pid=$!
  wait "$sleep_pid" || true
  sleep_pid=
  if ! kill -0 "$nginx_pid" 2>/dev/null; then
    break
  fi
  next=$(fingerprint)
  if [ "$next" != "$current" ]; then
    echo "nginx: certificate changed; reloading"
    if apply_config "$next"; then
      current=$next
      nginx -s reload
    fi
  fi
done

wait "$nginx_pid"
