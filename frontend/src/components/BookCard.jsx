/**
 * BookCard Component
 * Displays book information, reading progress, rating, shelf tags,
 * quick progress actions, shelf assignment manager, and deletion.
 */
export default function BookCard({
  book,
  onEdit,
  onDelete,
  onQuickProgress,
  onUpdateProgress,
  onManageShelves,
  currentShelf = null,
  onRemoveFromShelf = null,
  shelvesMap = {},
  onLend = null,
  onReturn = null,
  onViewLendingHistory = null,
  isBorrowed = false,
}) {
  const getStatusBadge = (status) => {
    switch (status) {
      case 'reading':
        return <span className="badge badge-accent">Reading</span>
      case 'finished':
        return <span className="badge badge-success">Finished</span>
      case 'want_to_read':
      default:
        return <span className="badge badge-info">Want to Read</span>
    }
  }

  const renderRatingStars = (rating) => {
    if (!rating) return <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Unrated</span>
    const stars = []
    for (let i = 1; i <= 5; i++) {
      stars.push(
        <span
          key={i}
          style={{
            color: i <= rating ? 'var(--warning)' : 'var(--text-muted)',
            fontSize: '1rem',
          }}
        >
          {i <= rating ? '★' : '☆'}
        </span>
      )
    }
    return <div style={{ display: 'inline-flex', gap: '2px' }}>{stars}</div>
  }

  const handleAdvance10 = () => {
    const next = book.total_pages
      ? Math.min(book.total_pages, book.current_page + 10)
      : book.current_page + 10
    if (onQuickProgress) {
      onQuickProgress(book.id, { current_page: next })
    }
  }

  const handleMarkFinished = () => {
    if (onQuickProgress) {
      onQuickProgress(book.id, {
        current_page: book.total_pages || book.current_page,
      })
    }
  }

  // Find names of shelves this book is currently assigned to
  const assignedShelfNames = (book.shelf_ids || [])
    .map((shelfId) => shelvesMap[shelfId])
    .filter(Boolean)

  return (
    <div
      className="card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: 'var(--space-md)',
        position: 'relative',
      }}
    >
      {/* Card Header: Title, Author, and Status Badge */}
      <div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: 'var(--space-sm)',
            marginBottom: 'var(--space-xs)',
          }}
        >
          <h3
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 600,
              lineHeight: 1.3,
              wordBreak: 'break-word',
            }}
          >
            {book.title}
          </h3>
          <div style={{ flexShrink: 0 }}>{getStatusBadge(book.status)}</div>
        </div>

        <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-sm)' }}>
          by <strong>{book.author}</strong>
        </div>

        {/* Lending Status Badges */}
        {isBorrowed ? (
          <div style={{ marginBottom: 'var(--space-sm)' }}>
            <span
              className="badge badge-info"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.75rem',
                padding: '3px 8px',
              }}
            >
              📥 Borrowed from <strong>{book.lender_name || book.lender_email || 'Owner'}</strong>
            </span>
          </div>
        ) : book.is_lent ? (
          <div style={{ marginBottom: 'var(--space-sm)' }}>
            <span
              className="badge badge-warning"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.75rem',
                padding: '3px 8px',
                background: 'rgba(245, 158, 11, 0.15)',
                borderColor: 'var(--warning)',
                color: 'var(--warning)',
              }}
            >
              🤝 Lent to <strong>{book.borrower_name || 'Borrower'}</strong>
            </span>
          </div>
        ) : null}

        {/* Shelf Chips / Badges */}
        {assignedShelfNames.length > 0 && (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '4px',
              marginBottom: 'var(--space-sm)',
            }}
          >
            {assignedShelfNames.map((name, idx) => (
              <span
                key={idx}
                style={{
                  fontSize: '0.7rem',
                  padding: '2px 8px',
                  borderRadius: '100px',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px',
                }}
              >
                📁 {name}
              </span>
            ))}
          </div>
        )}

        {/* Rating and Finished Date */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
          <div>{renderRatingStars(book.rating)}</div>
          {book.status === 'finished' && book.finished_date && (
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
              Completed {new Date(book.finished_date).toLocaleDateString()}
            </span>
          )}
        </div>

        {/* Reading Progress */}
        <div style={{ marginTop: 'var(--space-sm)' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--text-secondary)',
              marginBottom: '4px',
            }}
          >
            <span>
              Page {book.current_page}
              {book.total_pages ? ` of ${book.total_pages}` : ''}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {book.total_pages && book.status !== 'finished' && book.total_pages > book.current_page && (
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  ({book.total_pages - book.current_page} left)
                </span>
              )}
              {book.progress_percentage !== null && (
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  {book.progress_percentage}%
                </span>
              )}
            </div>
          </div>

          {book.total_pages ? (
            <div
              style={{
                width: '100%',
                height: '7px',
                background: 'var(--bg-primary)',
                borderRadius: '100px',
                overflow: 'hidden',
                border: '1px solid var(--border)',
              }}
            >
              <div
                style={{
                  width: `${Math.min(100, Math.max(0, book.progress_percentage || 0))}%`,
                  height: '100%',
                  background:
                    book.status === 'finished'
                      ? 'var(--success)'
                      : 'linear-gradient(90deg, var(--accent) 0%, #a78bfa 100%)',
                  transition: 'width var(--transition-base)',
                }}
              />
            </div>
          ) : null}
        </div>

        {/* Notes Preview */}
        {book.notes && (
          <div
            style={{
              marginTop: 'var(--space-sm)',
              padding: 'var(--space-xs) var(--space-sm)',
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--text-secondary)',
              fontStyle: 'italic',
              maxHeight: '48px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            "{book.notes}"
          </div>
        )}
      </div>

      {/* Card Footer: Quick Actions & Options */}
      <div
        style={{
          borderTop: '1px solid var(--border)',
          paddingTop: 'var(--space-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-xs)',
        }}
      >
        {isBorrowed ? (
          /* Borrowed Book: Strictly Read-Only View (No owner controls) */
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              padding: '8px',
              background: 'var(--bg-dark)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-muted)',
              fontSize: 'var(--font-size-xs)',
              fontStyle: 'italic',
            }}
          >
            🔒 Read-only borrowed copy • Owner retains catalog controls
          </div>
        ) : (
          /* Owned Book: Full Owner Controls */
          <>
            {/* Quick Progress Buttons & Tracker Button */}
            {(onQuickProgress || onUpdateProgress) && (
              <div style={{ display: 'flex', gap: 'var(--space-xs)', marginBottom: 'var(--space-xs)' }}>
                {onUpdateProgress && (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => onUpdateProgress(book)}
                    style={{
                      flex: 1.2,
                      padding: '5px 8px',
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--accent)',
                      borderColor: 'rgba(147, 51, 234, 0.4)',
                      fontWeight: 600,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '4px',
                    }}
                    title="Update reading progress, pages, rating and notes"
                  >
                    <span>📈</span> Progress
                  </button>
                )}
                {onQuickProgress && book.status !== 'finished' && (
                  <>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={handleAdvance10}
                      style={{ flex: 1, padding: '5px 8px', fontSize: 'var(--font-size-xs)' }}
                      title="Add 10 pages to progress"
                    >
                      +10
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={handleMarkFinished}
                      style={{ flex: 1, padding: '5px 8px', fontSize: 'var(--font-size-xs)', color: 'var(--success)' }}
                      title="Mark book as finished"
                    >
                      ✓ Finish
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Peer Lending Actions Row */}
            <div style={{ display: 'flex', gap: 'var(--space-xs)', marginBottom: 'var(--space-xs)' }}>
              {book.is_lent ? (
                <>
                  {onReturn && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => onReturn(book)}
                      style={{
                        flex: 1,
                        padding: '5px 8px',
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--warning)',
                        borderColor: 'rgba(245, 158, 11, 0.4)',
                        fontWeight: 600,
                      }}
                      title="Mark this lent book as returned"
                    >
                      ↩ Mark Returned
                    </button>
                  )}
                  {onViewLendingHistory && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => onViewLendingHistory(book)}
                      style={{
                        padding: '5px 8px',
                        fontSize: 'var(--font-size-xs)',
                      }}
                      title="View loan history"
                    >
                      📜 History
                    </button>
                  )}
                </>
              ) : (
                <>
                  {onLend && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => onLend(book)}
                      style={{
                        flex: 1,
                        padding: '5px 8px',
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--accent)',
                        borderColor: 'rgba(139, 92, 246, 0.4)',
                        fontWeight: 600,
                      }}
                      title="Lend this book to a friend"
                    >
                      🤝 Lend Book
                    </button>
                  )}
                  {onViewLendingHistory && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => onViewLendingHistory(book)}
                      style={{
                        padding: '5px 8px',
                        fontSize: 'var(--font-size-xs)',
                      }}
                      title="View loan history"
                    >
                      📜 History
                    </button>
                  )}
                </>
              )}
            </div>

            {/* Contextual "Remove from Shelf" Button when viewing an active shelf */}
            {currentShelf && onRemoveFromShelf && currentShelf.role !== 'viewer' && (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => onRemoveFromShelf(currentShelf.id, book.id, book.title, currentShelf.name)}
                style={{
                  padding: '5px 10px',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--warning)',
                  borderColor: 'rgba(245, 158, 11, 0.3)',
                  marginBottom: 'var(--space-xs)',
                  justifyContent: 'center',
                }}
                title={`Remove "${book.title}" from "${currentShelf.name}" (keeps book in library)`}
              >
                ✕ Remove from "{currentShelf.name}"
              </button>
            )}

            {/* Manage Shelves, Edit, and Delete Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-xs)' }}>
              {/* Manage Shelves Button */}
              {onManageShelves ? (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => onManageShelves(book)}
                  style={{
                    padding: '4px 8px',
                    fontSize: 'var(--font-size-xs)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                  title="Assign book to custom shelves"
                >
                  <span>📁</span> Shelves
                </button>
              ) : <div />}

              {/* Edit and Delete Buttons */}
              <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
                {onEdit && (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => onEdit(book)}
                    style={{ padding: '4px 10px', fontSize: 'var(--font-size-xs)' }}
                  >
                    Edit
                  </button>
                )}
                {onDelete && (
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() => onDelete(book.id, book.title)}
                    style={{ padding: '4px 10px', fontSize: 'var(--font-size-xs)' }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
