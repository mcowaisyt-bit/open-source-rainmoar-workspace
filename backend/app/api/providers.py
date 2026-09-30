from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from app.database.database import get_db
from app.database.models import User, AICredential, AuditLog
from app.auth.deps import get_current_user
from app.core.security import encrypt_credential, decrypt_credential
from app.ai.providers import OpenAIProvider, XAIProvider, GeminiProvider

router = APIRouter()

PROVIDER_INFO = {
    "openai": {"name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]},
    "xai": {"name": "xAI / Grok", "models": ["grok-2", "grok-2-mini"]},
    "gemini": {"name": "Google Gemini", "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]},
}


class ConnectProviderRequest(BaseModel):
    provider: str = Field(..., pattern="^(openai|xai|gemini)$")
    api_key: str = Field(..., min_length=10)


class ProviderStatus(BaseModel):
    provider: str
    name: str
    connected: bool
    status: str  # available, unavailable, rate_limited, not_connected, error
    models: List[str]
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None


class TestResult(BaseModel):
    provider: str
    ok: bool
    status: str
    message: str
    model: Optional[str] = None


@router.get("", response_model=List[ProviderStatus])
async def list_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    creds = {
        c.provider: c
        for c in db.query(AICredential).filter(AICredential.user_id == current_user.id).all()
    }
    result = []
    for key, info in PROVIDER_INFO.items():
        if key in creds and creds[key].is_active:
            result.append(ProviderStatus(
                provider=key,
                name=info["name"],
                connected=True,
                status=creds[key].status or "available",
                models=info["models"],
                last_used=creds[key].last_used,
            ))
        else:
            result.append(ProviderStatus(
                provider=key,
                name=info["name"],
                connected=False,
                status="not_connected",
                models=info["models"],
            ))
    return result


@router.post("/connect")
async def connect_provider(
    req: ConnectProviderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    providers = {
        "openai": OpenAIProvider(),
        "xai": XAIProvider(),
        "gemini": GeminiProvider(),
    }
    provider = providers[req.provider]
    ok = await provider.health_check(api_key=req.api_key)
    status = "available" if ok else "error"

    existing = db.query(AICredential).filter(
        AICredential.user_id == current_user.id,
        AICredential.provider == req.provider,
    ).first()

    encrypted = encrypt_credential(req.api_key)
    if existing:
        existing.encrypted_api_key = encrypted
        existing.is_active = True
        existing.status = status
        existing.updated_at = datetime.now(timezone.utc)
    else:
        cred = AICredential(
            user_id=current_user.id,
            provider=req.provider,
            encrypted_api_key=encrypted,
            is_active=True,
            status=status,
        )
        db.add(cred)

    audit = AuditLog(
        user_id=current_user.id,
        action="api_provider_connected",
        resource_type="provider",
        details={"provider": req.provider, "test_ok": ok},
    )
    db.add(audit)
    db.commit()

    return {
        "message": f"{PROVIDER_INFO[req.provider]['name']} connected",
        "provider": req.provider,
        "status": status,
        "test_ok": ok,
    }


@router.post("/test/{provider}", response_model=TestResult)
async def test_provider(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if provider not in PROVIDER_INFO:
        raise HTTPException(status_code=400, detail="Unknown provider")

    cred = db.query(AICredential).filter(
        AICredential.user_id == current_user.id,
        AICredential.provider == provider,
        AICredential.is_active == True,
    ).first()
    if not cred:
        return TestResult(
            provider=provider, ok=False, status="not_connected",
            message="Provider not connected",
        )

    providers = {
        "openai": OpenAIProvider(),
        "xai": XAIProvider(),
        "gemini": GeminiProvider(),
    }
    try:
        key = decrypt_credential(cred.encrypted_api_key)
        ok = await providers[provider].health_check(api_key=key)
        if ok:
            # Light chat probe
            try:
                result = await providers[provider].chat(
                    messages=[{"role": "user", "content": "Reply with exactly: OK"}],
                    model=None,
                    max_tokens=10,
                    api_key=key,
                )
                cred.status = "available"
                cred.last_used = datetime.now(timezone.utc)
                db.commit()
                return TestResult(
                    provider=provider, ok=True, status="available",
                    message="Connection successful",
                    model=result.get("model"),
                )
            except RuntimeError as e:
                err = str(e)
                if err == "RATE_LIMIT":
                    cred.status = "rate_limited"
                    db.commit()
                    return TestResult(provider=provider, ok=False, status="rate_limited", message="Rate limited")
                cred.status = "unavailable"
                db.commit()
                return TestResult(provider=provider, ok=False, status="unavailable", message=err)
        else:
            cred.status = "error"
            db.commit()
            return TestResult(provider=provider, ok=False, status="error", message="Health check failed")
    except Exception as e:
        cred.status = "error"
        db.commit()
        return TestResult(provider=provider, ok=False, status="error", message=str(e)[:200])


@router.post("/disconnect/{provider}")
async def disconnect_provider(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if provider not in PROVIDER_INFO:
        raise HTTPException(status_code=400, detail="Unknown provider")

    cred = db.query(AICredential).filter(
        AICredential.user_id == current_user.id,
        AICredential.provider == provider,
    ).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Provider not connected")

    db.delete(cred)
    audit = AuditLog(
        user_id=current_user.id,
        action="api_provider_disconnected",
        resource_type="provider",
        details={"provider": provider},
    )
    db.add(audit)
    db.commit()
    return {"message": f"{PROVIDER_INFO[provider]['name']} disconnected"}
