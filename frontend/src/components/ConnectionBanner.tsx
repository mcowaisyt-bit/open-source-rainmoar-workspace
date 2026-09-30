import { useEffect, useState } from 'react'
import { checkConnection, onConnectionChange } from '../services/api'

export default function ConnectionBanner() {
  const [online, setOnline] = useState(true)
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    checkConnection().then(setOnline)
    const unsub = onConnectionChange(setOnline)
    const interval = setInterval(() => checkConnection().then(setOnline), 15000)
    return () => { unsub(); clearInterval(interval) }
  }, [])

  if (online) return null

  return (
    <div className="bg-amber-500/15 border-b border-amber-500/30 px-4 py-2 flex items-center justify-between text-sm animate-fade-in">
      <div className="flex items-center gap-2 text-amber-300">
        <span className="animate-pulse-soft">●</span>
        <span>Can't reach RainMoal Workspace server — Trying to reconnect…</span>
        <span className="text-zinc-500 text-xs hidden sm:inline">Cloud agents keep running on the server.</span>
      </div>
      <button
        className="btn-ghost text-xs text-amber-300"
        disabled={checking}
        onClick={async () => {
          setChecking(true)
          await checkConnection()
          setChecking(false)
        }}
      >
        {checking ? 'Checking…' : 'Retry'}
      </button>
    </div>
  )
}
