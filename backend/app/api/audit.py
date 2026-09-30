from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.database.database import get_db
from app.database.models import User, AuditLog
from app.auth.deps import get_current_user

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: int
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[dict]
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [AuditLogResponse.model_validate(l) for l in logs]
