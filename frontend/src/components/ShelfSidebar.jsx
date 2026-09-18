/**
 * ShelfSidebar Component
 * Provides modular custom shelf navigation:
 * - "My Shelves" (owned collections) with Rename, Delete, and Share (RBAC) actions.
 * - "Shared with me" (collaborator collections) with Role badges (Editor/Viewer) and Collaborators/Leave action.
 * - Accurate book count badges (including 0 for empty shelves).
 */
export default function ShelfSidebar({
  shelves = [],
  totalBooksCount = 0,
  selectedShelfId = null,
  onSelectShelf,
  onOpenCreateShelf,
  onOpenEditShelf,
  onDeleteShelf,
  onOpenShareShelf,
  loading = false,
}) {
  const myShelves = shelves.filter((s) => s.role === 'owner' || !s.role)
  const sharedShelves = shelves.filter((s) => s.role && s.role !== 'owner')

  const renderShelfRow = (shelf, isShared = false) => {
    const isSelected = selectedShelfId === shelf.id
    return (
      <div
        key={shelf.id}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderRadius: 'var(--radius-md)',
          background: isSelected ? 'var(--accent-light)' : 'transparent',
          border: isSelected ? '1px solid var(--accent)' : '1px solid transparent',
          transition: 'all var(--transition-fast)',
          marginBottom: '2px',
        }}
      >
        {/* Select Shelf Button */}
        <button
          type="button"
          onClick={() => onSelectShelf(shelf.id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-sm)',
            padding: '8px 10px',
            background: 'transparent',
            color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
            fontWeight: isSelected ? 600 : 500,
            textAlign: 'left',
            flex: 1,
            minWidth: 0,
            cursor: 'pointer',
          }}
          title={
            isShared
              ? `View "${shelf.name}" (${shelf.role}) • Shared by ${shelf.owner_name || shelf.owner_email}`
              : `View books in "${shelf.name}"`
          }
        >
          <span style={{ fontSize: '0.95rem' }}>{isShared ? '🤝' : '📁'}</span>
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <span
              style={{
                fontSize: 'var(--font-size-sm)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {shelf.name}
            </span>
            {isShared && (
              <span
                style={{
                  fontSize: '0.68rem',
                  color: 'var(--text-muted)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                by {shelf.owner_name || shelf.owner_email || 'Owner'}
              </span>
            )}
          </div>
        </button>

        {/* Badges & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', paddingRight: '6px' }}>
          {/* Role badge for shared shelves */}
          {isShared && (
            <span
              className={`badge ${shelf.role === 'editor' ? 'badge-accent' : 'badge-info'}`}
              style={{ fontSize: '0.65rem', padding: '1px 5px', textTransform: 'capitalize' }}
            >
              {shelf.role}
            </span>
          )}

          {/* Book count badge */}
          <span
            className="badge"
            style={{
              background: isSelected ? 'var(--accent)' : 'var(--bg-primary)',
              color: isSelected ? '#ffffff' : 'var(--text-muted)',
              fontSize: 'var(--font-size-xs)',
              padding: '2px 6px',
            }}
            title={`${shelf.book_count} books on this shelf`}
          >
            {shelf.book_count}
          </span>

          {/* Share / Collaborators Action */}
          {onOpenShareShelf && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onOpenShareShelf(shelf)
              }}
              style={{
                background: 'transparent',
                color: 'var(--text-muted)',
                padding: '4px',
                fontSize: '0.85rem',
                lineHeight: 1,
                cursor: 'pointer',
                borderRadius: 'var(--radius-sm)',
              }}
              title={isShared ? 'View collaborators / leave shelf' : 'Manage collaborators (Invite/Share)'}
            >
              👥
            </button>
          )}

          {/* Owner Actions: Rename & Delete */}
          {!isShared && (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onOpenEditShelf(shelf)
                }}
                style={{
                  background: 'transparent',
                  color: 'var(--text-muted)',
                  padding: '4px',
                  fontSize: '0.85rem',
                  lineHeight: 1,
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-sm)',
                }}
                title="Rename shelf"
              >
                ✏️
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteShelf(shelf)
                }}
                style={{
                  background: 'transparent',
                  color: 'var(--text-muted)',
                  padding: '4px',
                  fontSize: '0.85rem',
                  lineHeight: 1,
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-sm)',
                }}
                title="Delete shelf (books remain safe in your library)"
              >
                🗑️
              </button>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <aside
      className="card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md)',
        padding: 'var(--space-md)',
        height: 'fit-content',
        position: 'sticky',
        top: 'var(--space-md)',
      }}
    >
      {/* Sidebar Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 'var(--space-sm)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
          <span style={{ fontSize: '1.1rem' }}>🗂️</span>
          <span
            style={{
              fontSize: 'var(--font-size-sm)',
              fontWeight: 700,
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
              color: 'var(--text-secondary)',
            }}
          >
            Shelves
          </span>
        </div>
        <button
          type="button"
          className="btn-primary"
          onClick={onOpenCreateShelf}
          style={{
            padding: '4px 10px',
            fontSize: 'var(--font-size-xs)',
            borderRadius: 'var(--radius-sm)',
          }}
          title="Create a new custom shelf"
        >
          + New Shelf
        </button>
      </div>

      {/* Navigation List */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {/* All Books Default View */}
        <button
          type="button"
          onClick={() => onSelectShelf(null)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 12px',
            borderRadius: 'var(--radius-md)',
            background: selectedShelfId === null ? 'var(--accent-light)' : 'transparent',
            color: selectedShelfId === null ? 'var(--text-primary)' : 'var(--text-secondary)',
            border: selectedShelfId === null ? '1px solid var(--accent)' : '1px solid transparent',
            fontWeight: selectedShelfId === null ? 600 : 500,
            textAlign: 'left',
            width: '100%',
            transition: 'all var(--transition-fast)',
            cursor: 'pointer',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <span style={{ fontSize: '1rem' }}>📚</span>
            <span style={{ fontSize: 'var(--font-size-sm)' }}>All Books</span>
          </div>
          <span
            className="badge"
            style={{
              background: selectedShelfId === null ? 'var(--accent)' : 'var(--bg-primary)',
              color: selectedShelfId === null ? '#ffffff' : 'var(--text-muted)',
              fontSize: 'var(--font-size-xs)',
              fontWeight: 600,
              padding: '2px 8px',
            }}
          >
            {totalBooksCount}
          </span>
        </button>

        {/* My Shelves Section */}
        <div style={{ margin: 'var(--space-xs) 0 4px 0', borderTop: '1px solid var(--border)', paddingTop: '6px' }}>
          <div
            style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              padding: '0 8px 4px 8px',
            }}
          >
            My Shelves ({myShelves.length})
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 'var(--space-sm)', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            Loading shelves...
          </div>
        ) : myShelves.length === 0 ? (
          <div
            style={{
              padding: 'var(--space-sm)',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: 'var(--font-size-xs)',
              lineHeight: 1.4,
            }}
          >
            No personal shelves yet.
          </div>
        ) : (
          myShelves.map((shelf) => renderShelfRow(shelf, false))
        )}

        {/* Shared With Me Section */}
        {sharedShelves.length > 0 && (
          <div style={{ margin: 'var(--space-xs) 0 4px 0', borderTop: '1px solid var(--border)', paddingTop: '6px' }}>
            <div
              style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                color: 'var(--accent)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                padding: '0 8px 4px 8px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>🤝</span> Shared with me ({sharedShelves.length})
            </div>
            {sharedShelves.map((shelf) => renderShelfRow(shelf, true))}
          </div>
        )}
      </nav>
    </aside>
  )
}
