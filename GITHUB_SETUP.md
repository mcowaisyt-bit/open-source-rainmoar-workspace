# GitHub setup for RainMoal Workspace v0.5.0

This archive is cleaned for GitHub:
- `.env` and local secrets removed
- Python virtual environment removed
- Python caches/bytecode removed
- Local SQLite databases removed
- Node/Tauri build output excluded by `.gitignore`

Before pushing:
1. Copy `.env.example` to `.env` only for local development.
2. Never commit `.env`.
3. For production, configure secrets in your hosting provider.
4. Deploy the `backend/` service as described in `DEPLOY.md`.
5. Build the Windows client with `VITE_API_URL` set to the hosted HTTPS API.
