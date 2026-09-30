"""v0.5.0 — scheduler recovery, backup, settings prefs, security."""
import os
import sys
import uuid

os.environ["DATABASE_URL"] = "sqlite:////tmp/acc_pytest_v05.db"
os.environ["SECRET_KEY"] = "pytest-secret-key-not-for-production-use"
os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "pytest-encryption-key-32b!!!!!"
os.environ["APP_ENV"] = "test"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.config import get_settings
get_settings.cache_clear()

from app.database.database import Base, engine
Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from app.main import app, VERSION
from app.agents.scheduler import scheduler_status

client = TestClient(app)


def auth():
    u = f"u_{uuid.uuid4().hex[:10]}"
    r = client.post("/api/auth/register", json={"username": u, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_version_050():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["version"].startswith("0.5")
    assert "scheduler" in r.json()


def test_root_rainmoal_050():
    r = client.get("/")
    d = r.json()
    assert d["name"] == "RainMoal Workspace"
    assert d["version"].startswith("0.5")
    assert d["agents"] == "cloud-scheduled"


def test_scheduler_status_safe():
    st = scheduler_status()
    assert "running" in st
    assert "in_flight" in st


def test_backup_sqlite():
    h = auth()
    r = client.post("/api/admin/backup", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert "message" in d


def test_system_info_no_secrets():
    h = auth()
    r = client.get("/api/admin/system", headers=h)
    assert r.status_code == 200
    text = r.text.lower()
    assert "secret" not in text
    assert "password" not in text
    assert "api_key" not in text


def test_settings_notification_prefs():
    h = auth()
    r = client.get("/api/settings", headers=h)
    assert r.status_code == 200
    # Patch prefs
    r2 = client.patch("/api/settings", headers=h, json={
        "notify_agent_failed": True,
        "notify_important_only": True,
    })
    assert r2.status_code == 200


def test_agent_off_by_default_from_prompt():
    h = auth()
    a = client.post("/api/agents/from-prompt", headers=h, json={
        "prompt": "Monitor security news hourly"
    }).json()
    assert a["status"] == "off"


def test_cross_user_run_isolation():
    h1 = auth()
    h2 = auth()
    a = client.post("/api/agents/from-prompt", headers=h1, json={"prompt": "Private"}).json()
    runs = client.get(f"/api/agents/{a['id']}/runs", headers=h2)
    assert runs.status_code == 404


def test_logout_audit():
    h = auth()
    r = client.post("/api/auth/logout", headers=h)
    assert r.status_code == 200
