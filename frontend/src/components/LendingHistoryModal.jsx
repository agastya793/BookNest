import { useState, useEffect, useCallback } from 'react'
import { getBookLendingHistoryApi } from '../api/lending'

/**
 * LendingHistoryModal Component
 * Shows complete lending history for an owned book.
 */
export default function LendingHistoryModal({
  isOpen,
  onClose,
  book,
}) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const fetchHistory = useCallback(async () => {
    if (!book?.id) return
    setLoading(true)
    setErrorMsg('')
    try {
      const records = await getBookLendingHistoryApi(book.id)
      setHistory(records || [])
    } catch (err) {
      console.error('Failed to load lending history:', err)
      setErrorMsg(
        err.response?.data?.detail || 'Failed to load lending history.'
      )
    } finally {
      setLoading(false)
    }
  }, [book?.id])

  useEffect(() => {
    if (isOpen && book?.id) {
      fetchHistory()
    }
  }, [isOpen, book?.id, fetchHistory])

  if (!isOpen || !book) return null

  const formatDate = (isoString) => {
    if (!isoString) return '-'
    try {
      return new Date(isoString).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return isoString
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
          maxWidth: '560px',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-card)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
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
            marginBottom: 'var(--space-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <span style={{ fontSize: '1.5rem' }}>📜</span>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>
              Lending History
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
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
            padding: 'var(--space-sm) var(--space-md)',
            background: 'var(--bg-dark)',
            borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--space-md)',
          }}
        >
          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{book.title}</div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>by {book.author}</div>
        </div>

        {errorMsg && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.15)',
              color: 'var(--danger)',
              fontSize: 'var(--font-size-sm)',
              marginBottom: 'var(--space-md)',
            }}
          >
            {errorMsg}
          </div>
        )}

        {/* List Content */}
        <div style={{ overflowY: 'auto', flex: 1, paddingRight: '4px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-xl)', color: 'var(--text-muted)' }}>
              Loading lending history...
            </div>
          ) : history.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: 'var(--space-xl)',
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              This book has never been lent out yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
              {history.map((record) => (
                <div
                  key={record.id}
                  style={{
                    padding: 'var(--space-md)',
                    borderRadius: 'var(--radius-md)',
                    background: record.is_active ? 'rgba(245, 158, 11, 0.08)' : 'var(--bg-dark)',
                    border: record.is_active ? '1px solid var(--warning)' : '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
                        {record.borrower_name}
                      </span>
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                        ({record.borrower_email})
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Lent: <strong>{formatDate(record.lent_at)}</strong>
                      {record.returned_at && (
                        <span> • Returned: <strong>{formatDate(record.returned_at)}</strong></span>
                      )}
                    </div>
                  </div>
                  <div>
                    {record.is_active ? (
                      <span className="badge badge-warning" style={{ fontSize: '0.75rem' }}>
                        Active Loan
                      </span>
                    ) : (
                      <span className="badge badge-success" style={{ fontSize: '0.75rem' }}>
                        Returned
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-md)' }}>
          <button type="button" className="btn-secondary" onClick={onClose} style={{ padding: '8px 16px' }}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
