import { useEffect, useState } from 'react'
import { api, UserSettings, checkConnection, getApiBase } from '../services/api'

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const [apiVersion, setApiVersion] = useState('')
  const [backupMsg, setBackupMsg] = useState('')
  const apiBase = getApiBase()

  useEffect(() => {
    api.getSettings().then(setSettings).catch(console.error)
    checkConnection().then(async (ok) => {
      setApiOnline(ok)
      if (ok) {
        try {
          const r = await fetch(`${apiBase || ''}/api/status`)
          const d = await r.json()
          setApiVersion(d.version || '')
        } catch {}
      }
    })
  }, [apiBase])

  async function update(patch: Partial<UserSettings>) {
    if (!settings) return
    setSaving(true)
    try {
      const updated = await api.updateSettings(patch)
      setSettings(updated)
    } finally {
      setSaving(false)
    }
  }

  async function doBackup() {
    setBackupMsg('Creating backup…')
    try {
      const token = localStorage.getItem('acc_token')
      const r = await fetch(`${apiBase || ''}/api/admin/backup`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      const d = await r.json()
      setBackupMsg(d.message + (d.file ? `: ${d.file}` : ''))
    } catch (e: any) {
      setBackupMsg(e.message || 'Backup failed')
    }
  }

  if (!settings) {
    return (
      <div className="p-8 flex justify-center">
        <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    )
  }

  const boolPref = (key: keyof UserSettings, label: string) => (
    <label className="flex items-center justify-between text-sm">
      <span>{label}</span>
      <input type="checkbox" checked={!!(settings as any)[key]}
        onChange={e => update({ [key]: e.target.checked } as any)} className="accent-accent" />
    </label>
  )

  return (
    <div className="p-8 max-w-xl mx-auto animate-fade-in">
      <h1 className="text-xl font-bold mb-6">Settings</h1>
      <div className="space-y-6">
        <section className="panel p-5">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Backend connection</h2>
          <div className="text-sm space-y-2">
            <div className="flex justify-between gap-4">
              <span className="text-zinc-500">API</span>
              <span className="font-mono text-xs text-zinc-300 truncate max-w-[240px] text-right">
                {apiBase || '(Vite proxy)'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Status</span>
              <span className={apiOnline ? 'text-emerald-400' : 'text-amber-400'}>
                {apiOnline ? '🟢 Connected' : apiOnline === false ? '🟡 Offline' : '…'}
              </span>
            </div>
            {apiVersion && (
              <div className="flex justify-between">
                <span className="text-zinc-500">Server version</span>
                <span className="text-zinc-300">{apiVersion}</span>
              </div>
            )}
          </div>
        </section>

        <section className="panel p-5">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">AI</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-zinc-400">Default model</label>
              <select className="input mt-1" value={settings.default_model}
                onChange={e => update({ default_model: e.target.value })}>
                <option value="auto">AUTO</option>
                <option value="openai">OpenAI</option>
                <option value="xai">Grok</option>
                <option value="gemini">Gemini</option>
              </select>
            </div>
            {boolPref('auto_routing', 'Auto routing')}
            {boolPref('auto_fallback', 'Auto fallback')}
          </div>
        </section>

        <section className="panel p-5">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Notifications</h2>
          <div className="space-y-3">
            {boolPref('notifications_enabled', 'Enable notifications')}
            {boolPref('notification_sound', 'Notification sound')}
            {boolPref('native_notifications' as any, 'Native Windows notifications')}
            {boolPref('notify_agent_completed' as any, 'Agent completed')}
            {boolPref('notify_agent_failed' as any, 'Agent failed')}
            {boolPref('notify_important_only' as any, 'Important results only')}
            {boolPref('notify_email_needs_response' as any, 'Email needs response')}
          </div>
        </section>

        <section className="panel p-5">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Data</h2>
          <button className="btn-secondary text-xs" onClick={doBackup}>Create database backup</button>
          {backupMsg && <p className="text-xs text-zinc-500 mt-2">{backupMsg}</p>}
        </section>

        <section className="panel p-5">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">About</h2>
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="" className="w-12 h-12" />
            <div className="text-sm space-y-0.5">
              <div className="font-medium"><span className="text-accent">Rain</span>Moal Workspace</div>
              <div className="text-zinc-400">Version 0.5.0</div>
              <div className="text-xs text-zinc-600">Give AI a job.</div>
              <div className="text-xs text-zinc-600 mt-1">Updates: configure Tauri updater endpoints for auto-update.</div>
            </div>
          </div>
        </section>
        {saving && <div className="text-xs text-zinc-500">Saving…</div>}
      </div>
    </div>
  )
}
