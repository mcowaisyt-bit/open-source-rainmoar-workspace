/**
 * Native Windows notifications via Tauri when available.
 * Supports deep-link payload so clicking opens the relevant page.
 */

type NavigateFn = (path: string) => void

export async function showNativeNotification(opts: {
  title: string
  body: string
  path?: string  // deep link path e.g. /agents/3
}): Promise<boolean> {
  try {
    const { isPermissionGranted, requestPermission, sendNotification } =
      await import('@tauri-apps/plugin-notification')

    let granted = await isPermissionGranted()
    if (!granted) {
      const perm = await requestPermission()
      granted = perm === 'granted'
    }
    if (!granted) return false

    // Include path in body metadata for click handlers when supported
    sendNotification({
      title: opts.title,
      body: opts.body,
      // extra data for deep link (plugin may pass through)
      ...(opts.path ? { extra: { path: opts.path } } : {}),
    } as any)

    // Also stash last deep-link for app resume
    if (opts.path) {
      sessionStorage.setItem('rm_notify_path', opts.path)
    }
    return true
  } catch {
    if ('Notification' in window && Notification.permission === 'granted') {
      const n = new Notification(opts.title, { body: opts.body, data: { path: opts.path } })
      if (opts.path) {
        n.onclick = () => {
          window.focus()
          window.location.hash = opts.path!
        }
      }
      return true
    }
    if ('Notification' in window && Notification.permission !== 'denied') {
      const p = await Notification.requestPermission()
      if (p === 'granted') {
        new Notification(opts.title, { body: opts.body })
        return true
      }
    }
    return false
  }
}

export function startNotificationPoll(intervalMs = 45000, navigate?: NavigateFn) {
  let lastIds = new Set<number>()
  let first = true

  // Handle pending deep link from notification click
  const pending = sessionStorage.getItem('rm_notify_path')
  if (pending && navigate) {
    sessionStorage.removeItem('rm_notify_path')
    setTimeout(() => navigate(pending), 300)
  }

  const tick = async () => {
    try {
      const { api } = await import('./api')
      const list = await api.listNotifications(true)
      for (const n of list) {
        if (!first && !lastIds.has(n.id)) {
          const agentId = n.agent_id || (n.data as any)?.agent_id
          const path = agentId ? `/agents/${agentId}` : '/history'
          await showNativeNotification({
            title: n.title,
            body: n.body || '',
            path,
          })
        }
        lastIds.add(n.id)
      }
      first = false
    } catch {
      // offline
    }
  }

  tick()
  return setInterval(tick, intervalMs)
}
