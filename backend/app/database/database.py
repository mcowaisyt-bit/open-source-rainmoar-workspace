from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings
import os
from pathlib import Path

settings = get_settings()

# Ensure parent directory of sqlite file exists if needed
if settings.DATABASE_URL.startswith("sqlite"):
    # Extract path
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if db_path.startswith("/"):
        parent = Path(db_path).parent
        parent.mkdir(parents=True, exist_ok=True)
    else:
        os.makedirs("data", exist_ok=True)

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
