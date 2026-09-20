import React, { useState, useEffect, useCallback } from 'react'
import { getActivitiesApi } from '../api/activity'
import { useAuth } from '../context/AuthContext'

/**
 * Human-readable status label formatter
 */
const formatStatus = (status) => {
  if (!status) return ''
  switch (status) {
    case 'want_to_read':
      return 'Want to Read'
    case 'reading':
      return 'Reading'
    case 'finished':
      return 'Finished'
    default:
      return status.replace(/_/g, ' ')
  }
}

/**
 * Format timestamp into relative/human readable string
 */
const formatTimestamp = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHours = Math.floor(diffMin / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSec < 45) return 'Just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * ActivityFeed Component
 *
 * Renders the chronological activity stream with:
 * - Server-side pagination
 * - Simple filter categories (All, Personal, Shelves, Lending)
 * - Human-readable descriptions (no raw JSON)
 * - Actor and target attribution
 * - Loading, Error, Empty, and Loaded UI states
 */
export default function ActivityFeed({
  refreshTrigger = 0,
  onClose,
  currentShelfId = null,
  compact = false,
}) {
  const { user } = useAuth()

  // State
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  // Filter category state: 'all' | 'personal' | 'shelves' | 'lending'
  const [activeFilter, setActiveFilter] = useState('all')

  const filterMap = {
    all: '',
    personal: 'book_added,status_changed,progress_updated',
    shelves: 'shelf_shared,shelf_role_changed,shelf_share_removed',
    lending: 'book_lent,book_returned',
  }

  // Fetch activities from backend
  const fetchActivities = useCallback(
    async (targetPage = page, targetFilter = activeFilter) => {
      setLoading(true)
      setError(null)
      try {
        const params = {
          page: targetPage,
          page_size: pageSize,
        }

        const actionQuery = filterMap[targetFilter]
        if (actionQuery) {
          params.action = actionQuery
        }

        if (currentShelfId) {
          params.shelf_id = currentShelfId
        }

        const res = await getActivitiesApi(params)
        const data = res.data
        setActivities(data.items || [])
        setPage(data.page || 1)
        setTotal(data.total || 0)
        setTotalPages(data.total_pages || 0)
      } catch (err) {
        console.error('Failed to fetch activity feed:', err)
        setError(err.response?.data?.detail || 'Failed to load activity feed. Please try again.')
      } finally {
        setLoading(false)
      }
    },
    [pageSize, currentShelfId]
  )

  // Effect: Refetch on mount or when page/filter changes
  useEffect(() => {
    fetchActivities(page, activeFilter)
  }, [fetchActivities, page, activeFilter])

  // Effect: Refetch when refreshTrigger changes (user completed a mutation elsewhere)
  useEffect(() => {
    if (refreshTrigger > 0) {
      fetchActivities(1, activeFilter)
    }
  }, [refreshTrigger])

  // Handle filter change (resets page to 1)
  const handleFilterChange = (newFilter) => {
    if (newFilter === activeFilter) return
    setActiveFilter(newFilter)
    setPage(1)
  }

  // Handle pagination
  const handlePrevPage = () => {
    if (page > 1 && !loading) {
      setPage((prev) => prev - 1)
    }
  }

  const handleNextPage = () => {
    if (page < totalPages && !loading) {
      setPage((prev) => prev + 1)
    }
  }

  // Helper to format activity item presentation
  const renderActivityDetails = (item) => {
    const details = item.details || {}
    const isCurrentUser = user && item.user_id === user.id
    const actorName = isCurrentUser ? 'You' : item.user_name || 'A collaborator'

    switch (item.action) {
      case 'book_added': {
        const title = details.title || 'a book'
        const author = details.author ? ` by ${details.author}` : ''
        return {
          icon: '📖',
          badgeClass: 'badge-accent',
          badgeText: 'Book Added',
          title: `${actorName} added "${title}"${author}`,
          subtitle: details.total_pages ? `${details.total_pages} total pages` : null,
        }
      }

      case 'status_changed': {
        const title = details.title || 'a book'
        const oldStatus = formatStatus(details.old_status)
        const newStatus = formatStatus(details.new_status)
        return {
          icon: '🔄',
          badgeClass: 'badge-info',
          badgeText: 'Status Changed',
          title: `${actorName} changed "${title}" from ${oldStatus} to ${newStatus}`,
          subtitle:
            details.new_page !== undefined && details.total_pages
              ? `Progress: ${details.new_page}/${details.total_pages} pages (${details.progress_percentage || 0}%)`
              : null,
        }
      }

      case 'progress_updated': {
        const title = details.title || 'a book'
        const newPage = details.new_page ?? 0
        const totalPages = details.total_pages
        const progressPct = details.progress_percentage
        const milestone = details.milestone
        return {
          icon: '📈',
          badgeClass: 'badge-accent',
          badgeText: 'Progress Updated',
          title: `${actorName} updated progress on "${title}" to page ${newPage}`,
          subtitle: totalPages
            ? `${newPage} of ${totalPages} pages (${progressPct || 0}%)${
                milestone ? ` • Milestone: ${milestone}` : ''
              }`
            : `Page ${newPage}`,
        }
      }

      case 'book_lent': {
        const title = details.book_title || 'a book'
        const borrower = details.borrower_name || details.borrower_email || 'another reader'
        return {
          icon: '🤝',
          badgeClass: 'badge-warning',
          badgeText: 'Book Lent',
          title: isCurrentUser
            ? `You lent "${title}" to ${borrower}`
            : `Lent "${title}" to ${borrower}`,
          subtitle: `Active peer loan`,
        }
      }

      case 'book_returned': {
        const title = details.book_title || 'a book'
        const borrower = details.borrower_name ? ` from ${details.borrower_name}` : ''
        return {
          icon: '↩️',
          badgeClass: 'badge-success',
          badgeText: 'Book Returned',
          title: `${actorName} marked "${title}" as returned${borrower}`,
          subtitle: 'Book restored to available catalog',
        }
      }

      case 'shelf_shared': {
        const shelfName = item.shelf_name || details.shelf_name || 'Shelf'
        const collaborator =
          details.collaborator_name || details.collaborator_email || 'collaborator'
        const role = details.role ? details.role.toUpperCase() : 'COLLABORATOR'
        return {
          icon: '👥',
          badgeClass: 'badge-info',
          badgeText: 'Shelf Shared',
          title: `${actorName} shared "${shelfName}" with ${collaborator} as ${role}`,
          subtitle: `Role: ${role}`,
        }
      }

      case 'shelf_role_changed': {
        const shelfName = item.shelf_name || details.shelf_name || 'Shelf'
        const collaborator =
          details.collaborator_name || details.collaborator_email || 'collaborator'
        const oldRole = (details.old_role || 'viewer').toUpperCase()
        const newRole = (details.new_role || 'editor').toUpperCase()
        return {
          icon: '🛡️',
          badgeClass: 'badge-accent',
          badgeText: 'Role Changed',
          title: `${actorName} changed ${collaborator}'s role on "${shelfName}" from ${oldRole} to ${newRole}`,
          subtitle: `Updated role: ${newRole}`,
        }
      }

      case 'shelf_share_removed': {
        const shelfName = item.shelf_name || details.shelf_name || 'Shelf'
        const collaborator =
          details.collaborator_name || details.collaborator_email || 'collaborator'
        const removedBy = details.removed_by === 'self' ? 'left' : 'was removed from'
        return {
          icon: '🚫',
          badgeClass: 'badge-warning',
          badgeText: 'Share Removed',
          title:
            details.removed_by === 'self'
              ? `${collaborator} left shelf "${shelfName}"`
              : `${actorName} removed ${collaborator} from "${shelfName}"`,
          subtitle: `Access revoked`,
        }
      }

      default:
        return {
          icon: '📌',
          badgeClass: 'badge-secondary',
          badgeText: item.action.replace(/_/g, ' '),
          title: `${actorName} performed ${item.action.replace(/_/g, ' ')}`,
          subtitle: null,
        }
    }
  }

  return (
    <div
      className="card"
      id="activity-feed-container"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md)',
        background: 'linear-gradient(180deg, var(--bg-card) 0%, rgba(26, 29, 39, 0.95) 100%)',
        borderColor: 'rgba(139, 92, 246, 0.3)',
        padding: 'var(--space-lg)',
        boxShadow: 'var(--shadow-lg)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-sm)',
          borderBottom: '1px solid var(--border)',
          paddingBottom: 'var(--space-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <span style={{ fontSize: '1.5rem' }}>⚡</span>
          <div>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700, margin: 0 }}>
              Activity Feed
            </h3>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', margin: 0 }}>
              Chronological audit log of your reading and collection events
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => fetchActivities(page, activeFilter)}
            disabled={loading}
            title="Refresh activities"
            style={{ fontSize: 'var(--font-size-xs)', padding: '6px 10px' }}
            id="activity-feed-refresh-btn"
          >
            {loading ? '↻ Loading...' : '↻ Refresh'}
          </button>
          {onClose && (
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              title="Close activity feed"
              style={{ fontSize: 'var(--font-size-xs)', padding: '6px 10px' }}
              id="activity-feed-close-btn"
            >
              ✕ Close
            </button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 'var(--space-xs)',
          alignItems: 'center',
          background: 'var(--bg-primary)',
          padding: '4px',
          borderRadius: 'var(--radius-md)',
          width: 'fit-content',
        }}
        id="activity-feed-filters"
      >
        {[
          { key: 'all', label: 'All Activity' },
          { key: 'personal', label: '📖 Personal Books' },
          { key: 'shelves', label: '📁 Shelves' },
          { key: 'lending', label: '🤝 Lending' },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => handleFilterChange(tab.key)}
            disabled={loading}
            style={{
              padding: '6px 12px',
              fontSize: 'var(--font-size-xs)',
              borderRadius: 'var(--radius-sm)',
              background: activeFilter === tab.key ? 'var(--accent)' : 'transparent',
              color: activeFilter === tab.key ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeFilter === tab.key ? 600 : 500,
              border: 'none',
              cursor: 'pointer',
              transition: 'all var(--transition-fast)',
            }}
            id={`activity-filter-${tab.key}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ minHeight: '180px' }}>
        {/* Loading State */}
        {loading && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 'var(--space-xl) 0',
              color: 'var(--text-secondary)',
              gap: 'var(--space-sm)',
            }}
            id="activity-feed-loading"
          >
            <div
              style={{
                width: '32px',
                height: '32px',
                border: '3px solid var(--border)',
                borderTopColor: 'var(--accent)',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
              }}
            />
            <span style={{ fontSize: 'var(--font-size-sm)' }}>Loading activities...</span>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div
            className="card"
            style={{
              borderColor: 'var(--error)',
              background: 'rgba(239, 68, 68, 0.1)',
              textAlign: 'center',
              padding: 'var(--space-lg)',
            }}
            id="activity-feed-error"
          >
            <div style={{ fontSize: '1.75rem', marginBottom: 'var(--space-xs)' }}>⚠️</div>
            <h4 style={{ color: 'var(--error)', marginBottom: 'var(--space-xs)' }}>
              Could not load activities
            </h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-md)' }}>
              {error}
            </p>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => fetchActivities(page, activeFilter)}
              style={{ fontSize: 'var(--font-size-xs)' }}
              id="activity-feed-retry-btn"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && activities.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--space-xl) var(--space-md)',
              color: 'var(--text-secondary)',
            }}
            id="activity-feed-empty"
          >
            <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-xs)' }}>📭</div>
            <h4 style={{ color: 'var(--text-primary)', marginBottom: 'var(--space-xs)' }}>
              No activity yet
            </h4>
            <p style={{ fontSize: 'var(--font-size-sm)', maxWidth: '360px', margin: '0 auto' }}>
              Events will appear here as you add books, track reading milestones, share shelves, and lend books to fellow readers.
            </p>
          </div>
        )}

        {/* Loaded Activity Items */}
        {!loading && !error && activities.length > 0 && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-sm)',
            }}
            id="activity-feed-list"
          >
            {activities.map((item) => {
              const display = renderActivityDetails(item)
              return (
                <div
                  key={item.id}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 'var(--space-md)',
                    padding: 'var(--space-sm) var(--space-md)',
                    background: 'var(--bg-secondary)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border)',
                    transition: 'border-color var(--transition-fast), transform var(--transition-fast)',
                  }}
                  className="activity-item"
                >
                  {/* Icon */}
                  <div
                    style={{
                      fontSize: '1.25rem',
                      width: '36px',
                      height: '36px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-input)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      marginTop: '2px',
                    }}
                  >
                    {display.icon}
                  </div>

                  {/* Body */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'baseline',
                        gap: 'var(--space-sm)',
                        flexWrap: 'wrap',
                        marginBottom: '2px',
                      }}
                    >
                      <span
                        style={{
                          fontSize: 'var(--font-size-sm)',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                        }}
                      >
                        {display.title}
                      </span>
                      <span
                        style={{
                          fontSize: 'var(--font-size-xs)',
                          color: 'var(--text-muted)',
                          whiteSpace: 'nowrap',
                        }}
                        title={new Date(item.created_at).toLocaleString()}
                      >
                        {formatTimestamp(item.created_at)}
                      </span>
                    </div>

                    {display.subtitle && (
                      <div
                        style={{
                          fontSize: 'var(--font-size-xs)',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        {display.subtitle}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Pagination Footer */}
      {!loading && !error && total > 0 && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderTop: '1px solid var(--border)',
            paddingTop: 'var(--space-sm)',
            marginTop: 'var(--space-xs)',
            flexWrap: 'wrap',
            gap: 'var(--space-sm)',
          }}
          id="activity-feed-pagination"
        >
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Showing page {page} of {totalPages} ({total} total {total === 1 ? 'event' : 'events'})
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={handlePrevPage}
              disabled={page <= 1 || loading}
              style={{ fontSize: 'var(--font-size-xs)', padding: '4px 10px' }}
              id="activity-feed-prev-btn"
            >
              Previous
            </button>
            <span
              style={{
                fontSize: 'var(--font-size-xs)',
                fontWeight: 600,
                padding: '4px 8px',
                color: 'var(--text-secondary)',
              }}
            >
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleNextPage}
              disabled={page >= totalPages || loading}
              style={{ fontSize: 'var(--font-size-xs)', padding: '4px 10px' }}
              id="activity-feed-next-btn"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
