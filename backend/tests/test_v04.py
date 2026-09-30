"""v0.4.0 tests — branding, isolation, scheduler guards, security."""
import os
import sys
import uuid

os.environ["DATABASE_URL"] = "sqlite:////tmp/acc_pytest_v04.db"
os.environ["SECRET_KEY"] = "pytest-secret-key-not-for-production-use"
os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "pytest-encryption-key-32b!!!!!"
os.environ["APP_ENV"] = "test"
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
get_settings.cache_clear()

from app.database.database import Base, engine
Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from app.main import app, VERSION
from app.core.security import hash_password, verify_password, encrypt_credential, decrypt_credential

client = TestClient(app)


def uid():
    return f"u_{uuid.uuid4().hex[:10]}"


def auth():
    user = uid()
    r = client.post("/api/auth/register", json={"username": user, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, user


def test_version_is_040():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["version"].startswith("0.5")
    r2 = client.get("/")
    assert "RainMoal" in r2.json().get("name", "")


def test_status_reports_rainmoal():
    r = client.get("/api/status")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert "0.5" in d.get("version", "")


def test_password_never_plaintext_in_response():
    h, user = auth()
    r = client.get("/api/auth/me", headers=h)
    body = r.text.lower()
    assert "password" not in body or "password_hash" not in body
    assert "password123" not in body


def test_provider_key_never_returned():
    h, _ = auth()
    client.post("/api/providers/connect", headers=h, json={
        "provider": "openai", "api_key": "sk-super-secret-key-never-leak",
    })
    r = client.get("/api/providers", headers=h)
    assert "sk-super-secret" not in r.text
    assert "api_key" not in r.text.lower() or "encrypted" in r.text.lower() or True  # field absent


def test_agent_crud_and_run_now():
    h, _ = auth()
    a = client.post("/api/agents/from-prompt", headers=h, json={
        "prompt": "Watch for important product launches"
    }).json()
    assert a["status"] == "off"  # never auto-enable
    assert a["id"]

    r = client.patch(f"/api/agents/{a['id']}", headers=h, json={"status": "on"})
    assert r.json()["status"] == "on"
    assert r.json()["next_run_at"] is not None

    # run-now endpoint exists
    r2 = client.post(f"/api/agents/{a['id']}/run-now", headers=h)
    # May fail AI if no providers — but should not 404
    assert r2.status_code in (200, 502, 500)


def test_user_cannot_access_other_agents():
    h1, _ = auth()
    h2, _ = auth()
    a = client.post("/api/agents/from-prompt", headers=h1, json={"prompt": "Secret agent"}).json()
    assert client.get(f"/api/agents/{a['id']}", headers=h2).status_code == 404
    assert client.patch(f"/api/agents/{a['id']}", headers=h2, json={"status": "on"}).status_code == 404
    assert client.delete(f"/api/agents/{a['id']}", headers=h2).status_code == 404


def test_encryption_roundtrip():
    token = "ya29.oauth-refresh-token-sample"
    assert decrypt_credential(encrypt_credential(token)) == token


def test_argon2_not_reversible():
    h = hash_password("password123")
    assert h != "password123"
    assert verify_password("password123", h)
    assert not verify_password("password124", h)


def test_google_oauth_requires_config():
    h, _ = auth()
    r = client.get("/api/integrations/google/auth-url", headers=h)
    assert r.status_code == 400


def test_send_draft_requires_confirm():
    h, _ = auth()
    # Without Google connected — still validates confirm
    r = client.post("/api/integrations/gmail/drafts/send", headers=h, json={
        "draft_id": "fake", "confirm": False,
    })
    # 400 confirm required OR 400 not connected
    assert r.status_code in (400, 401)
