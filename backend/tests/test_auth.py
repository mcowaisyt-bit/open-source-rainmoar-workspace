"""Auth and isolation tests — each test is self-contained."""
import os
import sys
import uuid

os.environ["DATABASE_URL"] = "sqlite:////tmp/acc_pytest.db"
os.environ["SECRET_KEY"] = "pytest-secret-key-not-for-production-use"
os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "pytest-encryption-key-32b!!!!!"
os.environ["APP_ENV"] = "test"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
get_settings.cache_clear()

from app.database.database import Base, engine
from app.core.security import hash_password, verify_password, encrypt_credential, decrypt_credential

Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def unique_user():
    return f"u_{uuid.uuid4().hex[:10]}"


def test_password_hashing():
    h = hash_password("MySecurePass123")
    assert h != "MySecurePass123"
    assert verify_password("MySecurePass123", h)
    assert not verify_password("wrong", h)


def test_credential_encryption():
    plain = "sk-test-key-abc123xyz"
    enc = encrypt_credential(plain)
    assert enc != plain
    assert decrypt_credential(enc) == plain


def test_register_login_me():
    user = unique_user()
    r = client.post("/api/auth/register", json={"username": user, "password": "password123"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["user"]["username"] == user

    r2 = client.post("/api/auth/login", json={"username": user, "password": "password123"})
    assert r2.status_code == 200
    token = r2.json()["access_token"]

    r3 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert r3.json()["username"] == user


def test_invalid_login():
    user = unique_user()
    client.post("/api/auth/register", json={"username": user, "password": "password123"})
    r = client.post("/api/auth/login", json={"username": user, "password": "wrongpassword"})
    assert r.status_code == 401


def test_duplicate_register():
    user = unique_user()
    client.post("/api/auth/register", json={"username": user, "password": "password123"})
    r = client.post("/api/auth/register", json={"username": user, "password": "password123"})
    assert r.status_code == 400


def test_agent_isolation():
    u1, u2 = unique_user(), unique_user()
    t1 = client.post("/api/auth/register", json={"username": u1, "password": "password123"}).json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}
    a = client.post("/api/agents/from-prompt", headers=h1, json={"prompt": "Watch Apple news"}).json()
    assert a.get("name"), a
    agent_id = a["id"]

    t2 = client.post("/api/auth/register", json={"username": u2, "password": "password123"}).json()["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}

    assert client.get(f"/api/agents/{agent_id}", headers=h2).status_code == 404
    assert client.get("/api/agents", headers=h2).json() == []


def test_agent_enable_schedule():
    user = unique_user()
    t = client.post("/api/auth/register", json={"username": user, "password": "password123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {t}"}
    a = client.post("/api/agents/from-prompt", headers=h, json={"prompt": "Monitor tech news"}).json()
    r = client.patch(f"/api/agents/{a['id']}", headers=h, json={"status": "on"})
    assert r.status_code == 200
    assert r.json()["status"] == "on"
    assert r.json()["next_run_at"] is not None


def test_status_endpoint():
    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
