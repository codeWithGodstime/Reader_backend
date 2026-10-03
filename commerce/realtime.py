import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from commerce.present import cart_payload

logger = logging.getLogger(__name__)


def cart_group_name(user_id):
    return f"cart.{user_id}"


def publish_cart(user, cart):
    """Return the cart snapshot and push it to this user's websocket group."""
    payload = cart_payload(cart)
    layer = get_channel_layer()
    if layer is None:
        return payload
    try:
        async_to_sync(layer.group_send)(
            cart_group_name(user.id),
            {"type": "cart.updated", "cart": payload},
        )
    except Exception:
        logger.exception("Cart broadcast failed for user %s", user.id)
    return payload
