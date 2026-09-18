export default function BookCard({ book, onEdit, onDelete, onQuickProgress }) {
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
    const next = Math.min(
      book.total_pages ? book.total_pages : book.current_page + 10,
      book.current_page + 10
    )
    const isNowFinished = book.total_pages && next >= book.total_pages
    onQuickProgress(book.id, {
      current_page: next,
      status: isNowFinished ? 'finished' : book.status === 'want_to_read' ? 'reading' : book.status,
    })
  }

  const handleMarkFinished = () => {
    onQuickProgress(book.id, {
      status: 'finished',
      current_page: book.total_pages || book.current_page,
    })
  }

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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-sm)', marginBottom: 'var(--space-xs)' }}>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginBottom: '4px' }}>
            <span>
              Page {book.current_page}
              {book.total_pages ? ` of ${book.total_pages}` : ''}
            </span>
            {book.progress_percentage !== null && <span>{book.progress_percentage}%</span>}
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
        {/* Quick Progress Buttons (when reading or want to read) */}
        {book.status !== 'finished' && (
          <div style={{ display: 'flex', gap: 'var(--space-xs)', marginBottom: 'var(--space-xs)' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleAdvance10}
              style={{ flex: 1, padding: '4px 8px', fontSize: 'var(--font-size-xs)' }}
              title="Add 10 pages to progress"
            >
              +10 Pages
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleMarkFinished}
              style={{ flex: 1, padding: '4px 8px', fontSize: 'var(--font-size-xs)', color: 'var(--success)' }}
              title="Mark book as finished"
            >
              ✓ Finished
            </button>
          </div>
        )}

        {/* Edit and Delete Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-sm)' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => onEdit(book)}
            style={{ padding: '4px 10px', fontSize: 'var(--font-size-xs)' }}
          >
            Edit
          </button>
          <button
            type="button"
            className="btn-danger"
            onClick={() => onDelete(book.id, book.title)}
            style={{ padding: '4px 10px', fontSize: 'var(--font-size-xs)' }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
