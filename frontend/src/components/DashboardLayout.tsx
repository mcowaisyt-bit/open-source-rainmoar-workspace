import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { User, api, setToken } from '../services/api'
import ConnectionBanner from './ConnectionBanner'
import CommandPalette from './CommandPalette'
import { startNotificationPoll } from '../services/notifications'

const NAV = [
  { to: '/', label: 'Command Center', icon: '⚡', shortcut: '1' },
  { to: '/chat', label: 'Chat', icon: '💬', shortcut: '2' },
  { to: '/agents', label: 'Agents', icon: '🤖', shortcut: '3' },
  { to: '/email', label: 'Email', icon: '📧', shortcut: '' },
  { to: '/history', label: 'History', icon: '🕘', shortcut: '4' },
  { to: '/integrations', label: 'Integrations', icon: '🔌', shortcut: '' },
  { to: '/settings', label: 'Settings', icon: '⚙', shortcut: '' },
]

export default function DashboardLayout({ user, onLogout }: { user: User; onLogout: () => void }) {
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const poll = startNotificationPoll(45000, (path) => navigate(path))
    return () => clearInterval(poll)
  }, [navigate])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'p') {
        e.preventDefault()
        setPaletteOpen(true)
      }
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey) {
        if (e.key === '1') { e.preventDefault(); navigate('/') }
        if (e.key === '2') { e.preventDefault(); navigate('/chat') }
        if (e.key === '3') { e.preventDefault(); navigate('/agents') }
        if (e.key === '4') { e.preventDefault(); navigate('/history') }
        if (e.key === 'k') { e.preventDefault(); setPaletteOpen(true) }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navigate])

  // Deep-link from notification click (query param or hash)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const agentId = params.get('agent')
    const runId = params.get('run')
    if (agentId) {
      navigate(`/agents/${agentId}${runId ? `?run=${runId}` : ''}`)
    }
  }, [navigate])

  async function handleLogout() {
    try { await api.logout() } catch {}
    setToken(null)
    onLogout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col bg-surface-0">
      <ConnectionBanner />
      <div className="flex flex-1 overflow-hidden">
        <aside className={`${collapsed ? 'w-14' : 'w-56'} border-r border-surface-4 bg-surface-1 flex flex-col shrink-0 transition-all duration-200`}>
          <div className="p-3 border-b border-surface-4 flex items-center justify-between">
            {!collapsed && (
              <div className="flex items-center gap-2 min-w-0">
                <img src="/logo.png" alt="" className="w-7 h-7 shrink-0" />
                <div className="min-w-0">
                  <div className="font-semibold text-sm leading-tight truncate">
                    <span className="text-accent">Rain</span>Moal
                  </div>
                  <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Workspace</div>
                </div>
              </div>
            )}
            {collapsed && <img src="/logo.png" alt="" className="w-7 h-7 mx-auto" />}
            <button className="btn-ghost p-1 text-xs" onClick={() => setCollapsed(!collapsed)} title="Toggle sidebar">
              {collapsed ? '»' : '«'}
            </button>
          </div>
          <nav className="flex-1 p-2 space-y-0.5">
            {NAV.map(item => (
              <NavLink key={item.to} to={item.to} end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                    isActive ? 'bg-accent/10 text-accent font-medium' : 'text-zinc-400 hover:text-zinc-100 hover:bg-surface-3'
                  } ${collapsed ? 'justify-center' : ''}`
                }
                title={item.label}
              >
                <span className="text-base shrink-0">{item.icon}</span>
                {!collapsed && <span className="truncate">{item.label}</span>}
              </NavLink>
            ))}
          </nav>
          <div className="p-3 border-t border-surface-4">
            {!collapsed && (
              <>
                <div className="text-xs text-zinc-500 mb-1 truncate">{user.display_name || user.username}</div>
                <button onClick={() => setPaletteOpen(true)} className="btn-ghost text-xs w-full justify-start px-2 mb-1">
                  ⌘ Command Palette
                </button>
                <button onClick={handleLogout} className="btn-ghost text-xs w-full justify-start px-2">
                  Log out
                </button>
              </>
            )}
            {collapsed && (
              <button onClick={handleLogout} className="btn-ghost text-xs w-full justify-center" title="Log out">⏻</button>
            )}
          </div>
        </aside>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  )
}
