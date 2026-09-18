import { useAuth } from '../context/AuthContext'

/**
 * Top navigation bar component displaying application brand,
 * authenticated user profile summary, and logout button.
 */
export default function Navbar() {
  const { user, logout } = useAuth()

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
        <span className="badge badge-accent" style={{ marginLeft: '8px' }}>
          Phase 2 Verified
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
