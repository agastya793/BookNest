import { useState, useMemo } from 'react'
import { Link, useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const SPECIAL_CHARS_REGEX = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/

export default function Signup() {
  const { signup, user } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  // If already authenticated, redirect to protected home
  if (user) {
    return <Navigate to="/" replace />
  }

  // Calculate password rule satisfaction dynamically
  const rules = useMemo(() => {
    const byteLength = new TextEncoder().encode(password).length
    return [
      { id: 'len', text: 'At least 8 characters', met: password.length >= 8 },
      {
        id: 'bytes',
        text: `At most 72 UTF-8 bytes (${byteLength}/72)`,
        met: password.length > 0 && byteLength <= 72,
        warning: byteLength > 72,
      },
      { id: 'upper', text: 'At least 1 uppercase letter (A-Z)', met: /[A-Z]/.test(password) },
      { id: 'lower', text: 'At least 1 lowercase letter (a-z)', met: /[a-z]/.test(password) },
      { id: 'digit', text: 'At least 1 numeric digit (0-9)', met: /\d/.test(password) },
      {
        id: 'special',
        text: 'At least 1 special character (!@#$%^&*...)',
        met: SPECIAL_CHARS_REGEX.test(password),
      },
    ]
  }, [password])

  const isPasswordValid = rules.every((r) => r.met)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMsg('')

    if (!name.trim()) {
      setErrorMsg('Please enter your name.')
      return
    }

    if (!isPasswordValid) {
      setErrorMsg('Please ensure your password meets all complexity requirements.')
      return
    }

    setLoading(true)
    try {
      await signup(name.trim(), email.trim(), password)
      navigate('/')
    } catch (err) {
      setErrorMsg(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.pageContainer}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.iconCircle}>📚</div>
          <h2 style={styles.title}>Join BookNest</h2>
          <p style={styles.subtitle}>Create your personal library account</p>
        </div>

        {errorMsg && (
          <div style={styles.errorAlert} role="alert">
            <span>⚠️ {errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formGroup}>
            <label htmlFor="signup-name" style={styles.label}>
              Full Name
            </label>
            <input
              id="signup-name"
              type="text"
              placeholder="Jane Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoComplete="name"
              disabled={loading}
            />
          </div>

          <div style={styles.formGroup}>
            <label htmlFor="signup-email" style={styles.label}>
              Email Address
            </label>
            <input
              id="signup-email"
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
              <label htmlFor="signup-password" style={styles.label}>
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
              id="signup-password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Create a strong password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              disabled={loading}
            />

            {/* Real-time interactive password checklist */}
            <div style={styles.rulesList}>
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  style={{
                    ...styles.ruleItem,
                    color: rule.met
                      ? 'var(--success)'
                      : rule.warning
                      ? 'var(--error)'
                      : 'var(--text-muted)',
                  }}
                >
                  <span>{rule.met ? '✓' : rule.warning ? '✗' : '○'}</span>
                  <span>{rule.text}</span>
                </div>
              ))}
            </div>
          </div>

          <button
            type="submit"
            className="btn-primary"
            style={styles.submitBtn}
            disabled={loading || (password.length > 0 && !isPasswordValid)}
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <div style={styles.footer}>
          <span style={{ color: 'var(--text-secondary)' }}>Already have an account?</span>{' '}
          <Link to="/login" style={styles.linkBtn}>
            Sign in here
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
    maxWidth: '460px',
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
  rulesList: {
    marginTop: 'var(--space-xs)',
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    gap: '3px',
  },
  ruleItem: {
    fontSize: 'var(--font-size-xs)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    transition: 'color var(--transition-fast)',
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
