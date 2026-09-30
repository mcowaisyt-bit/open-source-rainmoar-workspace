# RainMoal Workspace — Project State

**Version: 0.5.0**

## Product
**RainMoal Workspace** — Give AI a job.

## Architecture (immutable)
```
RainMoal Workspace.exe → HTTPS → Hosted FastAPI → Cloud agents
```
Agents survive closed EXE / powered-off PC.

## 0.5.0 completed
- Multi-step onboarding (skippable provider/gmail/agent steps)
- Agent run detail UI + editor Save & Enable
- Scheduler missed-run recovery (SKIPPED + reschedule)
- Notification preference fields
- SQLite backup API + retention
- Health includes scheduler status
- Tauri updater scaffold (off until configured)
- Loading/Empty/Error UI components
- 35 automated tests
- Version 0.5.0 backend/frontend/tauri

## Prior releases
- 0.4: RainMoal brand, rocket icons, deep links, duplicate-run protection
- 0.3: Gmail OAuth, drafts, provider test, Windows CI
- 0.2: Cloud agents, VITE_API_URL, Docker
- 0.1: Core MVP

## External for shipping
1. Host API on HTTPS + secrets
2. Google OAuth credentials
3. `VITE_API_URL` + `npm run tauri:build` (Windows/CI)
4. Optional: Tauri updater pubkey + release endpoint

## Commands
```bash
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
cd backend && PYTHONPATH=. pytest tests/ -v
```
