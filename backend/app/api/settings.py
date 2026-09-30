from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import User, UserSettings
from app.auth.deps import get_current_user
from app.auth.schemas import UserSettingsResponse, UserSettingsUpdate

router = APIRouter()


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return UserSettingsResponse.model_validate(settings)
    return UserSettingsResponse.model_validate(current_user.settings)


@router.patch("", response_model=UserSettingsResponse)
async def update_settings(
    req: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = current_user.settings
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.flush()
    
    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    return UserSettingsResponse.model_validate(settings)
