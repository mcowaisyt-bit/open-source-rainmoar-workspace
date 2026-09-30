# Deployment Guide — RainMoal Workspace

## Production architecture

```
User PC                          Cloud
─────────                        ─────
RainMoalWorkspace.exe  ──HTTPS──►  api.YOURDOMAIN.com (FastAPI)
                                 ├── Agent scheduler (always on)
                                 ├── SQLite or PostgreSQL
                                 └── Calls OpenAI / Grok / Gemini
```

## 1. Deploy the backend

### Option A: Docker (recommended)

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
cd backend
docker build -t rainmoal-workspace-api .
docker run -d -p 8000:8000 --env-file ../.env \
  -v acc-data:/tmp \
  --name acc-api rainmoal-workspace-api
```

### Option B: Railway / Render / Fly.io

1. Connect the `backend/` directory as the service root.
2. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set all env vars from `.env.example` (use strong secrets).
4. Attach a persistent volume or use managed Postgres (`DATABASE_URL=postgresql://...`).

### Option C: VPS (systemd)

```bash
# On the server
git clone <repo> && cd RainMoalWorkspace/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Configure .env with APP_ENV=production, strong SECRET_KEY, etc.
# Put behind nginx + certbot for HTTPS
```

### Required production env

```
APP_ENV=production
SECRET_KEY=<long-random>
CREDENTIAL_ENCRYPTION_KEY=<long-random>
DATABASE_URL=postgresql://...   # or sqlite with persistent volume
PUBLIC_API_URL=https://api.YOURDOMAIN.com
FRONTEND_URL=tauri://localhost
CORS_ORIGINS=tauri://localhost,http://tauri.localhost,https://app.YOURDOMAIN.com
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://api.YOURDOMAIN.com/api/integrations/google/callback
```

Put HTTPS in front (Caddy, nginx + Let's Encrypt, or platform TLS).

## 2. Build the Windows EXE

**Requires a Windows machine (or Windows CI) with:**
- Node.js 18+
- Rust (rustup)
- WebView2 (usually preinstalled on Win10/11)

```powershell
cd frontend
npm install

# Point the client at your hosted API
echo VITE_API_URL=https://api.YOURDOMAIN.com > .env.production

# Generate icons (optional but recommended)
# npx tauri icon path\to\icon-1024.png

npm run tauri:build
```

Artifacts:
- `src-tauri/target/release/rainmoal-workspace.exe`
- Installer under `src-tauri/target/release/bundle/nsis/` or `msi/`

Distribute `RainMoalWorkspace-Setup.exe` to users.

## 3. User flow (production)

1. Download & install EXE  
2. Open **RainMoal Workspace**  
3. Create account / log in (talks to `https://api.YOURDOMAIN.com`)  
4. Connect AI providers (API keys encrypted on server)  
5. Optionally connect Google  
6. Create agent → Enable  
7. Close EXE / shut down PC → **agents keep running on the server**  
8. Open EXE later → see run history, notifications, results  

## 4. Verify cloud agents

1. Create an agent, set schedule to 5 minutes, enable it.  
2. Close the desktop app completely.  
3. Wait 5+ minutes.  
4. Reopen the app → agent detail should show a new run in history.  

If no runs appear, check backend logs for scheduler errors and that `APP_ENV` / DB volume is persistent.

## 5. Development vs production

| | Development | Production |
|---|---|---|
| API URL | `http://localhost:8000` (Vite proxy) | `https://api.YOURDOMAIN.com` |
| Frontend | `npm run dev` | Built into EXE |
| Agents | Local backend scheduler | Same scheduler on hosted server |
| Database | `/tmp` or local SQLite | Persistent volume or Postgres |

**Never hardcode localhost into the production EXE build.**


## Gmail OAuth setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Gmail API** and **Google People API** (or userinfo).
3. Create OAuth 2.0 Client ID (Web application).
4. Authorized redirect URI:
   `https://api.YOURDOMAIN.com/api/integrations/google/callback`
5. Set on the server:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=https://api.YOURDOMAIN.com/api/integrations/google/callback
   ```
6. In the desktop app: Integrations → Connect Google Account.


## Production verification checklist

1. Deploy FastAPI behind HTTPS
2. Set strong `SECRET_KEY` and `CREDENTIAL_ENCRYPTION_KEY`
3. Configure database (SQLite volume or Postgres)
4. Set Google OAuth client + redirect URI
5. Verify `/health` returns version and scheduler.running
6. Build EXE with `VITE_API_URL=https://api.YOURDOMAIN.com`
7. Install on Windows → login
8. Connect a provider → Test
9. Optional: Connect Gmail
10. Create agent → Enable
11. Close EXE / power off PC
12. Confirm agent still runs (history after reopen)
13. Confirm notification + deep link
14. Backup: `POST /api/admin/backup` or `pg_dump`

## Database backups

### SQLite
- API: authenticated `POST /api/admin/backup`
- Files: `backups/rainmoal-YYYYMMDDTHHMMSSZ.db`
- Retention: last 14 backups kept automatically
- Never overwrite the live DB file during backup

### PostgreSQL
```bash
pg_dump "$DATABASE_URL" > backup-$(date +%Y%m%d).sql
```

## Automatic updates (Tauri)

Updater is scaffolded in `tauri.conf.json` with `"active": false`.
To enable:
1. Generate updater keypair (`tauri signer generate`)
2. Host signed release manifests
3. Set `pubkey` and `endpoints`
4. Set `"active": true`
Never distribute unsigned executables as updates.
