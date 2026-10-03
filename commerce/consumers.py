import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from catalog.realtime import saved_group_name, saved_snapshot
from commerce.present import cart_payload
from commerce.realtime import cart_group_name
from commerce.services import get_cart


class CartConsumer(AsyncWebsocketConsumer):
    group_name = None

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return
        self.group_name = cart_group_name(user.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        payload = await database_sync_to_async(_snapshot)(user)
        await self.send(text_data=json.dumps({"type": "cart.updated", "cart": payload}))

    async def disconnect(self, code):
        if self.group_name and self.channel_layer is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def cart_updated(self, event):
        await self.send(text_data=json.dumps({"type": "cart.updated", "cart": event["cart"]}))


def _snapshot(user):
    return cart_payload(get_cart(user))


class SavedConsumer(AsyncWebsocketConsumer):
    group_name = None

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return
        self.group_name = saved_group_name(user.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        payload = await database_sync_to_async(saved_snapshot)(user)
        await self.send(text_data=json.dumps({"type": "saved.updated", "saved": payload}))

    async def disconnect(self, code):
        if self.group_name and self.channel_layer is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def saved_updated(self, event):
        await self.send(text_data=json.dumps({"type": "saved.updated", "saved": event["saved"]}))
