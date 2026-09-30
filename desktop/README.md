# Desktop packaging

For Windows `.exe` packaging, use one of:

## Option A — Electron
1. Add electron to frontend
2. Wrap the Vite build + point to backend (or embed backend)

## Option B — Tauri (recommended for smaller binary)
1. `npm install -D @tauri-apps/cli`
2. `npx tauri init`
3. Configure to load the React UI and optionally bundle the Python backend

## Option C — Development mode
Run backend + frontend separately; open in browser.
Later package with Electron/Tauri for `AICommandCenter.exe`.

The API is designed so an Android client can connect to the same backend later.
