"""Admin / ops endpoints — backup, health details. No secrets exposed."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pathlib import Path
import shutil
import os
from app.database.database import get_db
from app.database.models import User, AuditLog
from app.auth.deps import get_current_user
from app.core.config import get_settings
from app.agents.scheduler import scheduler_status

router = APIRouter()
settings = get_settings()


@router.post("/backup")
async def create_backup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a timestamped SQLite backup (if using SQLite).
    Does not overwrite the live database.
    """
    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite"):
        return {
            "message": "Automatic file backup is for SQLite. Use pg_dump for PostgreSQL.",
            "database": "postgresql",
            "guidance": "pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql",
        }

    # Extract path
    path = db_url.replace("sqlite:///", "")
    if path.startswith("/") and path.startswith("//"):
        path = path[1:]  # sqlite:////tmp/... -> /tmp/...
    src = Path(path)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    backup_dir = src.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_dir / f"rainmoal-{stamp}.db"
    shutil.copy2(src, dest)

    # Retention: keep last 14 backups
    backups = sorted(backup_dir.glob("rainmoal-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[14:]:
        try:
            old.unlink()
        except OSError:
            pass

    audit = AuditLog(
        user_id=current_user.id,
        action="database_backup",
        resource_type="system",
        details={"file": dest.name, "size": dest.stat().st_size},
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Backup created",
        "file": dest.name,
        "path": str(dest),
        "size_bytes": dest.stat().st_size,
        "retained": min(len(backups), 14),
    }


@router.get("/system")
async def system_info(current_user: User = Depends(get_current_user)):
    return {
        "name": "RainMoal Workspace",
        "version": "0.5.0",
        "env": settings.APP_ENV,
        "scheduler": scheduler_status(),
        "database_type": "sqlite" if "sqlite" in settings.DATABASE_URL else "other",
    }
