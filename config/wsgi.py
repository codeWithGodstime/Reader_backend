import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application

_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.is_file():
    import environ

    environ.Env.read_env(_env_file)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_wsgi_application()
