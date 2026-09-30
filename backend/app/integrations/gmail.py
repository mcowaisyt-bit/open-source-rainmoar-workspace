"""
Gmail API client — list, read, classify helpers, create drafts.
Uses stored OAuth tokens. Never sends email without explicit user approval path.
"""
from typing import List, Dict, Any, Optional
import base64
import httpx
from email.mime.text import MIMEText


GMAIL_API = "https://gmail.googleapis.com/gmail/v1"


class GmailService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def list_messages(
        self,
        query: str = "in:inbox",
        max_results: int = 20,
        label_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"q": query, "maxResults": max_results}
        if label_ids:
            params["labelIds"] = label_ids

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{GMAIL_API}/users/me/messages",
                headers=self.headers,
                params=params,
            )
            if resp.status_code == 401:
                raise RuntimeError("GMAIL_TOKEN_EXPIRED")
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail list failed: {resp.status_code} {resp.text[:200]}")
            data = resp.json()
            return data.get("messages", [])

    async def get_message(self, message_id: str, format: str = "full") -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{GMAIL_API}/users/me/messages/{message_id}",
                headers=self.headers,
                params={"format": format},
            )
            if resp.status_code == 401:
                raise RuntimeError("GMAIL_TOKEN_EXPIRED")
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail get failed: {resp.status_code}")
            return resp.json()

    async def get_messages_with_meta(
        self, query: str = "in:inbox newer_than:7d", max_results: int = 15
    ) -> List[Dict[str, Any]]:
        """Fetch message list + metadata (headers, snippet)."""
        msgs = await self.list_messages(query=query, max_results=max_results)
        results = []
        for m in msgs:
            full = await self.get_message(m["id"], format="metadata")
            headers = {
                h["name"].lower(): h["value"]
                for h in full.get("payload", {}).get("headers", [])
            }
            results.append({
                "id": full["id"],
                "thread_id": full.get("threadId"),
                "snippet": full.get("snippet", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", "(no subject)"),
                "date": headers.get("date", ""),
                "label_ids": full.get("labelIds", []),
            })
        return results

    async def get_message_body(self, message_id: str) -> str:
        full = await self.get_message(message_id, format="full")
        return self._extract_body(full.get("payload", {}))

    def _extract_body(self, payload: Dict) -> str:
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        for part in payload.get("parts", []) or []:
            mime = part.get("mimeType", "")
            if mime == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            if mime.startswith("multipart/"):
                nested = self._extract_body(part)
                if nested:
                    return nested
        for part in payload.get("parts", []) or []:
            if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        return ""

    async def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Gmail draft. Does NOT send."""
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = in_reply_to

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        payload: Dict[str, Any] = {"message": {"raw": raw}}
        if thread_id:
            payload["message"]["threadId"] = thread_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{GMAIL_API}/users/me/drafts",
                headers=self.headers,
                json=payload,
            )
            if resp.status_code == 401:
                raise RuntimeError("GMAIL_TOKEN_EXPIRED")
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Draft create failed: {resp.status_code} {resp.text[:300]}")
            return resp.json()

    async def send_draft(self, draft_id: str) -> Dict[str, Any]:
        """Send an existing draft. Requires explicit user approval in the product flow."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{GMAIL_API}/users/me/drafts/{draft_id}/send",
                headers=self.headers,
            )
            if resp.status_code == 401:
                raise RuntimeError("GMAIL_TOKEN_EXPIRED")
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Send draft failed: {resp.status_code} {resp.text[:300]}")
            return resp.json()
