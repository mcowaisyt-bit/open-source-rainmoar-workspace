"""
Google OAuth 2.0 — authorization URL, code exchange, token refresh.
Secrets stay server-side. Never exposed to the client.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import httpx
from app.core.config import get_settings

settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# Gmail scopes — readonly + compose (drafts). Send requires explicit later permission.
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


class GoogleOAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_auth_url(self, state: str, scopes: Optional[List[str]] = None) -> str:
        if not self.is_configured():
            raise ValueError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        scope_str = " ".join(scopes or DEFAULT_SCOPES)
        from urllib.parse import urlencode
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope_str,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access + refresh tokens."""
        if not self.is_configured():
            raise ValueError("Google OAuth is not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                detail = resp.text
                raise RuntimeError(f"Token exchange failed: {detail}")
            return resp.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token."""
        if not self.is_configured():
            raise ValueError("Google OAuth is not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Token refresh failed: {resp.text}")
            return resp.json()

    async def get_user_email(self, access_token: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("email")

    async def revoke_token(self, token: str) -> bool:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GOOGLE_REVOKE_URL,
                params={"token": token},
            )
            return resp.status_code == 200

    @staticmethod
    def token_expires_at(token_response: Dict[str, Any]) -> datetime:
        expires_in = int(token_response.get("expires_in", 3600))
        return datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
