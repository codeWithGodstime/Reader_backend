import environ
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

env = environ.Env()


def _required(name):
    value = env(name, default="").strip()
    if not value:
        raise ImproperlyConfigured(f"Set {name} in the environment.")
    return value


SECRET_KEY = _required("SECRET_KEY")
DEBUG = False

ALLOWED_HOSTS = [host.strip() for host in env.list("ALLOWED_HOSTS", default=[]) if host.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS in the environment.")

_database_url = _required("DATABASE_URL")
DATABASES = {"default": env.db_url_config(_database_url)}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("DATABASE_URL must be a Postgres URL.")

CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in env.list("CORS_ALLOWED_ORIGINS", default=[]) if origin.strip()
]
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured("Set CORS_ALLOWED_ORIGINS in the environment.")

GOOGLE_OAUTH_CLIENT_IDS = [
    client_id.strip()
    for client_id in env.list("GOOGLE_OAUTH_CLIENT_IDS", default=[])
    if client_id.strip()
]
if not GOOGLE_OAUTH_CLIENT_IDS:
    raise ImproperlyConfigured("Set GOOGLE_OAUTH_CLIENT_IDS in the environment.")

BEHIND_HTTPS_PROXY = env.bool("BEHIND_HTTPS_PROXY", default=False)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = BEHIND_HTTPS_PROXY
if BEHIND_HTTPS_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0 and env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
