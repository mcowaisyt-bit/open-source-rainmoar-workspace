from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database.database import get_db
from app.database.models import User, UserSettings, Session as DBSession, AuditLog
from app.auth.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse, 
    OnboardingRequest, UserSettingsResponse
)
from app.auth.deps import get_current_user
from app.core.security import (
    hash_password, verify_password, create_access_token, 
    hash_token, generate_session_token
)
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.flush()
    
    # Create default settings
    user_settings = UserSettings(user_id=user.id)
    db.add(user_settings)
    
    # Create session
    raw_token = generate_session_token()
    access_token = create_access_token({"sub": str(user.id), "username": user.username})
    
    session = DBSession(
        user_id=user.id,
        token_hash=hash_token(access_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    
    # Audit
    audit = AuditLog(
        user_id=user.id,
        action="account_created",
        details={"username": user.username},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username.lower()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    access_token = create_access_token({"sub": str(user.id), "username": user.username})
    
    session = DBSession(
        user_id=user.id,
        token_hash=hash_token(access_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    
    audit = AuditLog(
        user_id=user.id,
        action="login",
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Invalidate current session by removing matching token hash if possible
    # For simplicity, we log the logout; client discards the token
    audit = AuditLog(
        user_id=current_user.id,
        action="logout",
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    db.commit()
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/onboarding", response_model=UserResponse)
async def complete_onboarding(
    req: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.display_name = req.display_name
    if req.use_case:
        current_user.use_case = req.use_case
    if req.preferred_style:
        current_user.preferred_style = req.preferred_style
    current_user.onboarding_completed = True
    
    if current_user.settings:
        current_user.settings.response_style = req.preferred_style or "professional"
    
    audit = AuditLog(
        user_id=current_user.id,
        action="onboarding_completed",
        details={"display_name": req.display_name, "use_case": req.use_case},
    )
    db.add(audit)
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)
