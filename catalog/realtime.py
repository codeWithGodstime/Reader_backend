import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def saved_group_name(user_id):
    return f"saved.{user_id}"


def saved_snapshot(user):
    """Default shelf (or the first shelf) in the shape GET /api/v1/shelves/{id} returns.

    Clients treat that payload's books as the saved-items list. ``saved_book_count``
    is the distinct total across every shelf, matching the profile badge. A reader
    with no shelf yet gets an empty list and no shelf is created.
    """
    from catalog.models import Shelf
    from catalog.views import _shelf_payload

    saved_book_count = (
        Shelf.books.through.objects.filter(shelf__user=user).values("book_id").distinct().count()
    )
    shelf = user.shelves.filter(is_default=True).first() or user.shelves.first()
    if shelf is None:
        return {
            "id": None,
            "name": "Saved",
            "is_default": True,
            "book_count": 0,
            "books": [],
            "saved_book_count": saved_book_count,
        }
    payload = _shelf_payload(shelf, user, with_books=True)
    payload["saved_book_count"] = saved_book_count
    return payload


def publish_saved(user):
    """Push this user's saved-items snapshot to group saved.<user id>."""
    payload = saved_snapshot(user)
    layer = get_channel_layer()
    if layer is None:
        return payload
    try:
        async_to_sync(layer.group_send)(
            saved_group_name(user.id),
            {"type": "saved.updated", "saved": payload},
        )
    except Exception:
        logger.exception("Saved-items broadcast failed for user %s", user.id)
    return payload
