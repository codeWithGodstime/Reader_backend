from django.urls import path

from commerce.consumers import CartConsumer, SavedConsumer

websocket_urlpatterns = [
    path("ws/cart/", CartConsumer.as_asgi()),
    path("ws/saved/", SavedConsumer.as_asgi()),
]
