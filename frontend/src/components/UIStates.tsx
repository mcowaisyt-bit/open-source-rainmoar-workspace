export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-zinc-500 animate-fade-in">
      <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin mb-3" />
      <div className="text-sm">{label}</div>
    </div>
  )
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}) {
  return (
    <div className="card text-center py-12 px-6 animate-fade-in">
      <div className="text-2xl mb-3 opacity-50">⚡</div>
      <h3 className="font-medium text-zinc-200 mb-1">{title}</h3>
      {description && <p className="text-sm text-zinc-500 mb-4 max-w-sm mx-auto">{description}</p>}
      {actionLabel && onAction && (
        <button className="btn-primary text-sm" onClick={onAction}>{actionLabel}</button>
      )}
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="card text-center py-10 px-6 border-red-500/20 animate-fade-in">
      <div className="text-red-400 text-sm mb-3">{message}</div>
      {onRetry && (
        <button className="btn-secondary text-xs" onClick={onRetry}>TRY AGAIN</button>
      )}
    </div>
  )
}
