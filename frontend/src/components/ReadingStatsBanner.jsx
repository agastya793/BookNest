/**
 * ReadingStatsBanner Component
 * Displays aggregated personal reading statistics at the top of the Dashboard.
 */
export default function ReadingStatsBanner({ stats, loading }) {
  if (loading && !stats) {
    return (
      <div
        className="card"
        style={{
          marginBottom: 'var(--space-lg)',
          padding: 'var(--space-md)',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: 'var(--font-size-sm)',
        }}
      >
        Loading reading statistics...
      </div>
    )
  }

  const {
    total_books = 0,
    books_reading = 0,
    books_finished = 0,
    total_pages_read = 0,
    completion_rate = 0.0,
  } = stats || {}

  const statItems = [
    {
      label: 'Pages Read',
      value: total_pages_read.toLocaleString(),
      subtext: 'Logged across library',
      icon: '📖',
      color: 'var(--accent)',
      bgColor: 'var(--accent-light)',
    },
    {
      label: 'Currently Reading',
      value: books_reading,
      subtext: books_reading === 1 ? '1 active book' : `${books_reading} active books`,
      icon: '⏳',
      color: 'var(--warning)',
      bgColor: 'var(--warning-bg)',
    },
    {
      label: 'Books Finished',
      value: books_finished,
      subtext: `${books_finished} of ${total_books} total`,
      icon: '🏆',
      color: 'var(--success)',
      bgColor: 'var(--success-bg)',
    },
    {
      label: 'Completion Rate',
      value: `${completion_rate}%`,
      subtext: 'Finished / Total Books',
      icon: '🎯',
      color: 'var(--info)',
      bgColor: 'var(--info-bg)',
      showBar: true,
      rate: completion_rate,
    },
  ]

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: 'var(--space-md)',
        marginBottom: 'var(--space-xl)',
      }}
    >
      {statItems.map((item, index) => (
        <div
          key={index}
          className="card"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
            padding: 'var(--space-md) var(--space-lg)',
            borderLeft: `3px solid ${item.color}`,
            background: 'var(--bg-card)',
            transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
          }}
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-md)',
              background: item.bgColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
              flexShrink: 0,
            }}
          >
            {item.icon}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--text-muted)',
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              {item.label}
            </div>
            <div
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1.2,
                marginTop: '2px',
              }}
            >
              {item.value}
            </div>
            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                marginTop: '2px',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {item.subtext}
            </div>
            {item.showBar && (
              <div
                style={{
                  width: '100%',
                  height: '4px',
                  background: 'var(--bg-primary)',
                  borderRadius: '100px',
                  marginTop: '6px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${Math.min(100, Math.max(0, item.rate))}%`,
                    height: '100%',
                    background: item.color,
                    transition: 'width var(--transition-base)',
                  }}
                />
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
