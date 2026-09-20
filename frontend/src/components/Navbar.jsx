import { useAuth } from '../context/AuthContext'
import { useSocketContext } from '../context/SocketContext'

/**
 * Top navigation bar component displaying application brand,
 * authenticated user profile summary, real-time connection status, and logout button.
 */
export default function Navbar() {
  const { user, logout } = useAuth()
  const { isConnected } = useSocketContext()

  return (
    <header
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 'var(--space-2xl)',
        paddingBottom: 'var(--space-md)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
        <span style={{ fontSize: '1.75rem' }}>📚</span>
        <span style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>BookNest</span>
        <span
          id="realtime-status-badge"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: '12px',
            marginLeft: '8px',
            backgroundColor: isConnected ? 'rgba(34, 197, 94, 0.15)' : 'rgba(156, 163, 175, 0.15)',
            color: isConnected ? '#16a34a' : '#9ca3af',
            border: `1px solid ${isConnected ? 'rgba(34, 197, 94, 0.3)' : 'rgba(156, 163, 175, 0.3)'}`,
            transition: 'all 0.3s ease',
          }}
          title={isConnected ? 'Connected to real-time events server' : 'Disconnected from real-time events server'}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isConnected ? '#22c55e' : '#9ca3af',
              boxShadow: isConnected ? '0 0 6px #22c55e' : 'none',
            }}
          />
          {isConnected ? 'Live' : 'Offline'}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Signed in as <strong>{user?.name}</strong>
        </span>
        <button
          className="btn-secondary"
          onClick={logout}
          style={{ fontSize: 'var(--font-size-xs)' }}
        >
          Log Out
        </button>
      </div>
    </header>
  )
}
