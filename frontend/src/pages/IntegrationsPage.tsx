import { useEffect, useState } from 'react'
import { api, ProviderStatus, IntegrationStatus } from '../services/api'

export default function IntegrationsPage() {
  const [providers, setProviders] = useState<ProviderStatus[]>([])
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([])
  const [connecting, setConnecting] = useState<string | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState('')
  const [testing, setTesting] = useState<string | null>(null)
  const [testMsg, setTestMsg] = useState<Record<string, string>>({})

  function load() {
    api.listProviders().then(setProviders).catch(console.error)
    api.listIntegrations().then(setIntegrations).catch(console.error)
  }

  useEffect(() => {
    load()
    // Refresh after possible OAuth popup return
    const onFocus = () => load()
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [])

  async function connectProvider(provider: string) {
    if (!apiKey.trim()) return
    setError('')
    try {
      await api.connectProvider(provider, apiKey.trim())
      setConnecting(null)
      setApiKey('')
      load()
    } catch (err: any) {
      setError(err.message)
    }
  }

  async function disconnect(provider: string) {
    await api.disconnectProvider(provider)
    load()
  }

  async function testConn(provider: string) {
    setTesting(provider)
    try {
      const r = await api.testProvider(provider)
      setTestMsg(prev => ({
        ...prev,
        [provider]: r.ok ? `✓ ${r.message}${r.model ? ` (${r.model})` : ''}` : `✗ ${r.message}`,
      }))
      load()
    } catch (err: any) {
      setTestMsg(prev => ({ ...prev, [provider]: `✗ ${err.message}` }))
    } finally {
      setTesting(null)
    }
  }

  async function connectGoogle() {
    try {
      const { auth_url } = await api.googleAuthUrl()
      window.open(auth_url, 'google-oauth', 'width=560,height=700')
    } catch (err: any) {
      alert(err.message)
    }
  }

  async function disconnectGoogle() {
    await api.disconnectGoogle()
    load()
  }

  return (
    <div className="p-8 max-w-2xl mx-auto animate-fade-in">
      <h1 className="text-xl font-bold mb-2">Integrations</h1>
      <p className="text-sm text-zinc-500 mb-6">Connect AI providers and services. Keys are encrypted on the server.</p>

      <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">AI Providers</h2>
      <div className="space-y-3 mb-8">
        {providers.map(p => (
          <div key={p.provider} className="card">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-zinc-500 mt-0.5">
                  {p.connected ? (
                    <span className={
                      p.status === 'available' ? 'text-emerald-400' :
                      p.status === 'rate_limited' ? 'text-amber-400' : 'text-red-400'
                    }>
                      {p.status === 'available' ? '✓ Connected' :
                       p.status === 'rate_limited' ? '⚠ Rate limited' :
                       p.status === 'error' ? '✗ Error' : `● ${p.status}`}
                    </span>
                  ) : (
                    <span className="text-zinc-600">Not connected</span>
                  )}
                </div>
                {testMsg[p.provider] && (
                  <div className="text-xs mt-1 text-zinc-400">{testMsg[p.provider]}</div>
                )}
              </div>
              <div className="flex gap-2">
                {p.connected && (
                  <>
                    <button className="btn-ghost text-xs" disabled={testing === p.provider}
                      onClick={() => testConn(p.provider)}>
                      {testing === p.provider ? 'Testing…' : 'Test'}
                    </button>
                    <button className="btn-ghost text-xs text-red-400" onClick={() => disconnect(p.provider)}>
                      Disconnect
                    </button>
                  </>
                )}
                {!p.connected && (
                  <button className="btn-secondary text-xs"
                    onClick={() => { setConnecting(p.provider); setApiKey(''); setError('') }}>
                    + Connect
                  </button>
                )}
              </div>
            </div>
            {connecting === p.provider && (
              <div className="mt-3 pt-3 border-t border-surface-4 space-y-2">
                <input className="input text-xs" type="password" placeholder="Paste API key…"
                  value={apiKey} onChange={e => setApiKey(e.target.value)} autoFocus />
                {error && <div className="text-red-400 text-xs">{error}</div>}
                <div className="flex gap-2">
                  <button className="btn-primary text-xs" onClick={() => connectProvider(p.provider)}>Save & Test</button>
                  <button className="btn-ghost text-xs" onClick={() => setConnecting(null)}>Cancel</button>
                </div>
                <p className="text-[10px] text-zinc-600">API keys are encrypted at rest and never shown again.</p>
              </div>
            )}
          </div>
        ))}
      </div>

      <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Services</h2>
      <div className="space-y-3">
        {integrations.map(i => (
          <div key={i.provider} className="card flex items-center justify-between">
            <div>
              <div className="font-medium">{i.name}</div>
              <div className="text-xs text-zinc-500 mt-0.5">
                {i.connected ? (
                  <span className="text-emerald-400">✓ Connected {i.email && `· ${i.email}`}</span>
                ) : (
                  <span className="text-zinc-600">Not connected</span>
                )}
              </div>
            </div>
            {i.provider === 'google' && (
              i.connected ? (
                <button className="btn-ghost text-xs text-red-400" onClick={disconnectGoogle}>Disconnect</button>
              ) : (
                <button className="btn-secondary text-xs" onClick={connectGoogle}>
                  Connect Google Account
                </button>
              )
            )}
            {i.provider === 'outlook' && (
              <span className="text-xs text-zinc-600">Coming soon</span>
            )}
          </div>
        ))}
      </div>

      <p className="text-xs text-zinc-600 mt-6">
        Google uses official OAuth. We never ask for your Google password.
        Gmail access is limited to read + create drafts by default.
      </p>
    </div>
  )
}
