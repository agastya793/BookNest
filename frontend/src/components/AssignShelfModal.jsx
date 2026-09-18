import { useState, useEffect } from 'react'
import { addBookToShelfApi, removeBookFromShelfApi } from '../api/shelves'

/**
 * AssignShelfModal Component
 * Allows assigning a book to multiple custom shelves or removing it from shelves.
 * Handles duplicate associations gracefully and keeps state in sync.
 */
export default function AssignShelfModal({
  isOpen,
  onClose,
  book,
  shelves = [],
  onAssignedChange,
}) {
  const [assignedShelfIds, setAssignedShelfIds] = useState(new Set())
  const [loadingShelfId, setLoadingShelfId] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  // Initialize assigned shelf IDs from book.shelf_ids
  useEffect(() => {
    if (book && isOpen) {
      setAssignedShelfIds(new Set(book.shelf_ids || []))
      setErrorMsg('')
    }
  }, [book, isOpen])

  if (!isOpen || !book) return null

  const handleToggleShelf = async (shelfId) => {
    setLoadingShelfId(shelfId)
    setErrorMsg('')
    const isCurrentlyAssigned = assignedShelfIds.has(shelfId)

    try {
      if (isCurrentlyAssigned) {
        // Remove book from shelf
        await removeBookFromShelfApi(shelfId, book.id)
        setAssignedShelfIds((prev) => {
          const next = new Set(prev)
          next.delete(shelfId)
          return next
        })
      } else {
        // Add book to shelf
        await addBookToShelfApi(shelfId, book.id)
        setAssignedShelfIds((prev) => {
          const next = new Set(prev)
          next.add(shelfId)
          return next
        })
      }
      // Notify parent to refresh books & shelves
      if (onAssignedChange) {
        await onAssignedChange()
      }
    } catch (err) {
      if (err.response?.status === 409) {
        // Already on shelf race condition - ensure marked as assigned
        setAssignedShelfIds((prev) => new Set([...prev, shelfId]))
        setErrorMsg('Book is already on this shelf.')
      } else {
        setErrorMsg(
          err.response?.data?.detail || err.message || 'Failed to update shelf assignment.'
        )
      }
    } finally {
      setLoadingShelfId(null)
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
        if (e.target === e.currentTarget && !loadingShelfId) onClose()
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '480px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
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
            paddingBottom: 'var(--space-sm)',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600 }}>Manage Shelves</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', marginTop: '2px' }}>
              Assign <strong>"{book.title}"</strong> to your custom shelves
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loadingShelfId !== null}
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

        {/* Error Alert */}
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

        {/* Shelves List */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-sm)',
            margin: 'var(--space-sm) 0 var(--space-lg) 0',
            maxHeight: '340px',
          }}
        >
          {shelves.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: 'var(--space-xl)',
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              <div style={{ fontSize: '2rem', marginBottom: 'var(--space-xs)' }}>📂</div>
              You don't have any custom shelves yet.
              <br />
              Create your first shelf from the sidebar on the left.
            </div>
          ) : (
            shelves.map((shelf) => {
              const isAssigned = assignedShelfIds.has(shelf.id)
              const isLoading = loadingShelfId === shelf.id

              return (
                <label
                  key={shelf.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: isAssigned ? 'var(--accent-light)' : 'var(--bg-secondary)',
                    border: isAssigned ? '1px solid var(--accent)' : '1px solid var(--border)',
                    cursor: isLoading ? 'wait' : 'pointer',
                    transition: 'all var(--transition-fast)',
                    userSelect: 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                    <input
                      type="checkbox"
                      checked={isAssigned}
                      disabled={isLoading}
                      onChange={() => handleToggleShelf(shelf.id)}
                      style={{
                        width: '18px',
                        height: '18px',
                        accentColor: 'var(--accent)',
                        cursor: 'pointer',
                      }}
                    />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
                        {shelf.name}
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
                        {shelf.book_count} {shelf.book_count === 1 ? 'book' : 'books'} currently on shelf
                      </div>
                    </div>
                  </div>

                  <div>
                    {isLoading ? (
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                        Saving...
                      </span>
                    ) : isAssigned ? (
                      <span className="badge badge-accent">On Shelf</span>
                    ) : (
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                        Click to add
                      </span>
                    )}
                  </div>
                </label>
              )
            })
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderTop: '1px solid var(--border)',
            paddingTop: 'var(--space-md)',
          }}
        >
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            Books can belong to multiple shelves simultaneously.
          </span>
          <button
            type="button"
            className="btn-primary"
            onClick={onClose}
            disabled={loadingShelfId !== null}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
