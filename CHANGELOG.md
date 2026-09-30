# Changelog

## 0.5.0 — Production polish (2026-09-30)

### Onboarding
- Multi-step first-run: Welcome → Profile → Providers → Gmail → First agent → Done
- All integration steps optional / skippable
- Agents created during onboarding remain OFF until enabled

### Agent experience
- Readable run detail panel (summary, routing, duration, sources)
- Technical details collapsed under expandable section
- Status labels: completed / failed / skipped / running
- Editor: Save / Save & Enable without resetting schedule unintentionally
- Run Now with progress state

### Scheduler
- Missed-schedule recovery: long downtime records SKIPPED run and reschedules (no catch-up spam)
- Health endpoint exposes safe scheduler status (running, jobs, in_flight)

### Notifications
- Granular preferences: agent completed/failed, important-only, email needs response, native OS
- Deep links retained from 0.4.0

### Ops
- `POST /api/admin/backup` — timestamped SQLite backups, retain last 14
- `GET /api/admin/system` — safe system info (no secrets)
- Tauri updater config scaffolded (inactive until pubkey + release URL set)

### UI
- Loading / Empty / Error shared components
- Settings: About 0.5.0, connection status, backup button

### Tests
- **35 passed** (version, backup, isolation, settings prefs, security, scheduler status)

## 0.4.0 — RainMoal Workspace branding + icons + reliability
## 0.3.0 — Gmail OAuth, notifications, Windows CI
## 0.2.0 — Production EXE → HTTPS path
## 0.1.0 — MVP foundation
