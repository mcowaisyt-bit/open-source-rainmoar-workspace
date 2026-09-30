import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, Agent } from '../services/api'

function timeAgo(iso?: string | null): string {
  if (!iso) return 'Never'
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (sec < 60) return `${sec}s ago`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`
  return new Date(iso).toLocaleDateString()
}

function timeUntil(iso?: string | null): string {
  if (!iso) return '—'
  const sec = Math.floor((new Date(iso).getTime() - Date.now()) / 1000)
  if (sec < 0) return 'Due now'
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m`
  return `${Math.floor(sec / 3600)}h`
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [runningId, setRunningId] = useState<number | null>(null)
  const navigate = useNavigate()

  function load() {
    api.listAgents().then(setAgents).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  async function toggleStatus(agent: Agent) {
    const newStatus = agent.status === 'on' ? 'off' : 'on'
    const updated = await api.updateAgent(agent.id, { status: newStatus })
    setAgents(prev => prev.map(a => a.id === agent.id ? updated : a))
  }

  async function runNow(agent: Agent, e: React.MouseEvent) {
    e.stopPropagation()
    setRunningId(agent.id)
    try {
      await api.runAgentNow(agent.id)
      load()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setRunningId(null)
    }
  }

  async function remove(agent: Agent, e: React.MouseEvent) {
    e.stopPropagation()
    if (!confirm(`Delete agent "${agent.name}"?`)) return
    await api.deleteAgent(agent.id)
    setAgents(prev => prev.filter(a => a.id !== agent.id))
  }

  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold">Agents</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Cloud agents keep running when this app is closed.</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/')}>+ New Agent</button>
      </div>

      {loading ? <div className="text-zinc-500">Loading…</div> :
        agents.length === 0 ? (
          <div className="card text-center py-12 text-zinc-500">
            No agents yet. Go to Command Center and give AI a job.
          </div>
        ) : (
          <div className="space-y-3">
            {agents.map(agent => (
              <div key={agent.id} className="card hover:border-accent/30 transition">
                <div className="flex items-start justify-between gap-3">
                  <button className="flex-1 text-left min-w-0" onClick={() => navigate(`/agents/${agent.id}`)}>
                    <div className="font-medium">{agent.name}</div>
                    <div className="text-xs text-zinc-500 mt-0.5 line-clamp-1">{agent.description || agent.instructions}</div>
                    <div className="text-xs text-zinc-600 mt-2 flex flex-wrap gap-x-3 gap-y-1">
                      <span>Every {agent.schedule_interval_minutes} min</span>
                      <span>Last: {timeAgo(agent.last_run_at)}</span>
                      {agent.status === 'on' && <span>Next: {timeUntil(agent.next_run_at)}</span>}
                      <span>AI: {agent.model.toUpperCase()}</span>
                      <span>{agent.sources?.length || 0} source(s)</span>
                    </div>
                  </button>
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full shrink-0 ${
                    agent.status === 'on' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-zinc-500/15 text-zinc-500'
                  }`}>
                    {agent.status === 'on' ? '● ON' : '○ OFF'}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-surface-4">
                  <button className="btn-secondary text-xs" onClick={() => navigate(`/agents/${agent.id}`)}>Open</button>
                  <button className="btn-secondary text-xs" onClick={(e) => runNow(agent, e)} disabled={runningId === agent.id}>
                    {runningId === agent.id ? 'Running…' : 'Run Now'}
                  </button>
                  <button className="btn-ghost text-xs" onClick={(e) => { e.stopPropagation(); toggleStatus(agent) }}>
                    {agent.status === 'on' ? 'Pause' : 'Resume'}
                  </button>
                  <button className="btn-ghost text-xs" onClick={() => navigate(`/agents/${agent.id}`)}>History</button>
                  <button className="btn-ghost text-xs text-red-400" onClick={(e) => remove(agent, e)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )
      }
    </div>
  )
}
