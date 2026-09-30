"""OAuth helpers, provider isolation, agent scheduling tests."""
import os
import sys
import uuid

os.environ["DATABASE_URL"] = "sqlite:////tmp/acc_pytest2.db"
os.environ["SECRET_KEY"] = "pytest-secret-key-not-for-production-use"
os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "pytest-encryption-key-32b!!!!!"
os.environ["APP_ENV"] = "test"
# Intentionally unset Google so we test "not configured" path
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
get_settings.cache_clear()

from app.database.database import Base, engine
Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from app.main import app
from app.integrations.google_oauth import GoogleOAuthService
from app.core.security import encrypt_credential, decrypt_credential

client = TestClient(app)


def uid():
    return f"u_{uuid.uuid4().hex[:10]}"


def auth_headers(username=None):
    user = username or uid()
    r = client.post("/api/auth/register", json={"username": user, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, user


def test_google_not_configured():
    h, _ = auth_headers()
    r = client.get("/api/integrations/google/auth-url", headers=h)
    assert r.status_code == 400
    assert "not configured" in r.json()["detail"].lower() or "GOOGLE" in r.json()["detail"]


def test_oauth_service_auth_url_requires_config():
    svc = GoogleOAuthService()
    assert not svc.is_configured()
    try:
        svc.get_auth_url("1:test")
        assert False, "should raise"
    except ValueError:
        pass


def test_provider_connect_and_list():
    h, _ = auth_headers()
    # Connect with a fake key (health check may fail — still stores)
    r = client.post("/api/providers/connect", headers=h, json={
        "provider": "openai",
        "api_key": "sk-test-fake-key-for-unit-tests-only",
    })
    assert r.status_code == 200
    r2 = client.get("/api/providers", headers=h)
    assert r2.status_code == 200
    openai = next(p for p in r2.json() if p["provider"] == "openai")
    assert openai["connected"] is True


def test_provider_isolation():
    h1, _ = auth_headers()
    h2, _ = auth_headers()
    client.post("/api/providers/connect", headers=h1, json={
        "provider": "gemini", "api_key": "fake-gemini-key-1234567890",
    })
    p1 = client.get("/api/providers", headers=h1).json()
    p2 = client.get("/api/providers", headers=h2).json()
    assert next(x for x in p1 if x["provider"] == "gemini")["connected"] is True
    assert next(x for x in p2 if x["provider"] == "gemini")["connected"] is False


def test_agent_run_history_fields():
    h, _ = auth_headers()
    a = client.post("/api/agents/from-prompt", headers=h, json={"prompt": "Watch tech news"}).json()
    client.patch(f"/api/agents/{a['id']}", headers=h, json={"status": "on"})
    runs = client.get(f"/api/agents/{a['id']}/runs", headers=h)
    assert runs.status_code == 200
    assert isinstance(runs.json(), list)


def test_encrypt_roundtrip():
    s = "secret-token-value-xyz"
    assert decrypt_credential(encrypt_credential(s)) == s


def test_status_version():
    r = client.get("/api/status")
    assert r.status_code == 200
    assert "0.3" in r.json().get("version", "") or r.json().get("status") == "ok"
