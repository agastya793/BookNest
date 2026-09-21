/**
 * DashboardSummary Component
 * Displays server-aggregated library statistics and collaborative metrics
 * required by BookNest Requirement #32.
 */
export default function DashboardSummary({ summary, loading, error }) {
  if (loading && !summary) {
    return (
      <div
        className="card"
        style={{
          padding: 'var(--space-lg)',
          marginBottom: 'var(--space-md)',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: 'var(--font-size-sm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 'var(--space-sm)',
        }}
      >
        <span>📊</span> Loading dashboard summary...
      </div>
    )
  }

  if (error) {
    return (
      <div
        className="card"
        style={{
          padding: 'var(--space-md) var(--space-lg)',
          marginBottom: 'var(--space-md)',
          background: 'var(--error-bg)',
          borderColor: 'var(--error)',
          color: 'var(--error)',
          fontSize: 'var(--font-size-sm)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-sm)',
        }}
      >
        <span>⚠️</span>
        <span>{error}</span>
      </div>
    )
  }

  const {
    status_counts = { want_to_read: 0, reading: 0, finished: 0 },
    books_finished_this_year = 0,
    average_rating = 0.0,
    shelf_with_most_books = null,
    books_currently_lent_out = 0,
    shelves_shared_with_me = 0,
  } = summary || {}

  const currentYear = new Date().getFullYear()

  return (
    <div
      className="dashboard-summary-container"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md)',
        marginBottom: 'var(--space-md)',
      }}
      id="dashboard-summary-section"
    >
      {/* Metrics Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 'var(--space-md)',
        }}
      >
        {/* 1. Status Counts: Reading, Want to Read, Finished */}
        <div
          className="card"
          style={{
            padding: 'var(--space-md) var(--space-lg)',
            background: 'var(--bg-card)',
            borderLeft: '4px solid var(--accent)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
          id="summary-status-counts-card"
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Reading Status
            </span>
            <span style={{ fontSize: '1.2rem' }}>📚</span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '6px',
              marginTop: '4px',
            }}
          >
            {/* Reading */}
            <div style={{ textAlign: 'center', flex: 1 }}>
              <div
                style={{
                  fontSize: '1.35rem',
                  fontWeight: 700,
                  color: 'var(--warning)',
                  lineHeight: 1.1,
                }}
                id="summary-count-reading"
              >
                {status_counts.reading}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Reading
              </div>
            </div>

            <div style={{ width: '1px', height: '24px', background: 'var(--border)' }} />

            {/* Want to Read */}
            <div style={{ textAlign: 'center', flex: 1 }}>
              <div
                style={{
                  fontSize: '1.35rem',
                  fontWeight: 700,
                  color: 'var(--info)',
                  lineHeight: 1.1,
                }}
                id="summary-count-want-to-read"
              >
                {status_counts.want_to_read}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Want to Read
              </div>
            </div>

            <div style={{ width: '1px', height: '24px', background: 'var(--border)' }} />

            {/* Finished */}
            <div style={{ textAlign: 'center', flex: 1 }}>
              <div
                style={{
                  fontSize: '1.35rem',
                  fontWeight: 700,
                  color: 'var(--success)',
                  lineHeight: 1.1,
                }}
                id="summary-count-finished"
              >
                {status_counts.finished}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Finished
              </div>
            </div>
          </div>
        </div>

        {/* 2. Finished This Year */}
        <div
          className="card"
          style={{
            padding: 'var(--space-md) var(--space-lg)',
            background: 'var(--bg-card)',
            borderLeft: '4px solid var(--success)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}
          id="summary-finished-this-year-card"
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--success-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
              flexShrink: 0,
            }}
          >
            🏆
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Finished This Year
            </div>
            <div
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1.2,
                marginTop: '2px',
              }}
              id="summary-finished-this-year-val"
            >
              {books_finished_this_year}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              In calendar year {currentYear}
            </div>
          </div>
        </div>

        {/* 3. Average Rating */}
        <div
          className="card"
          style={{
            padding: 'var(--space-md) var(--space-lg)',
            background: 'var(--bg-card)',
            borderLeft: '4px solid #f59e0b',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}
          id="summary-average-rating-card"
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(245, 158, 11, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
              flexShrink: 0,
            }}
          >
            ⭐
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Average Rating
            </div>
            <div
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1.2,
                marginTop: '2px',
                display: 'flex',
                alignItems: 'baseline',
                gap: '4px',
              }}
              id="summary-average-rating-val"
            >
              {average_rating > 0 ? (
                <>
                  <span>{average_rating.toFixed(1)}</span>
                  <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', fontWeight: 500 }}>
                    / 5.0
                  </span>
                </>
              ) : (
                <span style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                  No ratings yet
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              From rated library books
            </div>
          </div>
        </div>

        {/* 4. Shelf With Most Books */}
        <div
          className="card"
          style={{
            padding: 'var(--space-md) var(--space-lg)',
            background: 'var(--bg-card)',
            borderLeft: '4px solid #8b5cf6',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}
          id="summary-top-shelf-card"
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(139, 92, 246, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
              flexShrink: 0,
            }}
          >
            📁
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Top Shelf
            </div>
            {shelf_with_most_books ? (
              <>
                <div
                  style={{
                    fontSize: '1.15rem',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    lineHeight: 1.2,
                    marginTop: '2px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={shelf_with_most_books.name}
                  id="summary-top-shelf-name"
                >
                  {shelf_with_most_books.name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  <span className="badge badge-accent" style={{ fontSize: '0.7rem', padding: '1px 6px' }}>
                    {shelf_with_most_books.book_count} {shelf_with_most_books.book_count === 1 ? 'book' : 'books'}
                  </span>
                </div>
              </>
            ) : (
              <>
                <div
                  style={{
                    fontSize: '1.1rem',
                    fontWeight: 500,
                    color: 'var(--text-secondary)',
                    marginTop: '2px',
                  }}
                  id="summary-top-shelf-none"
                >
                  None
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  No books in shelves
                </div>
              </>
            )}
          </div>
        </div>

        {/* 5. Books Currently Lent Out */}
        <div
          className="card"
          style={{
            padding: 'var(--space-md) var(--space-lg)',
            background: 'var(--bg-card)',
            borderLeft: '4px solid var(--warning)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}
          id="summary-lent-out-card"
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--warning-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
              flexShrink: 0,
            }}
          >
            📤
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Currently Lent Out
            </div>
            <div
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1.2,
                marginTop: '2px',
              }}
              id="summary-lent-out-val"
            >
              {books_currently_lent_out}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Active peer loans
            </div>
          </div>
        </div>

        {/* 6. Shelves Shared With Me */}
        <div
          className="card"
          style={{
            padding: 'var(--space-md) var(--space-lg)',
            background: 'var(--bg-card)',
            borderLeft: '4px solid var(--info)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
          }}
          id="summary-shared-shelves-card"
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--info-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
              flexShrink: 0,
            }}
          >
            🤝
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-muted)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Shared With Me
            </div>
            <div
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1.2,
                marginTop: '2px',
              }}
              id="summary-shared-shelves-val"
            >
              {shelves_shared_with_me}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Collaborator shelves
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
