import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, Agent, ProviderStatus } from '../services/api'

function timeAgo(iso?: string | null): string {
  if (!iso) return 'Never'
  const d = new Date(iso)
  const sec = Math.floor((Date.now() - d.getTime()) / 1000)
  if (sec < 60) return `${sec}s ago`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`
  return d.toLocaleDateString()
}

function timeUntil(iso?: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const sec = Math.floor((d.getTime() - Date.now()) / 1000)
  if (sec < 0) return 'Due now'
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m`
  return `${Math.floor(sec / 3600)}h`
}

function agentIcon(name: string): string {
  const n = name.toLowerCase()
  if (n.includes('apple')) return '🍎'
  if (n.includes('email') || n.includes('gmail')) return '📧'
  if (n.includes('news') || n.includes('ai')) return '📰'
  if (n.includes('github')) return '💻'
  if (n.includes('calendar')) return '📅'
  return '🤖'
}

export default function DashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [providers, setProviders] = useState<ProviderStatus[]>([])
  const [prompt, setPrompt] = useState('')
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<Agent | null>(null)
  const navigate = useNavigate()

  function load() {
    Promise.all([api.listAgents(), api.listProviders()])
      .then(([a, p]) => { setAgents(a); setProviders(p) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 30000)
    return () => clearInterval(t)
  }, [])

  async function handleCreate() {
    if (!prompt.trim()) return
    setCreating(true)
    try {
      const agent = await api.createAgentFromPrompt(prompt.trim())
      setPreview(agent)
      setPrompt('')
      load()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setCreating(false)
    }
  }

  async function activatePreview() {
    if (!preview) return
    await api.updateAgent(preview.id, { status: 'on' })
    setPreview(null)
    load()
    navigate(`/agents/${preview.id}`)
  }

  const activeCount = agents.filter(a => a.status === 'on').length
  const connectedProviders = providers.filter(p => p.connected)

  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in">
      <div className="text-center mb-10">
        <div className="flex items-center justify-center gap-3 mb-2">
          <img src="/logo.png" alt="" className="w-10 h-10 drop-shadow-[0_0_10px_rgba(245,158,11,0.35)]" />
          <h1 className="text-3xl font-bold tracking-tight">GIVE AI A JOB.</h1>
        </div>
        <p className="text-zinc-400 text-sm"><span className="text-accent font-medium">Rain</span>Moal Workspace</p>
        <p className="text-zinc-500 text-sm">Tell AI what you want monitored, handled, or automated.</p>
        <p className="text-zinc-600 text-xs mt-1">Agents run in the cloud — they keep working even when this app is closed.</p>
      </div>

      {/* Create agent */}
      <div className="panel p-6 mb-8">
        <label className="block text-sm text-zinc-400 mb-3">What should I keep an eye on?</label>
        <div className="flex gap-3">
          <input
            className="input flex-1"
            placeholder="Watch for important Apple announcements every 30 minutes and notify me…"
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
          />
          <button className="btn-primary shrink-0" onClick={handleCreate} disabled={creating || !prompt.trim()}>
            {creating ? 'Creating…' : '⚡ CREATE AGENT'}
          </button>
        </div>
      </div>

      {/* Preview modal-ish */}
      {preview && (
        <div className="panel p-6 mb-8 border-accent/40 animate-slide-up">
          <div className="text-xs text-accent uppercase tracking-wider mb-2">Agent Preview</div>
          <h3 className="text-lg font-semibold mb-1">{preview.name}</h3>
          <p className="text-sm text-zinc-400 mb-3">{preview.description}</p>
          <div className="grid grid-cols-2 gap-2 text-xs text-zinc-500 mb-4">
            <div>Schedule: Every {preview.schedule_interval_minutes} min</div>
            <div>Model: {preview.model.toUpperCase()}</div>
            <div>Sources: {preview.sources.map(s => s.name || s.url).join(', ')}</div>
            <div>Notifications: {preview.notification_enabled ? 'On' : 'Off'}</div>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={activatePreview}>CREATE & ENABLE</button>
            <button className="btn-secondary" onClick={() => navigate(`/agents/${preview.id}`)}>EDIT</button>
            <button className="btn-ghost" onClick={() => setPreview(null)}>CANCEL</button>
          </div>
        </div>
      )}

      {/* Active agents */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
            Active Agents {activeCount > 0 && <span className="text-accent">({activeCount})</span>}
          </h2>
          <button className="btn-ghost text-xs" onClick={() => navigate('/agents')}>View all</button>
        </div>

        {loading ? (
          <div className="text-zinc-600 text-sm">Loading…</div>
        ) : agents.length === 0 ? (
          <div className="card text-center text-zinc-500 text-sm py-10">
            <div className="text-2xl mb-2 opacity-40">⚡</div>
            No agents yet. Type a job above to create your first AI worker.
          </div>
        ) : (
          <div className="space-y-2">
            {agents.slice(0, 8).map(agent => (
              <button
                key={agent.id}
                onClick={() => navigate(`/agents/${agent.id}`)}
                className="w-full card flex items-center justify-between hover:border-accent/40 transition text-left group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-lg shrink-0">{agentIcon(agent.name)}</span>
                  <div className="min-w-0">
                    <div className="font-medium text-sm truncate">{agent.name}</div>
                    <div className="text-xs text-zinc-500 flex flex-wrap gap-x-3">
                      <span>Every {agent.schedule_interval_minutes} min</span>
                      <span>Last: {timeAgo(agent.last_run_at)}</span>
                      {agent.status === 'on' && <span>Next: {timeUntil(agent.next_run_at)}</span>}
                      <span>AI: {agent.model.toUpperCase()}</span>
                    </div>
                  </div>
                </div>
                <span className={`text-xs font-medium px-2.5 py-1 rounded-full shrink-0 ${
                  agent.status === 'on'
                    ? 'bg-emerald-500/15 text-emerald-400'
                    : 'bg-zinc-500/15 text-zinc-500'
                }`}>
                  {agent.status === 'on' ? '● ACTIVE' : '○ OFF'}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* AI Status */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">AI Status</h2>
        <div className="grid grid-cols-3 gap-3">
          {providers.map(p => (
            <div key={p.provider} className="card text-center">
              <div className="text-xs text-zinc-500 mb-1">{p.name}</div>
              <div className={`text-sm font-medium ${
                p.connected && p.status === 'available' ? 'text-emerald-400' :
                p.connected ? 'text-amber-400' : 'text-zinc-600'
              }`}>
                {p.connected
                  ? (p.status === 'available' ? '🟢 Connected' : `🟡 ${p.status}`)
                  : '○ Not connected'}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 text-xs text-zinc-600 text-center">
          AUTO ROUTING: ON · AUTO FALLBACK: ON
          {connectedProviders.length === 0 && (
            <span className="text-amber-500/80"> · Connect a provider in Integrations to enable AI</span>
          )}
        </div>
      </div>
    </div>
  )
}
