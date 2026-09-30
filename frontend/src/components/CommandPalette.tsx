import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

interface Command {
  id: string
  label: string
  shortcut?: string
  action: () => void
}

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const commands: Command[] = [
    { id: 'dash', label: 'Open Dashboard', shortcut: 'Ctrl+1', action: () => navigate('/') },
    { id: 'chat', label: 'Open Chat', shortcut: 'Ctrl+2', action: () => navigate('/chat') },
    { id: 'agents', label: 'Open Agents', shortcut: 'Ctrl+3', action: () => navigate('/agents') },
    { id: 'history', label: 'Open History', shortcut: 'Ctrl+4', action: () => navigate('/history') },
    { id: 'integrations', label: 'Open Integrations', action: () => navigate('/integrations') },
    { id: 'settings', label: 'Open Settings', action: () => navigate('/settings') },
    { id: 'new-agent', label: 'Create Agent', action: () => navigate('/') },
    { id: 'new-chat', label: 'New Chat', action: () => navigate('/chat') },
  ]

  const filtered = commands.filter(c =>
    c.label.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, filtered.length - 1)) }
      if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)) }
      if (e.key === 'Enter' && filtered[selected]) {
        filtered[selected].action()
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, filtered, selected, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={onClose}>
      <div className="w-full max-w-lg panel shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="w-full bg-transparent border-b border-surface-4 px-4 py-3 text-sm outline-none placeholder-zinc-600"
          placeholder="Type a command…"
          value={query}
          onChange={e => { setQuery(e.target.value); setSelected(0) }}
        />
        <div className="max-h-72 overflow-auto py-1">
          {filtered.length === 0 && (
            <div className="px-4 py-3 text-sm text-zinc-600">No commands found</div>
          )}
          {filtered.map((cmd, i) => (
            <button
              key={cmd.id}
              className={`w-full flex items-center justify-between px-4 py-2.5 text-sm text-left transition ${
                i === selected ? 'bg-accent/15 text-accent' : 'text-zinc-300 hover:bg-surface-3'
              }`}
              onClick={() => { cmd.action(); onClose() }}
              onMouseEnter={() => setSelected(i)}
            >
              <span>{cmd.label}</span>
              {cmd.shortcut && <span className="text-xs text-zinc-600 font-mono">{cmd.shortcut}</span>}
            </button>
          ))}
        </div>
        <div className="border-t border-surface-4 px-4 py-2 text-[10px] text-zinc-600">
          ↑↓ navigate · Enter select · Esc close
        </div>
      </div>
    </div>
  )
}
