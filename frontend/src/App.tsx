import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api, setToken, User } from './services/api'
import LoginPage from './pages/LoginPage'
import OnboardingPage from './pages/OnboardingPage'
import DashboardLayout from './components/DashboardLayout'
import DashboardPage from './pages/DashboardPage'
import AgentsPage from './pages/AgentsPage'
import AgentDetailPage from './pages/AgentDetailPage'
import ChatPage from './pages/ChatPage'
import IntegrationsPage from './pages/IntegrationsPage'
import SettingsPage from './pages/SettingsPage'
import EmailPage from './pages/EmailPage'
import HistoryPage from './pages/HistoryPage'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('acc_token')
    if (!token) {
      setLoading(false)
      return
    }
    api.me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-0">
        <div className="text-accent text-2xl animate-pulse-soft">⚡</div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={
        user ? <Navigate to="/" /> : <LoginPage onLogin={setUser} />
      } />
      <Route path="/onboarding" element={
        !user ? <Navigate to="/login" /> :
        user.onboarding_completed ? <Navigate to="/" /> :
        <OnboardingPage user={user} onComplete={setUser} />
      } />
      <Route path="/" element={
        !user ? <Navigate to="/login" /> :
        !user.onboarding_completed ? <Navigate to="/onboarding" /> :
        <DashboardLayout user={user} onLogout={() => { setToken(null); setUser(null) }} />
      }>
        <Route index element={<DashboardPage />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/:id" element={<AgentDetailPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="chat/:id" element={<ChatPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="email" element={<EmailPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}
