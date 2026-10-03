import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django_asgi = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from commerce.routing import websocket_urlpatterns  # noqa: E402
from commerce.ws_auth import QueryJwtAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi,
        "websocket": QueryJwtAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
