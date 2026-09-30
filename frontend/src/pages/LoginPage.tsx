import { useState } from 'react'
import { api, setToken, User } from '../services/api'

export default function LoginPage({ onLogin }: { onLogin: (u: User) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = mode === 'login'
        ? await api.login(username, password)
        : await api.register(username, password)
      setToken(res.access_token)
      onLogin(res.user)
    } catch (err: any) {
      setError(err.message === 'CONNECTION_LOST'
        ? "Can't reach RainMoal Workspace server. Check your connection."
        : (err.message || 'Something went wrong'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-0 p-4">
      <div className="w-full max-w-sm animate-fade-in">
        <div className="text-center mb-8">
          <img src="/logo.png" alt="RainMoal" className="w-16 h-16 mx-auto mb-3 drop-shadow-[0_0_12px_rgba(245,158,11,0.4)]" />
          <h1 className="text-2xl font-bold tracking-tight">
            <span className="text-accent">Rain</span>Moal Workspace
          </h1>
          <p className="text-zinc-500 text-sm mt-1">Give AI a job.</p>
        </div>

        <form onSubmit={handleSubmit} className="panel p-6 space-y-4 shadow-glow">
          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-3 py-2">
              {error}
            </div>
          )}
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5 uppercase tracking-wider">Username</label>
            <input className="input" value={username} onChange={e => setUsername(e.target.value)}
              placeholder="username" required minLength={3} autoFocus />
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5 uppercase tracking-wider">Password</label>
            <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required minLength={8} />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'LOG IN' : 'CREATE ACCOUNT'}
          </button>
          <button type="button" className="btn-ghost w-full text-xs"
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
            {mode === 'login' ? 'CREATE ACCOUNT' : 'Already have an account? Log in'}
          </button>
        </form>
      </div>
    </div>
  )
}
