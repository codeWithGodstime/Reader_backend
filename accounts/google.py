from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from common.exceptions import APIError


def verify_google_id_token(raw_token):
    client_ids = settings.GOOGLE_OAUTH_CLIENT_IDS
    if not client_ids:
        raise APIError(
            "Google sign-in is not configured.",
            code="authentication_failed",
            status_code=401,
        )
    claims = None
    for client_id in client_ids:
        try:
            claims = id_token.verify_oauth2_token(
                raw_token,
                google_requests.Request(),
                audience=client_id,
            )
            break
        except Exception:
            claims = None
    if not claims:
        raise APIError(
            "Google ID token is invalid.",
            code="authentication_failed",
            status_code=401,
        )
    verified = claims.get("email_verified")
    if verified is not True and verified != "true":
        raise APIError(
            "Google email is not verified.",
            code="authentication_failed",
            status_code=401,
        )
    email = (claims.get("email") or "").strip().lower()
    subject = (claims.get("sub") or "").strip()
    if not email or not subject:
        raise APIError(
            "Google ID token is invalid.",
            code="authentication_failed",
            status_code=401,
        )
    name = (claims.get("name") or "").strip() or email.split("@")[0]
    return {"email": email, "sub": subject, "name": name[:120]}
