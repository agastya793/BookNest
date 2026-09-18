import { useState, useEffect } from 'react'

/**
 * ShelfModal Component
 * Supports both creating a new shelf and renaming an existing shelf.
 * Handles whitespace validation and 409 duplicate name conflict errors inline.
 */
export default function ShelfModal({ isOpen, onClose, onSave, shelf = null }) {
  const isEditing = !!shelf
  const [name, setName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (shelf) {
      setName(shelf.name || '')
    } else {
      setName('')
    }
    setErrorMsg('')
  }, [shelf, isOpen])

  if (!isOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMsg('')

    const trimmed = name.trim()
    if (!trimmed) {
      setErrorMsg('Shelf name cannot be empty or whitespace only.')
      return
    }

    if (isEditing && trimmed === shelf.name) {
      onClose()
      return
    }

    setSubmitting(true)
    try {
      await onSave({ name: trimmed })
      onClose()
    } catch (err) {
      const detail = err.response?.data?.detail
      if (err.response?.status === 409) {
        setErrorMsg(detail || `Shelf "${trimmed}" already exists. Please choose a unique name.`)
      } else if (err.response?.status === 422) {
        setErrorMsg('Invalid shelf name. Please enter a valid name (1–100 characters).')
      } else {
        setErrorMsg(detail || err.message || 'Failed to save shelf.')
      }
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
        if (e.target === e.currentTarget && !submitting) onClose()
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '440px',
          boxShadow: 'var(--shadow-lg)',
          padding: 'var(--space-xl)',
        }}
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
            <span style={{ fontSize: '1.4rem' }}>{isEditing ? '✏️' : '📁'}</span>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600 }}>
              {isEditing ? 'Rename Shelf' : 'Create New Shelf'}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
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

        {/* Inline Error Alert */}
        {errorMsg && (
          <div
            style={{
              background: 'var(--error-bg)',
              color: 'var(--error)',
              padding: 'var(--space-sm) var(--space-md)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-md)',
              fontSize: 'var(--font-size-sm)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
            }}
          >
            ⚠️ {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div>
            <label
              htmlFor="shelf-name-input"
              style={{
                display: 'block',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 500,
                marginBottom: 'var(--space-xs)',
              }}
            >
              Shelf Name *
            </label>
            <input
              id="shelf-name-input"
              type="text"
              placeholder="e.g. Sci-Fi, Favorites, Summer 2026..."
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                if (errorMsg) setErrorMsg('')
              }}
              autoFocus
              maxLength={100}
              disabled={submitting}
              required
            />
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)', marginTop: '4px' }}>
              Shelf names must be unique to your account.
            </p>
          </div>

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
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting || !name.trim()}
            >
              {submitting ? 'Saving...' : isEditing ? 'Rename Shelf' : 'Create Shelf'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
