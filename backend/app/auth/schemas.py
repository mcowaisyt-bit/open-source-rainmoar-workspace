from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, underscores, and hyphens")
        return v.lower()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    preferred_style: Optional[str] = None
    use_case: Optional[str] = None
    onboarding_completed: bool = False
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OnboardingRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=128)
    use_case: Optional[str] = None
    preferred_style: Optional[str] = "professional"


class UserSettingsResponse(BaseModel):
    default_model: str
    auto_routing: bool
    auto_fallback: bool
    response_style: str
    notifications_enabled: bool
    notification_sound: bool
    theme: str
    notify_agent_completed: bool = True
    notify_agent_failed: bool = True
    notify_important_only: bool = False
    notify_email_needs_response: bool = True
    native_notifications: bool = True
    
    class Config:
        from_attributes = True


class UserSettingsUpdate(BaseModel):
    default_model: Optional[str] = None
    auto_routing: Optional[bool] = None
    auto_fallback: Optional[bool] = None
    response_style: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    notification_sound: Optional[bool] = None
    theme: Optional[str] = None
    notify_agent_completed: Optional[bool] = None
    notify_agent_failed: Optional[bool] = None
    notify_important_only: Optional[bool] = None
    notify_email_needs_response: Optional[bool] = None
    native_notifications: Optional[bool] = None


TokenResponse.model_rebuild()
