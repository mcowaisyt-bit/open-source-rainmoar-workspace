# RainMoal Workspace (v0.5.0)

> **Give AI a job.**

Personal AI workspace for Windows. Create persistent **cloud agents** that monitor information, analyze changes, and notify you — even when your PC is off.

```
DOWNLOAD INSTALLER → INSTALL → OPEN RainMoal Workspace → LOGIN
→ CONNECT AI → CREATE AGENT → CLOSE APP → AGENT KEEPS RUNNING ONLINE
→ NOTIFICATION → OPEN → SEE RESULTS
```

## Architecture

```
RainMoal Workspace.exe  (Tauri desktop client)
        │  HTTPS
        ▼
Hosted FastAPI Backend
        │
        ├── Cloud agent scheduler (DB-persisted)
        ├── AI Model Router (OpenAI · Grok · Gemini)
        ├── Gmail OAuth + drafts
        └── Encrypted credentials
```

Production builds never hardcode `localhost`. Set `VITE_API_URL=https://api.YOURDOMAIN.com` before building the EXE.

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env
export PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Windows production build

```powershell
cd frontend
echo VITE_API_URL=https://api.YOURDOMAIN.com > .env.production
npm install
npm run tauri:build
# Installer: src-tauri/target/release/bundle/nsis/
```

Or use GitHub Actions (`windows-build.yml`) on `windows-latest`.

## Features

- **Cloud agents** — schedule, RSS, AI analysis, history (survive closed EXE)
- **Natural-language agent creation** — preview before enable
- **AI Model Router** — AUTO + automatic fallback
- **Gmail** — OAuth, classify, analyze, draft (send requires confirm)
- **Native notifications** + deep link to agent
- **RainMoal rocket branding** and Windows icon pack
- **Security** — Argon2id, encrypted API keys & OAuth tokens, user isolation

## Docs

- [DEPLOY.md](./DEPLOY.md) — cloud + EXE + Gmail OAuth
- [claude.md](./claude.md) — implementation state
- [CHANGELOG.md](./CHANGELOG.md)

---

**RainMoal Workspace · Give AI a job.**
