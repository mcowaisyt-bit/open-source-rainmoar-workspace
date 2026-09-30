import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, Conversation, ConversationListItem, Message } from '../services/api'

export default function ChatPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const [conv, setConv] = useState<Conversation | null>(null)
  const [input, setInput] = useState('')
  const [model, setModel] = useState('auto')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.listConversations().then(setConversations)
  }, [])

  useEffect(() => {
    if (id) {
      api.getConversation(+id).then(c => {
        setConv(c)
        setModel(c.model || 'auto')
      })
    } else {
      setConv(null)
    }
  }, [id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conv?.messages])

  async function newChat() {
    const c = await api.createConversation(model)
    setConversations(prev => [{ id: c.id, title: c.title, model: c.model }, ...prev])
    navigate(`/chat/${c.id}`)
  }

  async function send() {
    if (!input.trim() || sending) return
    let convId = conv?.id
    if (!convId) {
      const c = await api.createConversation(model)
      convId = c.id
      setConversations(prev => [{ id: c.id, title: c.title, model: c.model }, ...prev])
      navigate(`/chat/${c.id}`)
      setConv({ ...c, messages: [] })
    }

    const userContent = input.trim()
    setInput('')
    setSending(true)

    // Optimistic user message
    setConv(prev => prev ? {
      ...prev,
      messages: [...prev.messages, { id: Date.now(), role: 'user', content: userContent }],
    } : prev)

    try {
      const msg = await api.sendMessage(convId!, userContent, model)
      setConv(prev => prev ? {
        ...prev,
        messages: [...prev.messages.filter(m => m.role !== 'user' || m.id !== Date.now()),
          { id: Date.now() - 1, role: 'user', content: userContent },
          msg],
      } : prev)
      // Refresh conversation for proper IDs
      const refreshed = await api.getConversation(convId!)
      setConv(refreshed)
      api.listConversations().then(setConversations)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-56 border-r border-surface-4 bg-surface-1 flex flex-col shrink-0">
        <div className="p-3">
          <button className="btn-primary w-full text-xs" onClick={newChat}>+ New Chat</button>
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-0.5">
          {conversations.map(c => (
            <button key={c.id} onClick={() => navigate(`/chat/${c.id}`)}
              className={`w-full text-left rounded-lg px-3 py-2 text-sm truncate transition ${
                conv?.id === c.id ? 'bg-surface-3 text-zinc-100' : 'text-zinc-500 hover:bg-surface-2 hover:text-zinc-300'
              }`}>
              {c.title}
            </button>
          ))}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        <div className="border-b border-surface-4 px-4 py-2 flex items-center gap-3">
          <span className="text-sm text-zinc-400">Model:</span>
          <select className="input w-auto py-1 text-xs" value={model} onChange={e => setModel(e.target.value)}>
            <option value="auto">AUTO</option>
            <option value="openai">OpenAI</option>
            <option value="xai">Grok</option>
            <option value="gemini">Gemini</option>
          </select>
        </div>

        <div className="flex-1 overflow-auto p-6 space-y-4">
          {!conv && (
            <div className="text-center text-zinc-600 mt-20">
              <div className="text-3xl mb-2">💬</div>
              <p>Start a new conversation or select one from the sidebar.</p>
            </div>
          )}
          {conv?.messages.map(m => (
            <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[75%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
                m.role === 'user' ? 'bg-accent/20 text-zinc-100' : 'bg-surface-3 text-zinc-200'
              }`}>
                {m.content}
                {m.provider_used && (
                  <div className="text-[10px] text-zinc-500 mt-1">{m.provider_used}/{m.model_used}</div>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-surface-3 rounded-xl px-4 py-3 text-sm text-zinc-500 animate-pulse-soft">Thinking…</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-surface-4 p-4">
          <div className="flex gap-2 max-w-3xl mx-auto">
            <input className="input flex-1" placeholder="Message…" value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              disabled={sending} />
            <button className="btn-primary" onClick={send} disabled={sending || !input.trim()}>Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}
