from datetime import date
from decimal import Decimal
from unittest.mock import patch

from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from catalog.models import Author, Book, BookFormat, Genre
from catalog.realtime import saved_group_name
from commerce.realtime import cart_group_name
from commerce.routing import websocket_urlpatterns
from commerce.ws_auth import QueryJwtAuthMiddleware


def make_book():
    genre = Genre.objects.create(slug="fiction", name="Fiction")
    author = Author.objects.create(slug="ada", name="Ada")
    book = Book.objects.create(
        slug="sample",
        title="Sample",
        description="A book.",
        about="About.",
        author=author,
        genre=genre,
        cover_url="https://example.com/cover.jpg",
        sku="SKU-1",
        pages=100,
        publisher="Press",
        language="English",
        isbn13="9780000000001",
        dimensions="1 x 1",
        published_on=date(2020, 1, 1),
        default_format="paperback",
        price=Decimal("12.00"),
    )
    BookFormat.objects.create(book=book, code="paperback", label="Paperback", price=Decimal("12.00"))
    return book


class RecordingLayer:
    def __init__(self):
        self.sent = []

    async def group_send(self, group, message):
        self.sent.append((group, message))


class CartBroadcastTests(TestCase):
    def test_cart_mutation_broadcasts_to_that_users_group(self):
        user = User.objects.create_user("ada@example.com", "shelf-reader-4802", name="Ada")
        other = User.objects.create_user("bea@example.com", "shelf-reader-4802", name="Bea")
        book = make_book()
        client = APIClient()
        client.force_authenticate(user=user)
        layer = RecordingLayer()

        with patch("commerce.realtime.get_channel_layer", return_value=layer):
            created = client.post(
                "/api/v1/cart/items",
                {"book_id": str(book.id), "format": "paperback", "quantity": 1},
                format="json",
            )
            self.assertEqual(created.status_code, 200)
            item_id = created.json()["items"][0]["id"]
            updated = client.patch(
                f"/api/v1/cart/items/{item_id}",
                {"quantity": 2},
                format="json",
            )
            removed = client.delete(f"/api/v1/cart/items/{item_id}")

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(removed.status_code, 200)
        self.assertEqual([message["cart"]["item_count"] for _, message in layer.sent], [1, 2, 0])
        groups = {group for group, _ in layer.sent}
        self.assertEqual(groups, {cart_group_name(user.id)})
        self.assertNotIn(cart_group_name(other.id), groups)
        self.assertTrue(all(message["type"] == "cart.updated" for _, message in layer.sent))


class CartSocketTests(TransactionTestCase):
    def setUp(self):
        self.application = QueryJwtAuthMiddleware(URLRouter(websocket_urlpatterns))

    async def test_socket_receives_only_its_users_cart(self):
        user = await User.objects.acreate(
            email="ada@example.com",
            name="Ada",
            member_since=date(2024, 1, 1),
            patron_number="1001",
        )
        other = await User.objects.acreate(
            email="bea@example.com",
            name="Bea",
            member_since=date(2024, 1, 1),
            patron_number="1002",
        )
        user.set_password("shelf-reader-4802")
        other.set_password("shelf-reader-4802")
        await user.asave()
        await other.asave()

        owner = WebsocketCommunicator(self.application, f"/ws/cart/?token={AccessToken.for_user(user)}")
        stranger = WebsocketCommunicator(self.application, f"/ws/cart/?token={AccessToken.for_user(other)}")
        anonymous = WebsocketCommunicator(self.application, "/ws/cart/")
        try:
            connected, _ = await owner.connect()
            self.assertTrue(connected)
            stranger_connected, _ = await stranger.connect()
            self.assertTrue(stranger_connected)
            anon_connected, _ = await anonymous.connect()
            self.assertFalse(anon_connected)

            owner_snapshot = await owner.receive_json_from()
            stranger_snapshot = await stranger.receive_json_from()
            self.assertEqual(owner_snapshot["type"], "cart.updated")
            self.assertEqual(stranger_snapshot["cart"]["item_count"], 0)

            payload = {**owner_snapshot["cart"], "item_count": 3}
            await get_channel_layer().group_send(
                cart_group_name(user.id),
                {"type": "cart.updated", "cart": payload},
            )
            delivered = await owner.receive_json_from()
            self.assertEqual(delivered["cart"]["item_count"], 3)
            self.assertTrue(await stranger.receive_nothing(timeout=0.2))
        finally:
            await owner.disconnect()
            await stranger.disconnect()
            await anonymous.disconnect()

    def test_asgi_application_imports(self):
        from config.asgi import application

        self.assertTrue(callable(application))
        self.assertIn("websocket", application.application_mapping)


class SavedBroadcastTests(TestCase):
    def test_saved_mutation_broadcasts_to_that_users_group(self):
        user = User.objects.create_user("ada@example.com", "shelf-reader-4802", name="Ada")
        other = User.objects.create_user("bea@example.com", "shelf-reader-4802", name="Bea")
        book = make_book()
        client = APIClient()
        client.force_authenticate(user=user)
        layer = RecordingLayer()

        with patch("catalog.realtime.get_channel_layer", return_value=layer):
            created = client.post(f"/api/v1/books/{book.id}/save")
            self.assertEqual(created.status_code, 200)
            shelf_id = created.json()["shelf_id"]
            removed = client.delete(f"/api/v1/shelves/{shelf_id}/books/{book.id}")
            unsaved = client.delete(f"/api/v1/books/{book.id}/save")

        self.assertEqual(removed.status_code, 204)
        self.assertEqual(unsaved.status_code, 200)
        self.assertEqual([len(message["saved"]["books"]) for _, message in layer.sent], [1, 0, 0])
        self.assertEqual(layer.sent[0][1]["saved"]["books"][0]["id"], str(book.id))
        self.assertTrue(layer.sent[0][1]["saved"]["books"][0]["saved"])
        groups = {group for group, _ in layer.sent}
        self.assertEqual(groups, {saved_group_name(user.id)})
        self.assertNotIn(saved_group_name(other.id), groups)
        self.assertTrue(all(message["type"] == "saved.updated" for _, message in layer.sent))


class SavedSocketTests(TransactionTestCase):
    def setUp(self):
        self.application = QueryJwtAuthMiddleware(URLRouter(websocket_urlpatterns))

    async def test_socket_receives_only_its_users_saved_items(self):
        user = await User.objects.acreate(
            email="ada@example.com",
            name="Ada",
            member_since=date(2024, 1, 1),
            patron_number="1001",
        )
        other = await User.objects.acreate(
            email="bea@example.com",
            name="Bea",
            member_since=date(2024, 1, 1),
            patron_number="1002",
        )
        user.set_password("shelf-reader-4802")
        other.set_password("shelf-reader-4802")
        await user.asave()
        await other.asave()

        owner = WebsocketCommunicator(self.application, f"/ws/saved/?token={AccessToken.for_user(user)}")
        stranger = WebsocketCommunicator(self.application, f"/ws/saved/?token={AccessToken.for_user(other)}")
        anonymous = WebsocketCommunicator(self.application, "/ws/saved/")
        try:
            connected, _ = await owner.connect()
            self.assertTrue(connected)
            stranger_connected, _ = await stranger.connect()
            self.assertTrue(stranger_connected)
            anon_connected, _ = await anonymous.connect()
            self.assertFalse(anon_connected)

            owner_snapshot = await owner.receive_json_from()
            stranger_snapshot = await stranger.receive_json_from()
            self.assertEqual(owner_snapshot["type"], "saved.updated")
            self.assertEqual(stranger_snapshot["saved"]["books"], [])

            payload = {**owner_snapshot["saved"], "book_count": 1, "books": [{"id": "book-1", "saved": True}]}
            await get_channel_layer().group_send(
                saved_group_name(user.id),
                {"type": "saved.updated", "saved": payload},
            )
            delivered = await owner.receive_json_from()
            self.assertEqual(delivered["saved"]["book_count"], 1)
            self.assertTrue(await stranger.receive_nothing(timeout=0.2))
        finally:
            await owner.disconnect()
            await stranger.disconnect()
            await anonymous.disconnect()

