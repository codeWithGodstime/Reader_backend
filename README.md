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

Cart changes (add, update, remove, voucher, checkout, buy-again) are broadcast to `ws://<host>/ws/cart/?token=<access JWT>` for that user only. The channel layer is in-memory and stays inside one process. Production should run one Daphne process: `daphne -b 0.0.0.0 -p $PORT config.asgi:application`. More than one worker needs a Redis channel layer, which is not configured.

Unset `DJANGO_SETTINGS_MODULE` uses `config.settings.local`. Production must set `DJANGO_SETTINGS_MODULE=config.settings.production` and provide `SECRET_KEY`, `ALLOWED_HOSTS`, a Postgres `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, and `GOOGLE_OAUTH_CLIENT_IDS`. Copy `.env.example` to `.env` for local values. Do not commit `.env`.

`GOOGLE_OAUTH_CLIENT_IDS` is a comma-separated list of Google OAuth client IDs for web and mobile. ID-token sign-in does not use a client secret.

CORS allows `localhost:3000`, `localhost:5173`, and common Expo web ports (`8081`, `19006`, and any other `localhost` or `127.0.0.1` port).

## Sample reader

| | |
| --- | --- |
| Email | `elena.rostova@reader.example` |
| Password | `shelf-reader-4802` |
| Voucher | `GUILD24` ($24 off, once) |

`seed_reader` reloads the catalog, restores Elena's sample cart, and resets that voucher. It does not delete orders you place afterward.
