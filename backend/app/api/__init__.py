from fastapi import APIRouter
from .auth import router as auth_router
from .agents import router as agents_router
from .chat import router as chat_router
from .providers import router as providers_router
from .integrations import router as integrations_router
from .notifications import router as notifications_router
from .audit import router as audit_router
from .settings import router as settings_router
from .admin import router as admin_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(providers_router, prefix="/providers", tags=["providers"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
