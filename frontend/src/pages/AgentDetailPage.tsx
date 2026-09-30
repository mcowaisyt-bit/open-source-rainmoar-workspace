import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Agent, AgentRun } from '../services/api'
import { LoadingState, ErrorState } from '../components/UIStates'

export default function AgentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [agent, setAgent] = useState<Agent | null>(null)
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [running, setRunning] = useState(false)
  const [editing, setEditing] = useState(false)
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', instructions: '', schedule_interval_minutes: 30, model: 'auto' })

  function load() {
    if (!id) return
    setError('')
    api.getAgent(+id).then(a => {
      setAgent(a)
      setForm({ name: a.name, instructions: a.instructions, schedule_interval_minutes: a.schedule_interval_minutes, model: a.model })
    }).catch(e => setError(e.message))
    api.listAgentRuns(+id).then(setRuns).catch(() => {})
  }

  useEffect(() => { load() }, [id])

  async function toggleStatus() {
    if (!agent) return
    const updated = await api.updateAgent(agent.id, { status: agent.status === 'on' ? 'off' : 'on' })
    setAgent(updated)
  }

  async function save(andEnable = false) {
    if (!agent) return
    const payload: any = { ...form }
    if (andEnable) payload.status = 'on'
    const updated = await api.updateAgent(agent.id, payload)
    setAgent(updated)
    setEditing(false)
  }

  async function runNow() {
    if (!agent) return
    setRunning(true)
    try {
      const run = await api.runAgentNow(agent.id)
      setRuns(prev => [run, ...prev])
      setSelectedRun(run)
      const refreshed = await api.getAgent(agent.id)
      setAgent(refreshed)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  async function remove() {
    if (!agent || !confirm('Delete this agent?')) return
    await api.deleteAgent(agent.id)
    navigate('/agents')
  }

  if (error && !agent) return <div className="p-8"><ErrorState message={error} onRetry={load} /></div>
  if (!agent) return <LoadingState label="Loading agent…" />

  const statusLabel = agent.status === 'on' ? '🟢 ACTIVE' : '🔴 OFF'

  return (
    <div className="p-8 max-w-3xl mx-auto animate-fade-in">
      <button className="btn-ghost text-xs mb-4" onClick={() => navigate('/agents')}>← Agents</button>

      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold">{agent.name}</h1>
          <p className="text-zinc-500 text-sm mt-1">{agent.description}</p>
        </div>
        <span className={`text-xs font-medium px-3 py-1 rounded-full shrink-0 ${
          agent.status === 'on' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-zinc-500/15 text-zinc-500'
        }`}>{statusLabel}</span>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        <button className="btn-secondary" onClick={toggleStatus}>
          {agent.status === 'on' ? 'Pause' : 'Resume'}
        </button>
        <button className="btn-secondary" onClick={runNow} disabled={running}>
          {running ? 'Running…' : 'Run Now'}
        </button>
        <button className="btn-ghost" onClick={() => setEditing(!editing)}>{editing ? 'Cancel' : 'Edit'}</button>
        <button className="btn-ghost text-red-400" onClick={remove}>Delete</button>
      </div>

      {editing ? (
        <div className="panel p-5 space-y-4 mb-6">
          <div>
            <label className="text-xs text-zinc-400 uppercase">Name</label>
            <input className="input mt-1" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="text-xs text-zinc-400 uppercase">Instructions</label>
            <textarea className="input mt-1 min-h-[100px]" value={form.instructions}
              onChange={e => setForm({ ...form, instructions: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-zinc-400 uppercase">Schedule (minutes)</label>
              <input type="number" className="input mt-1" min={5} max={1440}
                value={form.schedule_interval_minutes}
                onChange={e => setForm({ ...form, schedule_interval_minutes: +e.target.value })} />
            </div>
            <div>
              <label className="text-xs text-zinc-400 uppercase">Model</label>
              <select className="input mt-1" value={form.model}
                onChange={e => setForm({ ...form, model: e.target.value })}>
                <option value="auto">AUTO</option>
                <option value="openai">OpenAI</option>
                <option value="xai">Grok</option>
                <option value="gemini">Gemini</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={() => save(false)}>Save</button>
            <button className="btn-secondary" onClick={() => save(true)}>Save & Enable</button>
          </div>
        </div>
      ) : (
        <div className="panel p-5 space-y-3 mb-6 text-sm">
          <div><span className="text-zinc-500">Instructions:</span> <span className="text-zinc-300">{agent.instructions}</span></div>
          <div className="grid grid-cols-2 gap-2 text-zinc-400">
            <div>Schedule: Every {agent.schedule_interval_minutes} min</div>
            <div>Model: {agent.model.toUpperCase()}</div>
            <div>Last run: {agent.last_run_at ? new Date(agent.last_run_at).toLocaleString() : 'Never'}</div>
            <div>Next run: {agent.next_run_at && agent.status === 'on' ? new Date(agent.next_run_at).toLocaleString() : '—'}</div>
          </div>
          <div>
            <span className="text-zinc-500">Sources:</span>
            <ul className="mt-1 space-y-1">
              {agent.sources.map(s => (
                <li key={s.id} className="text-zinc-400 text-xs">• {s.name || s.url} ({s.source_type})</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Selected run detail */}
      {selectedRun && (
        <div className="panel p-5 mb-6 border-accent/30 animate-slide-up">
          <div className="flex justify-between items-start mb-3">
            <h3 className="font-semibold text-sm">Run detail</h3>
            <button className="btn-ghost text-xs" onClick={() => setSelectedRun(null)}>Close</button>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400 mb-3">
            <div>Status: <span className="text-zinc-200">{selectedRun.status}</span></div>
            <div>Duration: {selectedRun.duration_ms != null ? `${(selectedRun.duration_ms / 1000).toFixed(1)}s` : '—'}</div>
            <div>Sources: {selectedRun.sources_checked}</div>
            <div>Changes: {selectedRun.changes_detected}</div>
            <div>AI: {selectedRun.provider_used || '—'} / {selectedRun.model_used || '—'}</div>
            <div>Notification: {selectedRun.notification_sent ? 'Sent' : 'No'}</div>
          </div>
          {(selectedRun as any).routing_note && (
            <div className="text-xs text-zinc-500 mb-2">
              {(selectedRun as any).was_fallback ? '↩ Fallback: ' : 'Routing: '}
              {(selectedRun as any).routing_note}
            </div>
          )}
          {selectedRun.summary && (
            <div className="text-sm text-zinc-200 whitespace-pre-wrap bg-surface-2 rounded-lg p-3 mb-2">
              {selectedRun.summary}
            </div>
          )}
          {selectedRun.error_message && (
            <div className="text-sm text-red-400 bg-red-500/10 rounded-lg p-3">{selectedRun.error_message}</div>
          )}
          <details className="text-xs text-zinc-600 mt-2">
            <summary className="cursor-pointer">Technical details</summary>
            <pre className="mt-2 overflow-auto max-h-40 text-[10px] text-zinc-500">
              {JSON.stringify({ id: selectedRun.id, raw: (selectedRun as any).raw_data, ai: selectedRun.ai_result }, null, 2)}
            </pre>
          </details>
        </div>
      )}

      <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Run History</h2>
      {runs.length === 0 ? (
        <div className="text-zinc-600 text-sm">No runs yet. Use Run Now or enable the agent.</div>
      ) : (
        <div className="space-y-2">
          {runs.map(run => (
            <button key={run.id} onClick={() => setSelectedRun(run)}
              className="w-full card text-sm text-left hover:border-accent/40 transition">
              <div className="flex items-center justify-between mb-1">
                <span className="text-zinc-400">{run.started_at ? new Date(run.started_at).toLocaleString() : '—'}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  run.status === 'completed' ? 'bg-emerald-500/15 text-emerald-400' :
                  run.status === 'failed' ? 'bg-red-500/15 text-red-400' :
                  run.status === 'skipped' ? 'bg-zinc-500/15 text-zinc-500' :
                  'bg-amber-500/15 text-amber-400'
                }`}>{run.status}</span>
              </div>
              <div className="text-xs text-zinc-500">
                {run.sources_checked} sources · {run.changes_detected} changes
                {run.model_used && ` · ${run.provider_used}/${run.model_used}`}
                {run.duration_ms != null && ` · ${(run.duration_ms / 1000).toFixed(1)}s`}
                {run.notification_sent && ' · 🔔'}
              </div>
              {run.summary && <div className="mt-1 text-zinc-400 text-xs line-clamp-2">{run.summary}</div>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
