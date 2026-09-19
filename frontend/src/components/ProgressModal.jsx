import { useState, useEffect } from 'react'

/**
 * ProgressModal Component
 * Interactive modal for tracking reading progress with range slider scrubber,
 * milestone indicators, quick steppers, and reflection notes.
 */
export default function ProgressModal({ isOpen, onClose, book, onSaveProgress }) {
  const [currentPage, setCurrentPage] = useState(0)
  const [notes, setNotes] = useState('')
  const [rating, setRating] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (book) {
      setCurrentPage(book.current_page ?? 0)
      setNotes(book.notes || '')
      setRating(book.rating ?? null)
    }
    setErrorMsg('')
  }, [book, isOpen])

  if (!isOpen || !book) return null

  const totalPages = book.total_pages
  const hasTotalPages = totalPages !== null && totalPages !== undefined && totalPages > 0

  const pct = hasTotalPages
    ? Math.round(((currentPage / totalPages) * 100) * 10) / 10
    : null
  const pagesRemaining = hasTotalPages ? Math.max(0, totalPages - currentPage) : null

  // Milestone preview badge
  let milestoneBadge = null
  if (pct !== null) {
    if (pct >= 100) {
      milestoneBadge = { label: '🏆 Completed (100%)', color: 'var(--success)', bg: 'var(--success-bg)' }
    } else if (pct >= 75) {
      milestoneBadge = { label: '🔥 Final Stretch (75%+)', color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)' }
    } else if (pct >= 50) {
      milestoneBadge = { label: '⚡ Halfway Mark (50%+)', color: 'var(--warning)', bg: 'var(--warning-bg)' }
    } else if (pct >= 25) {
      milestoneBadge = { label: '🌱 Good Momentum (25%+)', color: 'var(--info)', bg: 'var(--info-bg)' }
    }
  }

  const handleStep = (delta) => {
    setCurrentPage((prev) => {
      const next = prev + delta
      const clampedMin = Math.max(0, next)
      return hasTotalPages ? Math.min(totalPages, clampedMin) : clampedMin
    })
  }

  const handleSetMax = () => {
    if (hasTotalPages) {
      setCurrentPage(totalPages)
    }
  }

  const handleSetZero = () => {
    setCurrentPage(0)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMsg('')

    if (currentPage < 0) {
      setErrorMsg('Page number cannot be negative.')
      return
    }

    if (hasTotalPages && currentPage > totalPages) {
      setErrorMsg(`Current page (${currentPage}) cannot exceed total pages (${totalPages}).`)
      return
    }

    setSubmitting(true)
    try {
      await onSaveProgress(book.id, {
        current_page: currentPage,
        notes: notes.trim() || null,
        rating: rating,
      })
      onClose()
    } catch (err) {
      const detail = err.response?.data?.detail
      let formattedMsg = 'Failed to update progress.'
      if (typeof detail === 'string') {
        formattedMsg = detail
      } else if (Array.isArray(detail)) {
        formattedMsg = detail.map((d) => d.msg || JSON.stringify(d)).join(', ')
      } else if (err.message) {
        formattedMsg = err.message
      }
      setErrorMsg(formattedMsg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 'var(--space-md)',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '520px',
          maxHeight: '92vh',
          overflowY: 'auto',
          boxShadow: 'var(--shadow-lg)',
          padding: 'var(--space-xl)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: 'var(--space-md)',
          }}
        >
          <div>
            <span
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--accent)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Update Reading Progress
            </span>
            <h2
              style={{
                fontSize: 'var(--font-size-xl)',
                fontWeight: 700,
                color: 'var(--text-primary)',
                marginTop: '2px',
                lineHeight: 1.3,
              }}
            >
              {book.title}
            </h2>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
              by <strong>{book.author}</strong>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '1.4rem',
              cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            &times;
          </button>
        </div>

        {errorMsg && (
          <div
            style={{
              background: 'var(--error-bg)',
              color: 'var(--error)',
              padding: 'var(--space-sm) var(--space-md)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-md)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
          {/* Progress Status Hero */}
          <div
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-md)',
              textAlign: 'center',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'baseline', gap: '6px' }}>
              <span style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>
                {currentPage}
              </span>
              {hasTotalPages && (
                <span style={{ fontSize: 'var(--font-size-md)', color: 'var(--text-muted)' }}>
                  / {totalPages} pages
                </span>
              )}
            </div>

            {hasTotalPages && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--text-secondary)',
                  marginTop: 'var(--space-xs)',
                }}
              >
                <span>{pct}% completed</span>
                <span>{pagesRemaining === 0 ? 'Finished!' : `${pagesRemaining} pages remaining`}</span>
              </div>
            )}

            {/* Visual Progress Bar with Milestones */}
            {hasTotalPages && (
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  height: '10px',
                  background: 'var(--bg-primary)',
                  borderRadius: '100px',
                  marginTop: 'var(--space-sm)',
                  overflow: 'hidden',
                  border: '1px solid var(--border)',
                }}
              >
                <div
                  style={{
                    width: `${Math.min(100, Math.max(0, pct || 0))}%`,
                    height: '100%',
                    background:
                      pct >= 100
                        ? 'var(--success)'
                        : 'linear-gradient(90deg, var(--accent) 0%, #38bdf8 100%)',
                    transition: 'width 100ms ease',
                  }}
                />
              </div>
            )}

            {/* Milestone Badge if hit */}
            {milestoneBadge && (
              <div style={{ marginTop: 'var(--space-sm)' }}>
                <span
                  style={{
                    display: 'inline-block',
                    padding: '3px 10px',
                    borderRadius: '100px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    background: milestoneBadge.bg,
                    color: milestoneBadge.color,
                    border: `1px solid ${milestoneBadge.color}`,
                  }}
                >
                  {milestoneBadge.label}
                </span>
              </div>
            )}
          </div>

          {/* Scrubber Slider */}
          {hasTotalPages && (
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: 'var(--space-xs)',
                }}
              >
                Drag to adjust page:
              </label>
              <input
                type="range"
                min="0"
                max={totalPages}
                value={currentPage}
                onChange={(e) => setCurrentPage(parseInt(e.target.value, 10))}
                style={{
                  width: '100%',
                  accentColor: 'var(--accent)',
                  cursor: 'pointer',
                }}
              />
            </div>
          )}

          {/* Quick Stepper Buttons */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: 'var(--space-xs)',
              }}
            >
              Quick Page Adjustments:
            </label>
            <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleStep(-10)}
                style={{ flex: 1, minWidth: '45px', padding: '6px 4px', fontSize: 'var(--font-size-xs)' }}
                title="Subtract 10 pages"
              >
                -10
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleStep(-1)}
                style={{ flex: 1, minWidth: '45px', padding: '6px 4px', fontSize: 'var(--font-size-xs)' }}
                title="Subtract 1 page"
              >
                -1
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleStep(1)}
                style={{ flex: 1, minWidth: '45px', padding: '6px 4px', fontSize: 'var(--font-size-xs)' }}
                title="Add 1 page"
              >
                +1
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleStep(10)}
                style={{ flex: 1, minWidth: '45px', padding: '6px 4px', fontSize: 'var(--font-size-xs)' }}
                title="Add 10 pages"
              >
                +10
              </button>
              {hasTotalPages && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleSetMax}
                  style={{
                    flex: 1.2,
                    minWidth: '60px',
                    padding: '6px 4px',
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--success)',
                  }}
                  title="Mark as finished"
                >
                  ✓ Finish
                </button>
              )}
            </div>
          </div>

          {/* Direct Numeric Input */}
          <div>
            <label
              htmlFor="current-page-input"
              style={{
                display: 'block',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: 'var(--space-xs)',
              }}
            >
              Exact Page Number:
            </label>
            <input
              id="current-page-input"
              type="number"
              min="0"
              max={hasTotalPages ? totalPages : undefined}
              value={currentPage}
              onChange={(e) => {
                const val = e.target.value === '' ? 0 : parseInt(e.target.value, 10)
                setCurrentPage(isNaN(val) ? 0 : val)
              }}
              style={{
                width: '100%',
                padding: 'var(--space-sm) var(--space-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                fontSize: 'var(--font-size-md)',
              }}
            />
          </div>

          {/* Reading Reflection / Notes */}
          <div>
            <label
              htmlFor="progress-notes-input"
              style={{
                display: 'block',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: 'var(--space-xs)',
              }}
            >
              Reading Reflection or Note (optional):
            </label>
            <textarea
              id="progress-notes-input"
              rows="2"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Jot down a quick thought, favorite quote, or reflection..."
              style={{
                width: '100%',
                padding: 'var(--space-sm) var(--space-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                fontSize: 'var(--font-size-sm)',
                resize: 'vertical',
              }}
            />
          </div>

          {/* Rating (optional) */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: 'var(--space-xs)',
              }}
            >
              Rating (optional):
            </label>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(rating === star ? null : star)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    fontSize: '1.5rem',
                    cursor: 'pointer',
                    color: star <= (rating || 0) ? 'var(--warning)' : 'var(--text-muted)',
                    padding: '2px',
                    transition: 'transform 100ms ease',
                  }}
                  title={`Rate ${star} star${star > 1 ? 's' : ''}`}
                >
                  ★
                </button>
              ))}
              {rating && (
                <button
                  type="button"
                  onClick={() => setRating(null)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: 'var(--font-size-xs)',
                    cursor: 'pointer',
                    marginLeft: 'var(--space-xs)',
                    textDecoration: 'underline',
                  }}
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Actions */}
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
              disabled={submitting}
              style={{ padding: 'var(--space-sm) var(--space-lg)' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting}
              style={{ padding: 'var(--space-sm) var(--space-lg)' }}
            >
              {submitting ? 'Saving...' : 'Save Progress'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
