# Reader API

Django REST API for the Reader bookstore. The contract is [`openapi.yaml`](openapi.yaml), summarized in [`API_CONTRACT.md`](API_CONTRACT.md).

Base URL: `http://127.0.0.1:8001`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_reader
python manage.py runserver
```

`runserver` listens on `127.0.0.1:$PORT` (default `8001`) when no address is passed. Daphne is first in `INSTALLED_APPS`, so that command is the ASGI server and also serves websockets. Docs: `http://127.0.0.1:8001/api/docs/`

Cart changes (add, update, remove, voucher, checkout, buy-again) are broadcast to `ws://<host>/ws/cart/?token=<access JWT>` for that user only. The channel layer is in-memory and stays inside one process. More than one worker needs a Redis channel layer, which is not configured.

## Docker

Compose runs one Daphne container, Postgres, nginx, and Certbot. nginx is the only service published on the host (`80` and `443`). Daphne and Postgres stay on the Compose network. Do not scale `api`.

```bash
cp .env.example .env
```

Set `SECRET_KEY` to a long random value, and set `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `GOOGLE_OAUTH_CLIENT_IDS`, and `POSTGRES_PASSWORD`. Compose does not read `DATABASE_URL`; the API connects to the Postgres service.

```bash
docker compose up -d --build
```

Leave `APP_DOMAIN` and `CERTBOT_EMAIL` empty to serve HTTP at `http://localhost/`. Docs: `http://localhost/api/docs/`.

For HTTPS, point `APP_DOMAIN` at this host, set `CERTBOT_EMAIL`, and include that hostname in `ALLOWED_HOSTS`. Certbot uses the HTTP-01 challenge, then nginx reloads with the certificate and redirects HTTP to HTTPS. `CERTBOT_STAGING=true` requests a staging certificate. Open ports 80 and 443 on the host firewall. If the certificate arrives after the API has started, run `docker compose up -d --force-recreate api`.

`SEED=1` loads the sample catalog on startup. To load it later: `docker compose exec api python manage.py seed_reader`.

Volumes keep Postgres data, uploaded media, collected static files, and Let's Encrypt certificates. `docker compose down` leaves them in place.

On a host without Docker, `sudo ./deploy/setup-server.sh` installs the same pieces with systemd: packages, Postgres, nginx, Certbot, and one Daphne process on `127.0.0.1:8001`.

Unset `DJANGO_SETTINGS_MODULE` uses `config.settings.local`. Production must set `DJANGO_SETTINGS_MODULE=config.settings.production` and provide `SECRET_KEY`, `ALLOWED_HOSTS`, a Postgres `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, and `GOOGLE_OAUTH_CLIENT_IDS`. Copy `.env.example` to `.env` for local values. Do not commit `.env`.

`GOOGLE_OAUTH_CLIENT_IDS` is a comma-separated list of Google OAuth client IDs for web and mobile. ID-token sign-in does not use a client secret.

CORS allows `localhost:3000`, `localhost:5173`, and common Expo web ports (`8081`, `19006`, and any other `localhost` or `127.0.0.1` port).

## Sample reader

| | |
| --- | --- |
| Email | `elena.rostova@reader.example` |
| Password | `shelf-reader-4802` |
| Voucher | `GUILD24` ($24 off, once) |
| Admin email | `admin@reader.example` |
| Admin password | `shelf-admin-4802` |

`seed_reader` reloads the catalog, restores Elena's sample cart, resets that voucher, and creates the Django admin superuser. It does not delete orders you place afterward. Admin: `http://127.0.0.1:8001/admin/`.
