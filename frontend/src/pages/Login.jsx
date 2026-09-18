import { useState } from 'react'
import { Link, useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  // If already authenticated, redirect to protected home
  if (user) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMsg('')

    if (!email.trim() || !password) {
      setErrorMsg('Please enter both email and password.')
      return
    }

    setLoading(true)
    try {
      await login(email.trim(), password)
      navigate('/')
    } catch (err) {
      setErrorMsg(err.message || 'Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.pageContainer}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.iconCircle}>📖</div>
          <h2 style={styles.title}>Welcome Back</h2>
          <p style={styles.subtitle}>Sign in to access your BookNest library</p>
        </div>

        {errorMsg && (
          <div style={styles.errorAlert} role="alert">
            <span>⚠️ {errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formGroup}>
            <label htmlFor="login-email" style={styles.label}>
              Email Address
            </label>
            <input
              id="login-email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              disabled={loading}
            />
          </div>

          <div style={styles.formGroup}>
            <div style={styles.labelRow}>
              <label htmlFor="login-password" style={styles.label}>
                Password
              </label>
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={styles.toggleBtn}
                tabIndex={-1}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            style={styles.submitBtn}
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div style={styles.footer}>
          <span style={{ color: 'var(--text-secondary)' }}>Don't have an account?</span>{' '}
          <Link to="/signup" style={styles.linkBtn}>
            Create an account
          </Link>
        </div>
      </div>
    </div>
  )
}

const styles = {
  pageContainer: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 'var(--space-xl) var(--space-md)',
  },
  card: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-xl)',
    padding: 'var(--space-2xl) var(--space-xl)',
    maxWidth: '440px',
    width: '100%',
    boxShadow: 'var(--shadow-lg)',
    margin: '0 auto',
  },
  header: {
    textAlign: 'center',
    marginBottom: 'var(--space-xl)',
  },
  iconCircle: {
    fontSize: '2rem',
    marginBottom: 'var(--space-sm)',
  },
  title: {
    fontSize: 'var(--font-size-2xl)',
    fontWeight: 700,
    marginBottom: 'var(--space-xs)',
  },
  subtitle: {
    color: 'var(--text-secondary)',
    fontSize: 'var(--font-size-sm)',
  },
  errorAlert: {
    background: 'var(--error-bg)',
    color: 'var(--error)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-sm) var(--space-md)',
    marginBottom: 'var(--space-lg)',
    fontSize: 'var(--font-size-sm)',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-lg)',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-xs)',
    textAlign: 'left',
  },
  labelRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    fontSize: 'var(--font-size-sm)',
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  toggleBtn: {
    background: 'transparent',
    color: 'var(--accent)',
    fontSize: 'var(--font-size-xs)',
    padding: 0,
    cursor: 'pointer',
  },
  submitBtn: {
    width: '100%',
    padding: 'var(--space-md)',
    fontSize: 'var(--font-size-base)',
    fontWeight: 600,
    marginTop: 'var(--space-xs)',
  },
  footer: {
    marginTop: 'var(--space-xl)',
    textAlign: 'center',
    fontSize: 'var(--font-size-sm)',
  },
  linkBtn: {
    color: 'var(--accent)',
    fontSize: 'var(--font-size-sm)',
    fontWeight: 600,
    padding: '0 4px',
    cursor: 'pointer',
    textDecoration: 'underline',
  },
}
