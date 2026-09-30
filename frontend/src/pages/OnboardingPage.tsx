import { useState } from 'react'
import { api, User } from '../services/api'

const USE_CASES = ['School / studying', 'Coding', 'Productivity', 'Research', 'Personal projects', 'Other']
const STYLES = [
  { id: 'simple', label: 'Simple & direct' },
  { id: 'detailed', label: 'Detailed' },
  { id: 'friendly', label: 'Friendly' },
  { id: 'professional', label: 'Professional' },
]

type Step = 'welcome' | 'profile' | 'providers' | 'gmail' | 'first-agent' | 'done'

export default function OnboardingPage({ user, onComplete }: { user: User; onComplete: (u: User) => void }) {
  const [step, setStep] = useState<Step>('welcome')
  const [name, setName] = useState(user.display_name || '')
  const [useCase, setUseCase] = useState('')
  const [style, setStyle] = useState('professional')
  const [loading, setLoading] = useState(false)
  const [agentPrompt, setAgentPrompt] = useState('Watch for important Apple announcements and tell me when something happens.')
  const [error, setError] = useState('')

  async function finishProfile() {
    if (!name.trim()) return
    setLoading(true)
    setError('')
    try {
      await api.onboarding({
        display_name: name.trim(),
        use_case: useCase || undefined,
        preferred_style: style,
      })
      setStep('providers')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function finishAll(skipAgent = false) {
    setLoading(true)
    setError('')
    try {
      // Ensure onboarding flag is set
      const updated = await api.onboarding({
        display_name: name.trim() || user.display_name || user.username,
        use_case: useCase || undefined,
        preferred_style: style,
      })
      if (!skipAgent && agentPrompt.trim()) {
        try {
          await api.createAgentFromPrompt(agentPrompt.trim())
        } catch {}
      }
      onComplete(updated)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function connectGoogle() {
    try {
      const { auth_url } = await api.googleAuthUrl()
      window.open(auth_url, 'google-oauth', 'width=560,height=700')
    } catch (e: any) {
      // Not configured — just skip
      setError(e.message)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-0 p-4">
      <div className="w-full max-w-md panel p-8 space-y-6 animate-slide-up shadow-glow">
        {step === 'welcome' && (
          <div className="text-center space-y-4">
            <img src="/logo.png" alt="RainMoal" className="w-20 h-20 mx-auto drop-shadow-[0_0_16px_rgba(245,158,11,0.4)]" />
            <h1 className="text-2xl font-bold">
              <span className="text-accent">Rain</span>Moal Workspace
            </h1>
            <p className="text-zinc-400 text-sm">Give AI a job.</p>
            <p className="text-zinc-500 text-xs">
              Create persistent cloud agents that monitor information and notify you — even when this app is closed.
            </p>
            <button className="btn-primary w-full" onClick={() => setStep('profile')}>GET STARTED</button>
          </div>
        )}

        {step === 'profile' && (
          <>
            <div className="text-center">
              <h2 className="text-lg font-semibold">Personalize</h2>
              <p className="text-xs text-zinc-500 mt-1">Step 2 of 5</p>
            </div>
            {error && <div className="text-red-400 text-sm">{error}</div>}
            <div>
              <label className="block text-sm text-zinc-300 mb-2">What should AI call you?</label>
              <input className="input" value={name} onChange={e => setName(e.target.value)} required placeholder="Your name" autoFocus />
            </div>
            <div>
              <label className="block text-sm text-zinc-300 mb-2">Why are you using AI?</label>
              <div className="grid grid-cols-2 gap-2">
                {USE_CASES.map(uc => (
                  <button key={uc} type="button"
                    className={`rounded-lg border px-3 py-2 text-sm transition ${useCase === uc ? 'border-accent bg-accent/10 text-accent' : 'border-surface-5 bg-surface-2 text-zinc-400 hover:border-zinc-500'}`}
                    onClick={() => setUseCase(uc)}>{uc}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm text-zinc-300 mb-2">Preferred AI style</label>
              <div className="grid grid-cols-2 gap-2">
                {STYLES.map(s => (
                  <button key={s.id} type="button"
                    className={`rounded-lg border px-3 py-2 text-sm transition ${style === s.id ? 'border-accent bg-accent/10 text-accent' : 'border-surface-5 bg-surface-2 text-zinc-400 hover:border-zinc-500'}`}
                    onClick={() => setStyle(s.id)}>{s.label}</button>
                ))}
              </div>
            </div>
            <button className="btn-primary w-full" disabled={loading || !name.trim()} onClick={finishProfile}>
              {loading ? 'Saving…' : 'Continue'}
            </button>
          </>
        )}

        {step === 'providers' && (
          <div className="space-y-4 text-center">
            <h2 className="text-lg font-semibold">Connect AI providers</h2>
            <p className="text-xs text-zinc-500">Step 3 of 5 — optional. You can do this later in Integrations.</p>
            <div className="space-y-2 text-left">
              {['OpenAI', 'xAI / Grok', 'Google Gemini'].map(n => (
                <div key={n} className="card flex justify-between items-center text-sm">
                  <span>{n}</span>
                  <span className="text-xs text-zinc-600">Not connected</span>
                </div>
              ))}
            </div>
            <button className="btn-primary w-full" onClick={() => setStep('gmail')}>Continue</button>
            <button className="btn-ghost w-full text-xs" onClick={() => setStep('gmail')}>SKIP</button>
            <p className="text-[10px] text-zinc-600">Connect API keys in Integrations after setup.</p>
          </div>
        )}

        {step === 'gmail' && (
          <div className="space-y-4 text-center">
            <h2 className="text-lg font-semibold">Connect Gmail</h2>
            <p className="text-xs text-zinc-500">Step 4 of 5 — optional</p>
            <p className="text-sm text-zinc-400">Let RainMoal analyze and organize your inbox. We never ask for your Google password.</p>
            {error && <div className="text-red-400 text-sm">{error}</div>}
            <button className="btn-primary w-full" onClick={async () => { await connectGoogle(); setStep('first-agent') }}>
              CONNECT GMAIL
            </button>
            <button className="btn-ghost w-full text-xs" onClick={() => setStep('first-agent')}>SKIP FOR NOW</button>
          </div>
        )}

        {step === 'first-agent' && (
          <div className="space-y-4">
            <div className="text-center">
              <h2 className="text-lg font-semibold">Create your first AI job</h2>
              <p className="text-xs text-zinc-500">Step 5 of 5 — optional. Agent starts OFF until you enable it.</p>
            </div>
            <textarea className="input min-h-[80px] text-sm" value={agentPrompt}
              onChange={e => setAgentPrompt(e.target.value)}
              placeholder="Watch for important Apple announcements…" />
            <button className="btn-primary w-full" disabled={loading} onClick={() => finishAll(false)}>
              {loading ? 'Creating…' : 'CREATE MY FIRST AGENT'}
            </button>
            <button className="btn-ghost w-full text-xs" disabled={loading} onClick={() => finishAll(true)}>SKIP</button>
          </div>
        )}

        {step === 'done' && (
          <div className="text-center space-y-4">
            <img src="/logo.png" alt="" className="w-16 h-16 mx-auto" />
            <h2 className="text-xl font-bold">You're ready.</h2>
            <p className="text-zinc-400 text-sm">Give AI a job.</p>
            <button className="btn-primary w-full" onClick={() => finishAll(true)}>OPEN WORKSPACE</button>
          </div>
        )}
      </div>
    </div>
  )
}
