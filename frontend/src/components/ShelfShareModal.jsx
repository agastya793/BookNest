import { useState, useEffect, useCallback } from 'react'
import {
  getShelfSharesApi,
  shareShelfApi,
  updateShelfShareRoleApi,
  removeShelfShareApi,
} from '../api/shelves'

/**
 * ShelfShareModal Component
 * Handles shelf collaboration and Role-Based Access Control:
 * - Owner can invite users by email as 'editor' or 'viewer'.
 * - Owner can change roles or remove collaborators.
 * - Collaborators can view fellow members and leave the shelf.
 */
export default function ShelfShareModal({
  isOpen,
  onClose,
  shelf,
  currentUserId,
  onShareUpdated,
}) {
  const [collaborators, setCollaborators] = useState([])
  const [loading, setLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('editor')
  const [inviting, setInviting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [actionId, setActionId] = useState(null)

  const isOwner = shelf?.role === 'owner' || (shelf?.user_id && shelf?.user_id === currentUserId)

  // Fetch collaborators list from server
  const fetchCollaborators = useCallback(async () => {
    if (!shelf?.id) return
    setLoading(true)
    setErrorMsg('')
    try {
      const res = await getShelfSharesApi(shelf.id)
      setCollaborators(res.data || [])
    } catch (err) {
      console.error('Failed to load shelf collaborators:', err)
      setErrorMsg(err.response?.data?.detail || 'Failed to load collaborators.')
    } finally {
      setLoading(false)
    }
  }, [shelf?.id])

  useEffect(() => {
    if (isOpen && shelf?.id) {
      setEmail('')
      setRole('editor')
      setErrorMsg('')
      setSuccessMsg('')
      fetchCollaborators()
    }
  }, [isOpen, shelf?.id, fetchCollaborators])

  if (!isOpen || !shelf) return null

  // Handle inviting a new collaborator
  const handleInvite = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')

    const trimmedEmail = email.trim().toLowerCase()
    if (!trimmedEmail) {
      setErrorMsg('Please enter a registered user email.')
      return
    }

    setInviting(true)
    try {
      await shareShelfApi(shelf.id, { email: trimmedEmail, role })
      setSuccessMsg(`Successfully invited ${trimmedEmail} as ${role}!`)
      setEmail('')
      await fetchCollaborators()
      if (onShareUpdated) onShareUpdated()
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (status === 404) {
        setErrorMsg(`User with email "${trimmedEmail}" was not found. Ensure they have created a BookNest account.`)
      } else if (status === 400) {
        setErrorMsg('You cannot share a shelf with yourself.')
      } else if (status === 409) {
        setErrorMsg(`This shelf is already shared with "${trimmedEmail}".`)
      } else if (status === 403) {
        setErrorMsg('Only the shelf owner can invite collaborators.')
      } else {
        setErrorMsg(detail || 'Failed to invite collaborator.')
      }
    } finally {
      setInviting(false)
    }
  }

  // Handle role change by owner
  const handleRoleChange = async (shareId, newRole) => {
    setErrorMsg('')
    setSuccessMsg('')
    setActionId(shareId)
    try {
      await updateShelfShareRoleApi(shelf.id, shareId, newRole)
      setSuccessMsg(`Collaborator role updated to ${newRole}.`)
      await fetchCollaborators()
      if (onShareUpdated) onShareUpdated()
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to update role.')
    } finally {
      setActionId(null)
    }
  }

  // Handle removing a collaborator or leaving the shelf
  const handleRemoveCollaborator = async (share) => {
    const isSelf = share.user_id === currentUserId
    const confirmMsg = isSelf
      ? `Are you sure you want to leave shelf "${shelf.name}"? You will lose access to this shared shelf.`
      : `Remove ${share.user_name || share.user_email} from shelf "${shelf.name}"?`

    if (!window.confirm(confirmMsg)) return

    setErrorMsg('')
    setSuccessMsg('')
    setActionId(share.id)
    try {
      await removeShelfShareApi(shelf.id, share.id)
      if (isSelf) {
        onClose()
        if (onShareUpdated) onShareUpdated(true) // left shelf
      } else {
        setSuccessMsg(`Removed ${share.user_name || share.user_email} from shelf.`)
        await fetchCollaborators()
        if (onShareUpdated) onShareUpdated()
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to remove collaborator.')
    } finally {
      setActionId(null)
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
        if (e.target === e.currentTarget && !inviting) onClose()
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '520px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--shadow-lg)',
          padding: 'var(--space-xl)',
          overflow: 'hidden',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: 'var(--space-md)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
              <span style={{ fontSize: '1.4rem' }}>👥</span>
              <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600 }}>
                {isOwner ? 'Manage Collaborators' : 'Shared Shelf Collaborators'}
              </h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)', marginTop: '2px' }}>
              Shelf: <strong style={{ color: 'var(--text-primary)' }}>{shelf.name}</strong>
              {shelf.owner_name && ` • Owned by ${shelf.owner_name}`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={inviting}
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

        {/* Feedback Alerts */}
        {errorMsg && (
          <div
            style={{
              background: 'var(--error-bg)',
              color: 'var(--error)',
              padding: 'var(--space-xs) var(--space-md)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-sm)',
              fontSize: 'var(--font-size-xs)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
            }}
          >
            ⚠️ {errorMsg}
          </div>
        )}

        {successMsg && (
          <div
            style={{
              background: 'rgba(34, 197, 94, 0.15)',
              color: 'var(--success)',
              padding: 'var(--space-xs) var(--space-md)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-sm)',
              fontSize: 'var(--font-size-xs)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
            }}
          >
            ✓ {successMsg}
          </div>
        )}

        {/* Owner Invite Form */}
        {isOwner ? (
          <form
            onSubmit={handleInvite}
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-md)',
              marginBottom: 'var(--space-md)',
            }}
          >
            <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, marginBottom: 'var(--space-xs)' }}>
              Invite a Collaborator
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap' }}>
              <input
                type="email"
                placeholder="registered.user@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  if (errorMsg) setErrorMsg('')
                }}
                disabled={inviting}
                required
                style={{ flex: 2, minWidth: '180px', padding: '6px 10px', fontSize: 'var(--font-size-xs)' }}
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                disabled={inviting}
                style={{ width: 'auto', padding: '6px 10px', fontSize: 'var(--font-size-xs)' }}
              >
                <option value="editor">Editor (Can add/remove books)</option>
                <option value="viewer">Viewer (Read-only)</option>
              </select>
              <button
                type="submit"
                className="btn-primary"
                disabled={inviting || !email.trim()}
                style={{ padding: '6px 14px', fontSize: 'var(--font-size-xs)' }}
              >
                {inviting ? 'Inviting...' : '+ Invite'}
              </button>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginTop: '6px' }}>
              Invited users will immediately see "{shelf.name}" under their "Shared with me" shelves.
            </p>
          </form>
        ) : (
          <div
            style={{
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-sm) var(--space-md)',
              marginBottom: 'var(--space-md)',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
            }}
          >
            You are a <strong>{shelf.role?.toUpperCase()}</strong> on this shared shelf.
            {shelf.role === 'viewer' && ' You have read-only access to browse its books.'}
            {shelf.role === 'editor' && ' You can add and remove books from this shelf.'}
          </div>
        )}

        {/* Collaborators List Section */}
        <div style={{ flex: 1, overflowY: 'auto', minHeight: '120px' }}>
          <div
            style={{
              fontSize: 'var(--font-size-xs)',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: 'var(--space-xs)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Active Collaborators ({collaborators.length})
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-lg)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
              Loading collaborators...
            </div>
          ) : collaborators.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: 'var(--space-lg)',
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-xs)',
                border: '1px dashed var(--border)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              {isOwner
                ? 'No collaborators yet. Invite someone above by their registered BookNest email.'
                : 'No other collaborators on this shelf.'}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
              {collaborators.map((c) => {
                const isSelf = c.user_id === currentUserId
                return (
                  <div
                    key={c.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: 'var(--space-xs) var(--space-sm)',
                      background: isSelf ? 'rgba(139, 92, 246, 0.1)' : 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-sm)',
                      border: isSelf ? '1px solid var(--accent)' : '1px solid var(--border)',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
                          {c.user_name || c.user_email}
                        </span>
                        {isSelf && <span className="badge badge-accent" style={{ fontSize: '0.65rem' }}>You</span>}
                      </div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                        {c.user_email}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                      {isOwner ? (
                        <>
                          <select
                            value={c.role}
                            onChange={(e) => handleRoleChange(c.id, e.target.value)}
                            disabled={actionId === c.id}
                            style={{
                              padding: '4px 8px',
                              fontSize: 'var(--font-size-xs)',
                              borderRadius: 'var(--radius-sm)',
                            }}
                          >
                            <option value="editor">Editor</option>
                            <option value="viewer">Viewer</option>
                          </select>
                          <button
                            type="button"
                            className="btn-danger"
                            onClick={() => handleRemoveCollaborator(c)}
                            disabled={actionId === c.id}
                            style={{ padding: '4px 8px', fontSize: 'var(--font-size-xs)' }}
                            title="Remove collaborator"
                          >
                            ✕
                          </button>
                        </>
                      ) : (
                        <>
                          <span
                            className={`badge ${c.role === 'editor' ? 'badge-accent' : 'badge-info'}`}
                            style={{ textTransform: 'capitalize' }}
                          >
                            {c.role}
                          </span>
                          {isSelf && (
                            <button
                              type="button"
                              className="btn-danger"
                              onClick={() => handleRemoveCollaborator(c)}
                              disabled={actionId === c.id}
                              style={{ padding: '3px 8px', fontSize: 'var(--font-size-xs)' }}
                            >
                              Leave Shelf
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            marginTop: 'var(--space-md)',
            borderTop: '1px solid var(--border)',
            paddingTop: 'var(--space-sm)',
          }}
        >
          <button type="button" className="btn-secondary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
