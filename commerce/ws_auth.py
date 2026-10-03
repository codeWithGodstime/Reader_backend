from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class QueryJwtAuthMiddleware(BaseMiddleware):
    """Authenticate a websocket with the same access JWT the HTTP API uses.

    Native clients often cannot set handshake headers, so the token may be
    `?token=`. An `Authorization: Bearer` header is accepted too.
    """

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["user"] = await _user_for_token(_token_from_scope(scope))
        return await super().__call__(scope, receive, send)


def _token_from_scope(scope):
    query = parse_qs(scope.get("query_string", b"").decode("latin1"))
    values = query.get("token") or []
    if values and values[0]:
        return values[0]
    headers = {name.lower(): value for name, value in scope.get("headers", [])}
    raw = headers.get(b"authorization", b"").decode("latin1").strip()
    prefix = "bearer "
    if raw.lower().startswith(prefix):
        token = raw[len(prefix) :].strip()
        return token or None
    return None


@database_sync_to_async
def _user_for_token(raw_token):
    if not raw_token:
        return AnonymousUser()
    auth = JWTAuthentication()
    try:
        validated = auth.get_validated_token(raw_token.encode("utf-8"))
        return auth.get_user(validated)
    except (InvalidToken, TokenError, AuthenticationFailed):
        return AnonymousUser()
