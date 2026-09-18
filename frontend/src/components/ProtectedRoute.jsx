import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Route protection component using React Router.
 * Displays loading indicator while AuthContext initializes,
 * redirects unauthenticated users to /login via <Navigate to="/login" replace />,
 * and renders authenticated children or nested <Outlet />.
 */
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 'var(--space-md)',
        }}
      >
        <div style={{ fontSize: '2.5rem' }}>📚</div>
        <p style={{ color: 'var(--text-secondary)' }}>Loading BookNest session...</p>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children ? children : <Outlet />
}
