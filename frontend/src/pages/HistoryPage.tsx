import { useEffect, useState } from 'react'
import { api, AuditLog } from '../services/api'

export default function HistoryPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listAudit().then(setLogs).finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-8 max-w-3xl mx-auto animate-fade-in">
      <h1 className="text-xl font-bold mb-6">Audit Log</h1>
      {loading ? <div className="text-zinc-500">Loading…</div> :
        logs.length === 0 ? (
          <div className="card text-center py-8 text-zinc-500">No activity yet.</div>
        ) : (
          <div className="space-y-1">
            {logs.map(log => (
              <div key={log.id} className="flex items-center gap-4 px-3 py-2 rounded-lg hover:bg-surface-2 text-sm">
                <span className="text-zinc-600 text-xs w-36 shrink-0">
                  {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                </span>
                <span className="text-zinc-300 font-mono text-xs">{log.action}</span>
                {log.resource_type && (
                  <span className="text-zinc-600 text-xs">{log.resource_type}
                  {log.resource_id != null && ` #${log.resource_id}`}</span>
                )}
              </div>
            ))}
          </div>
        )
      }
    </div>
  )
}
