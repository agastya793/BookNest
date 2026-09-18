import { useState, useEffect } from 'react'

export default function BookModal({ isOpen, onClose, onSave, book = null }) {
  const isEditing = !!book

  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [status, setStatus] = useState('want_to_read')
  const [totalPages, setTotalPages] = useState('')
  const [currentPage, setCurrentPage] = useState('0')
  const [rating, setRating] = useState('')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  // Sync state when editing an existing book or resetting for a new book
  useEffect(() => {
    if (book) {
      setTitle(book.title || '')
      setAuthor(book.author || '')
      setStatus(book.status || 'want_to_read')
      setTotalPages(book.total_pages ? String(book.total_pages) : '')
      setCurrentPage(String(book.current_page ?? 0))
      setRating(book.rating ? String(book.rating) : '')
      setNotes(book.notes || '')
    } else {
      setTitle('')
      setAuthor('')
      setStatus('want_to_read')
      setTotalPages('')
      setCurrentPage('0')
      setRating('')
      setNotes('')
    }
    setErrorMsg('')
  }, [book, isOpen])

  if (!isOpen) return null

  // Cross-field page validation
  const numTotal = totalPages !== '' ? parseInt(totalPages, 10) : null
  const numCurrent = currentPage !== '' ? parseInt(currentPage, 10) : 0
  const isPageInvalid = numTotal !== null && numCurrent > numTotal

  const handleStatusChange = (newStatus) => {
    setStatus(newStatus)
    // If marking finished and totalPages is known, automatically complete pages
    if (newStatus === 'finished' && numTotal !== null && numCurrent === 0) {
      setCurrentPage(String(numTotal))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMsg('')

    if (!title.trim() || !author.trim()) {
      setErrorMsg('Title and Author are required.')
      return
    }

    if (isPageInvalid) {
      setErrorMsg(`Current page (${numCurrent}) cannot exceed total pages (${numTotal}).`)
      return
    }

    const payload = {
      title: title.trim(),
      author: author.trim(),
      status,
      total_pages: numTotal,
      current_page: numCurrent,
      rating: rating ? parseInt(rating, 10) : null,
      notes: notes.trim() || null,
    }

    setSubmitting(true)
    try {
      await onSave(payload)
      onClose()
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to save book.')
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
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: 'var(--shadow-lg)',
          padding: 'var(--space-xl)',
        }}
      >
        {/* Modal Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-lg)' }}>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600 }}>
            {isEditing ? 'Edit Book' : 'Add New Book'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              color: 'var(--text-muted)',
              fontSize: '1.25rem',
              padding: '4px 8px',
            }}
          >
            ✕
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

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {/* Title */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 500, marginBottom: '4px' }}>
              Title *
            </label>
            <input
              type="text"
              placeholder="e.g. Clean Code"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              disabled={submitting}
            />
          </div>

          {/* Author */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 500, marginBottom: '4px' }}>
              Author *
            </label>
            <input
              type="text"
              placeholder="e.g. Robert C. Martin"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              required
              disabled={submitting}
            />
          </div>

          {/* Status and Rating Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
            <div>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 500, marginBottom: '4px' }}>
                Reading Status
              </label>
              <select
                value={status}
                onChange={(e) => handleStatusChange(e.target.value)}
                disabled={submitting}
              >
                <option value="want_to_read">Want to Read</option>
                <option value="reading">Currently Reading</option>
                <option value="finished">Finished</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 500, marginBottom: '4px' }}>
                Rating
              </label>
              <select
                value={rating}
                onChange={(e) => setRating(e.target.value)}
                disabled={submitting}
              >
                <option value="">Unrated</option>
                <option value="5">★★★★★ (5 stars)</option>
                <option value="4">★★★★☆ (4 stars)</option>
                <option value="3">★★★☆☆ (3 stars)</option>
                <option value="2">★★☆☆☆ (2 stars)</option>
                <option value="1">★☆☆☆☆ (1 star)</option>
              </select>
            </div>
          </div>

          {/* Page Boundaries Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
            <div>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 500, marginBottom: '4px' }}>
                Current Page
              </label>
              <input
                type="number"
                min="0"
                placeholder="0"
                value={currentPage}
                onChange={(e) => setCurrentPage(e.target.value)}
                disabled={submitting}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 500, marginBottom: '4px' }}>
                Total Pages (Optional)
              </label>
              <input
                type="number"
                min="1"
                placeholder="e.g. 350"
                value={totalPages}
                onChange={(e) => setTotalPages(e.target.value)}
                disabled={submitting}
              />
            </div>
          </div>

          {/* Real-time page boundary warning */}
          {isPageInvalid && (
            <div style={{ color: 'var(--error)', fontSize: 'var(--font-size-xs)' }}>
              ⚠️ Current page ({numCurrent}) cannot exceed total pages ({numTotal}).
            </div>
          )}

          {/* Notes */}
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 500, marginBottom: '4px' }}>
              Notes / Thoughts
            </label>
            <textarea
              rows={3}
              placeholder="What are your thoughts on this book?"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={submitting}
            />
          </div>

          {/* Modal Action Buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-sm)', marginTop: 'var(--space-sm)' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting || isPageInvalid}
            >
              {submitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Add Book'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
