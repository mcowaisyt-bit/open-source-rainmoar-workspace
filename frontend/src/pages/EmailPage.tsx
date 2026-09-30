import { useEffect, useState } from 'react'
import { api, EmailItem, EmailAnalysis, IntegrationStatus } from '../services/api'

export default function EmailPage() {
  const [connected, setConnected] = useState(false)
  const [emails, setEmails] = useState<EmailItem[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<EmailAnalysis | null>(null)
  const [draftBody, setDraftBody] = useState('')
  const [creatingDraft, setCreatingDraft] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listIntegrations().then((list: IntegrationStatus[]) => {
      const g = list.find(i => i.provider === 'google')
      setConnected(!!g?.connected)
      if (g?.connected) {
        return api.gmailInbox(true).then(setEmails).catch(e => setError(e.message))
      }
    }).finally(() => setLoading(false))
  }, [])

  async function analyze(id: string) {
    setAnalyzing(id)
    setAnalysis(null)
    try {
      const a = await api.gmailAnalyze(id)
      setAnalysis(a)
      setDraftBody(a.suggested_reply && a.suggested_reply !== 'NONE' ? a.suggested_reply : '')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setAnalyzing(null)
    }
  }

  async function createDraft() {
    if (!analysis || !draftBody.trim()) return
    setCreatingDraft(true)
    try {
      // Extract email from "Name <email>" format roughly
      const toMatch = analysis.from.match(/<([^>]+)>/) || [null, analysis.from]
      const to = (toMatch[1] || analysis.from).trim()
      const res = await api.gmailCreateDraft({
        to,
        subject: analysis.subject.startsWith('Re:') ? analysis.subject : `Re: ${analysis.subject}`,
        body: draftBody,
      })
      alert(res.message + (res.draft_id ? ` (draft id: ${res.draft_id})` : ''))
    } catch (e: any) {
      alert(e.message)
    } finally {
      setCreatingDraft(false)
    }
  }

  if (loading) return <div className="p-8 text-zinc-500">Loading…</div>

  if (!connected) {
    return (
      <div className="p-8 max-w-lg mx-auto text-center animate-fade-in">
        <div className="text-3xl mb-3">📧</div>
        <h1 className="text-xl font-bold mb-2">Gmail</h1>
        <p className="text-zinc-500 text-sm mb-4">Connect Google in Integrations to classify and draft replies.</p>
        <a href="/integrations" className="btn-primary inline-flex">Open Integrations</a>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in">
      <h1 className="text-xl font-bold mb-1">Gmail</h1>
      <p className="text-sm text-zinc-500 mb-6">AI classification and reply drafts. Sending always requires your approval.</p>

      {error && <div className="mb-4 text-sm text-red-400">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-2">
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Inbox</h2>
          {emails.length === 0 && <div className="text-zinc-600 text-sm">No recent messages.</div>}
          {emails.map(e => (
            <button key={e.id} onClick={() => analyze(e.id)}
              className={`w-full card text-left hover:border-accent/40 transition ${analysis?.id === e.id ? 'border-accent/50' : ''}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{e.subject}</div>
                  <div className="text-xs text-zinc-500 truncate">{e.from_addr}</div>
                  <div className="text-xs text-zinc-600 mt-1 line-clamp-2">{e.summary || e.snippet}</div>
                </div>
                {e.classification && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
                    e.classification.includes('important') || e.needs_response
                      ? 'bg-accent/15 text-accent'
                      : 'bg-surface-4 text-zinc-500'
                  }`}>{e.classification}</span>
                )}
              </div>
              {analyzing === e.id && <div className="text-xs text-zinc-500 mt-2 animate-pulse-soft">Analyzing…</div>}
            </button>
          ))}
        </div>

        <div>
          {analysis ? (
            <div className="panel p-5 space-y-4 sticky top-4">
              <div>
                <div className="text-xs text-zinc-500 uppercase">From</div>
                <div className="text-sm">{analysis.from}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500 uppercase">Subject</div>
                <div className="text-sm font-medium">{analysis.subject}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500 uppercase">AI Summary</div>
                <div className="text-sm text-zinc-300">{analysis.summary}</div>
              </div>
              {analysis.why_matters && (
                <div>
                  <div className="text-xs text-zinc-500 uppercase">Why it matters</div>
                  <div className="text-sm text-zinc-400">{analysis.why_matters}</div>
                </div>
              )}
              <div className="flex gap-2 text-xs">
                <span className="px-2 py-0.5 rounded bg-surface-3">{analysis.classification}</span>
                {analysis.needs_response && <span className="px-2 py-0.5 rounded bg-accent/15 text-accent">Needs response</span>}
                {analysis.provider_used && <span className="text-zinc-600">{analysis.provider_used}/{analysis.model_used}</span>}
              </div>

              <div>
                <div className="text-xs text-zinc-500 uppercase mb-1">Suggested Reply</div>
                <textarea className="input min-h-[140px] text-sm" value={draftBody}
                  onChange={e => setDraftBody(e.target.value)} />
              </div>
              <div className="flex gap-2">
                <button className="btn-primary text-xs" disabled={creatingDraft || !draftBody.trim()}
                  onClick={createDraft}>
                  {creatingDraft ? 'Creating…' : 'CREATE DRAFT'}
                </button>
                <span className="text-[10px] text-zinc-600 self-center">Does not send. Review in Gmail.</span>
              </div>
            </div>
          ) : (
            <div className="text-zinc-600 text-sm panel p-8 text-center">
              Select an email to analyze
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
