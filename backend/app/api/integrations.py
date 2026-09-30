from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.database.database import get_db
from app.database.models import User, OAuthAccount, AuditLog
from app.auth.deps import get_current_user
from app.core.config import get_settings
from app.core.security import encrypt_credential, decrypt_credential
from app.integrations.google_oauth import GoogleOAuthService, DEFAULT_SCOPES
from app.integrations.gmail import GmailService
from app.ai.router import get_ai_router
import logging
import secrets

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class IntegrationStatus(BaseModel):
    provider: str
    name: str
    connected: bool
    email: Optional[str] = None
    scopes: Optional[List[str]] = None
    error: Optional[str] = None


class EmailItem(BaseModel):
    id: str
    thread_id: Optional[str] = None
    from_addr: str = ""
    subject: str = ""
    snippet: str = ""
    date: str = ""
    classification: Optional[str] = None
    summary: Optional[str] = None
    needs_response: Optional[bool] = None
    why_matters: Optional[str] = None
    suggested_reply: Optional[str] = None


class DraftRequest(BaseModel):
    to: str
    subject: str
    body: str
    thread_id: Optional[str] = None
    in_reply_to: Optional[str] = None


class DraftResponse(BaseModel):
    draft_id: str
    message: str = "Draft created in Gmail. Review before sending."


class SendDraftRequest(BaseModel):
    draft_id: str
    confirm: bool = Field(..., description="Must be true to send")


async def _get_valid_gmail_token(user: User, db: Session) -> str:
    """Return a valid access token, refreshing if needed."""
    account = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == user.id,
        OAuthAccount.provider == "google",
        OAuthAccount.is_active == True,
    ).first()
    if not account or not account.encrypted_access_token:
        raise HTTPException(status_code=400, detail="Google/Gmail is not connected")

    access = decrypt_credential(account.encrypted_access_token)
    needs_refresh = (
        account.token_expires_at is not None
        and account.token_expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc)
    )

    if needs_refresh:
        if not account.encrypted_refresh_token:
            raise HTTPException(status_code=401, detail="Gmail token expired. Please reconnect Google.")
        oauth = GoogleOAuthService()
        try:
            refresh = decrypt_credential(account.encrypted_refresh_token)
            data = await oauth.refresh_access_token(refresh)
            account.encrypted_access_token = encrypt_credential(data["access_token"])
            account.token_expires_at = GoogleOAuthService.token_expires_at(data)
            if data.get("refresh_token"):
                account.encrypted_refresh_token = encrypt_credential(data["refresh_token"])
            db.commit()
            access = data["access_token"]
        except Exception as e:
            logger.warning(f"Token refresh failed for user {user.id}: {e}")
            raise HTTPException(status_code=401, detail="Gmail token refresh failed. Please reconnect Google.")

    return access


@router.get("", response_model=List[IntegrationStatus])
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    accounts = {
        a.provider: a
        for a in db.query(OAuthAccount).filter(
            OAuthAccount.user_id == current_user.id,
            OAuthAccount.is_active == True,
        ).all()
    }
    google = accounts.get("google")
    result = [
        IntegrationStatus(
            provider="google",
            name="Google / Gmail",
            connected=google is not None,
            email=google.email if google else None,
            scopes=google.scopes if google else None,
        ),
        IntegrationStatus(
            provider="outlook",
            name="Microsoft Outlook",
            connected=False,
            email=None,
        ),
    ]
    return result


@router.get("/google/auth-url")
async def google_auth_url(
    current_user: User = Depends(get_current_user),
):
    oauth = GoogleOAuthService()
    if not oauth.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the server environment.",
        )
    # state = user_id:nonce for CSRF protection
    state = f"{current_user.id}:{secrets.token_urlsafe(16)}"
    url = oauth.get_auth_url(state=state)
    return {"auth_url": url, "state": state}


@router.get("/google/callback")
async def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    OAuth callback from Google.
    Exchanges code for tokens and stores them encrypted.
    Returns a simple HTML page the desktop/webview can close.
    """
    if error:
        return HTMLResponse(
            f"""<!DOCTYPE html><html><body style="font-family:system-ui;background:#111;color:#eee;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
            <div style="text-align:center"><h2>Google connection cancelled</h2><p style="color:#888">{error}</p>
            <p>You can close this window.</p></div>
            <script>setTimeout(()=>window.close(),2000)</script></body></html>""",
            status_code=400,
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    try:
        user_id_str = state.split(":")[0]
        user_id = int(user_id_str)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    oauth = GoogleOAuthService()
    try:
        token_data = await oauth.exchange_code(code)
    except Exception as e:
        logger.exception("OAuth token exchange failed")
        return HTMLResponse(
            f"""<!DOCTYPE html><html><body style="font-family:system-ui;background:#111;color:#eee;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
            <div style="text-align:center"><h2>Connection failed</h2><p style="color:#f88">Could not complete Google sign-in.</p>
            <p style="color:#888">You can close this window and try again.</p></div></body></html>""",
            status_code=400,
        )

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received")

    email = await oauth.get_user_email(access_token)
    expires_at = GoogleOAuthService.token_expires_at(token_data)
    scopes = token_data.get("scope", " ".join(DEFAULT_SCOPES)).split()

    existing = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == user.id,
        OAuthAccount.provider == "google",
    ).first()

    if existing:
        existing.encrypted_access_token = encrypt_credential(access_token)
        if refresh_token:
            existing.encrypted_refresh_token = encrypt_credential(refresh_token)
        existing.token_expires_at = expires_at
        existing.email = email
        existing.scopes = scopes
        existing.is_active = True
        existing.provider_user_id = email
    else:
        account = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=email,
            email=email,
            encrypted_access_token=encrypt_credential(access_token),
            encrypted_refresh_token=encrypt_credential(refresh_token) if refresh_token else None,
            token_expires_at=expires_at,
            scopes=scopes,
            is_active=True,
        )
        db.add(account)

    audit = AuditLog(
        user_id=user.id,
        action="google_connected",
        resource_type="integration",
        details={"email": email, "scopes": scopes},
    )
    db.add(audit)
    db.commit()

    return HTMLResponse(
        f"""<!DOCTYPE html><html><body style="font-family:system-ui;background:#0a0a0b;color:#eee;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
        <div style="text-align:center">
          <div style="font-size:48px;margin-bottom:12px">✓</div>
          <h2 style="margin:0 0 8px">Google Account Connected</h2>
          <p style="color:#a1a1aa">{email or 'Gmail linked successfully'}</p>
          <p style="color:#52525b;font-size:13px">You can close this window and return to AI Command Center.</p>
        </div>
        <script>setTimeout(()=>window.close(),2500)</script>
        </body></html>"""
    )


@router.post("/google/disconnect")
async def disconnect_google(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == current_user.id,
        OAuthAccount.provider == "google",
    ).first()
    if account:
        # Best-effort revoke
        try:
            if account.encrypted_access_token:
                oauth = GoogleOAuthService()
                await oauth.revoke_token(decrypt_credential(account.encrypted_access_token))
        except Exception:
            pass
        db.delete(account)
        audit = AuditLog(
            user_id=current_user.id,
            action="google_disconnected",
            resource_type="integration",
        )
        db.add(audit)
        db.commit()
    return {"message": "Google account disconnected"}


# ─── Gmail features ───────────────────────────────────────────

@router.get("/gmail/inbox", response_model=List[EmailItem])
async def gmail_inbox(
    query: str = "in:inbox newer_than:7d",
    max_results: int = Query(default=15, le=50),
    classify: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent emails. Optionally run AI classification."""
    token = await _get_valid_gmail_token(current_user, db)
    gmail = GmailService(token)
    try:
        messages = await gmail.get_messages_with_meta(query=query, max_results=max_results)
    except RuntimeError as e:
        if str(e) == "GMAIL_TOKEN_EXPIRED":
            raise HTTPException(status_code=401, detail="Gmail token expired. Please reconnect Google.")
        raise HTTPException(status_code=502, detail=str(e))

    items = [
        EmailItem(
            id=m["id"],
            thread_id=m.get("thread_id"),
            from_addr=m.get("from", ""),
            subject=m.get("subject", ""),
            snippet=m.get("snippet", ""),
            date=m.get("date", ""),
        )
        for m in messages
    ]

    if classify and items:
        try:
            router_ai = get_ai_router()
            email_text = "\n\n".join(
                f"ID: {it.id}\nFrom: {it.from_addr}\nSubject: {it.subject}\nSnippet: {it.snippet}"
                for it in items[:12]
            )
            result = await router_ai.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You classify emails. For each email respond with lines:\n"
                            "ID: <id>\nCLASS: important|low|notification|needs_response|other\n"
                            "SUMMARY: one sentence\nNEEDS_RESPONSE: yes|no\nWHY: brief reason\n---"
                        ),
                    },
                    {"role": "user", "content": email_text},
                ],
                user=current_user,
                db=db,
                model="auto",
                task_hint="classification",
            )
            # Parse AI response into items
            blocks = (result.get("content") or "").split("---")
            by_id = {it.id: it for it in items}
            for block in blocks:
                lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
                eid = None
                data: Dict[str, str] = {}
                for line in lines:
                    if line.upper().startswith("ID:"):
                        eid = line.split(":", 1)[1].strip()
                    elif ":" in line:
                        k, v = line.split(":", 1)
                        data[k.strip().upper()] = v.strip()
                if eid and eid in by_id:
                    it = by_id[eid]
                    it.classification = data.get("CLASS", "").lower() or None
                    it.summary = data.get("SUMMARY")
                    it.needs_response = data.get("NEEDS_RESPONSE", "").lower().startswith("y")
                    it.why_matters = data.get("WHY")
        except Exception as e:
            logger.warning(f"Email classification failed: {e}")

    return items


@router.get("/gmail/messages/{message_id}")
async def gmail_message_detail(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token = await _get_valid_gmail_token(current_user, db)
    gmail = GmailService(token)
    try:
        meta_list = await gmail.get_messages_with_meta(query=f"rfc822msgid:{message_id}", max_results=1)
        body = await gmail.get_message_body(message_id)
        full = await gmail.get_message(message_id, format="metadata")
        headers = {
            h["name"].lower(): h["value"]
            for h in full.get("payload", {}).get("headers", [])
        }
        return {
            "id": message_id,
            "thread_id": full.get("threadId"),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "snippet": full.get("snippet", ""),
            "body": body[:15000],
        }
    except RuntimeError as e:
        if str(e) == "GMAIL_TOKEN_EXPIRED":
            raise HTTPException(status_code=401, detail="Gmail token expired. Please reconnect.")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/gmail/analyze/{message_id}")
async def gmail_analyze_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI summary + suggested reply for one email."""
    token = await _get_valid_gmail_token(current_user, db)
    gmail = GmailService(token)
    try:
        body = await gmail.get_message_body(message_id)
        full = await gmail.get_message(message_id, format="metadata")
        headers = {
            h["name"].lower(): h["value"]
            for h in full.get("payload", {}).get("headers", [])
        }
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    from_addr = headers.get("from", "")
    subject = headers.get("subject", "")
    snippet = full.get("snippet", "")

    router_ai = get_ai_router()
    try:
        result = await router_ai.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyze this email. Respond exactly with:\n"
                        "CLASS: important|low|notification|needs_response|other\n"
                        "SUMMARY: 2-3 sentence summary\n"
                        "WHY: why it matters or not\n"
                        "NEEDS_RESPONSE: yes|no\n"
                        "SUGGESTED_REPLY: a polite professional reply draft (or NONE)"
                    ),
                },
                {
                    "role": "user",
                    "content": f"From: {from_addr}\nSubject: {subject}\n\n{body[:6000] or snippet}",
                },
            ],
            user=current_user,
            db=db,
            model="auto",
            task_hint="writing",
        )
        text = result.get("content", "")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {e}")

    parsed: Dict[str, str] = {}
    for line in text.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            parsed[k.strip().upper()] = v.strip()

    audit = AuditLog(
        user_id=current_user.id,
        action="email_analyzed",
        resource_type="gmail",
        details={"message_id": message_id, "subject": subject[:100]},
    )
    db.add(audit)
    db.commit()

    return {
        "id": message_id,
        "from": from_addr,
        "subject": subject,
        "classification": parsed.get("CLASS", "").lower(),
        "summary": parsed.get("SUMMARY", ""),
        "why_matters": parsed.get("WHY", ""),
        "needs_response": parsed.get("NEEDS_RESPONSE", "").lower().startswith("y"),
        "suggested_reply": parsed.get("SUGGESTED_REPLY", ""),
        "provider_used": result.get("provider"),
        "model_used": result.get("model"),
    }


@router.post("/gmail/drafts", response_model=DraftResponse)
async def create_gmail_draft(
    req: DraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Gmail draft. Does NOT send."""
    token = await _get_valid_gmail_token(current_user, db)
    gmail = GmailService(token)
    try:
        draft = await gmail.create_draft(
            to=req.to,
            subject=req.subject,
            body=req.body,
            thread_id=req.thread_id,
            in_reply_to=req.in_reply_to,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    draft_id = draft.get("id", "")
    audit = AuditLog(
        user_id=current_user.id,
        action="email_draft_created",
        resource_type="gmail",
        details={"draft_id": draft_id, "to": req.to, "subject": req.subject[:100]},
    )
    db.add(audit)
    db.commit()

    return DraftResponse(draft_id=draft_id)


@router.post("/gmail/drafts/send")
async def send_gmail_draft(
    req: SendDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a draft. Requires confirm=true. Never silent."""
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Sending requires explicit confirm=true")

    token = await _get_valid_gmail_token(current_user, db)
    gmail = GmailService(token)
    try:
        result = await gmail.send_draft(req.draft_id)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    audit = AuditLog(
        user_id=current_user.id,
        action="email_sent",
        resource_type="gmail",
        details={"draft_id": req.draft_id},
    )
    db.add(audit)
    db.commit()

    return {"message": "Email sent", "result": {"id": result.get("id")}}
