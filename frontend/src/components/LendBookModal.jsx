import { useState, useEffect } from 'react'
import { lendBookApi } from '../api/lending'

/**
 * LendBookModal Component
 * Allows an owner to lend a book to another registered BookNest user by email.
 * Includes email validation, loading states, error handling (400/404/409), and confirmation.
 */
export default function LendBookModal({
  isOpen,
  onClose,
  book,
  onLendSuccess,
}) {
  const [borrowerEmail, setBorrowerEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (isOpen) {
      setBorrowerEmail('')
      setErrorMsg('')
      setLoading(false)
    }
  }, [isOpen])

  if (!isOpen || !book) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    const trimmed = borrowerEmail.trim().toLowerCase()
    if (!trimmed || !trimmed.includes('@')) {
      setErrorMsg('Please enter a valid email address.')
      return
    }

    setLoading(true)
    setErrorMsg('')
    try {
      const lending = await lendBookApi({
        book_id: book.id,
        borrower_email: trimmed,
      })
      if (onLendSuccess) {
        onLendSuccess(lending)
      }
      onClose()
    } catch (err) {
      console.error('Failed to lend book:', err)
      const detail =
        err.response?.data?.detail || 'Failed to lend book. Please try again.'
      setErrorMsg(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 'var(--space-md)',
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '480px',
          background: 'var(--bg-card)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)',
          border: '1px solid var(--border-color)',
          padding: 'var(--space-xl)',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--space-lg)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <span style={{ fontSize: '1.5rem' }}>🤝</span>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>
              Lend Book
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '1.5rem',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            &times;
          </button>
        </div>

        {/* Book Info Summary */}
        <div
          style={{
            padding: 'var(--space-md)',
            background: 'var(--bg-dark)',
            borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--space-lg)',
            borderLeft: '4px solid var(--accent)',
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 'var(--font-size-md)', color: 'var(--text-primary)' }}>
            {book.title}
          </div>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
            by {book.author}
          </div>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid var(--danger)',
              color: 'var(--danger)',
              fontSize: 'var(--font-size-sm)',
              marginBottom: 'var(--space-md)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span>⚠️</span>
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div>
            <label
              htmlFor="borrowerEmail"
              style={{
                display: 'block',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: 'var(--space-xs)',
              }}
            >
              Borrower Email Address
            </label>
            <input
              id="borrowerEmail"
              type="email"
              value={borrowerEmail}
              onChange={(e) => setBorrowerEmail(e.target.value)}
              placeholder="reader@example.com"
              required
              disabled={loading}
              className="input"
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input, #1e2130)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: 'var(--font-size-sm)',
              }}
            />
            <small style={{ display: 'block', marginTop: '6px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
              The borrower must have an active registered account on BookNest. They will receive read-only access to this book.
            </small>
          </div>

          {/* Action Buttons */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 'var(--space-sm)',
              marginTop: 'var(--space-sm)',
            }}
          >
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={loading}
              style={{ padding: '8px 16px' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
              style={{
                padding: '8px 20px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontWeight: 600,
              }}
            >
              {loading ? (
                <>
                  <span className="spinner" style={{ width: '14px', height: '14px' }} />
                  Lending...
                </>
              ) : (
                'Confirm Loan'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
