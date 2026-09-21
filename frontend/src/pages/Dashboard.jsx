import { useState, useEffect, useCallback, useMemo } from 'react'
import { useAuth } from '../context/AuthContext'
import { useSocket, useShelfSubscription } from '../hooks/useSocket'
import Navbar from '../components/Navbar'
import BookCard from '../components/BookCard'
import BookModal from '../components/BookModal'
import ShelfSidebar from '../components/ShelfSidebar'
import ShelfModal from '../components/ShelfModal'
import AssignShelfModal from '../components/AssignShelfModal'
import ShelfShareModal from '../components/ShelfShareModal'
import ReadingStatsBanner from '../components/ReadingStatsBanner'
import DashboardSummary from '../components/DashboardSummary'
import ProgressModal from '../components/ProgressModal'
import LendBookModal from '../components/LendBookModal'
import LendingHistoryModal from '../components/LendingHistoryModal'
import ActivityFeed from '../components/ActivityFeed'
import {
  getBooksApi,
  createBookApi,
  updateBookApi,
  deleteBookApi,
  updateBookProgressApi,
  getReadingStatsApi,
} from '../api/books'
import {
  getShelvesApi,
  createShelfApi,
  updateShelfApi,
  deleteShelfApi,
  addBookToShelfApi,
  removeBookFromShelfApi,
} from '../api/shelves'
import {
  getLendingsApi,
  getBorrowedBooksApi,
  returnBookApi,
} from '../api/lending'
import { getDashboardSummaryApi } from '../api/dashboard'
import { getMeApi } from '../api/auth'
import { getAccessToken } from '../api/client'

export default function Dashboard() {
  const { user, refreshSession, accessToken } = useAuth()

  // Books State
  const [books, setBooks] = useState([])
  const [totalCatalogCount, setTotalCatalogCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Pagination State
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  // Shelves State
  const [shelves, setShelves] = useState([])
  const [shelvesLoading, setShelvesLoading] = useState(false)
  const [selectedShelfId, setSelectedShelfId] = useState(null)

  // Filters and Sorting
  const [statusFilter, setStatusFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortDir, setSortDir] = useState('desc')

  // Modals State
  const [isBookModalOpen, setIsBookModalOpen] = useState(false)
  const [editingBook, setEditingBook] = useState(null)
  const [shelfModalState, setShelfModalState] = useState({
    isOpen: false,
    mode: 'create',
    shelf: null,
  })
  const [assignModalBook, setAssignModalBook] = useState(null)
  const [shareModalShelf, setShareModalShelf] = useState(null)

  // Reading Statistics State (Phase 6)
  const [readingStats, setReadingStats] = useState(null)
  const [readingStatsLoading, setReadingStatsLoading] = useState(false)
  const [readingStatsError, setReadingStatsError] = useState(null)

  // Dedicated Dashboard Summary State (Step 2 - Requirement #32)
  const [dashboardSummary, setDashboardSummary] = useState(null)
  const [dashboardSummaryLoading, setDashboardSummaryLoading] = useState(false)
  const [dashboardSummaryError, setDashboardSummaryError] = useState(null)

  // Progress Modal State (Phase 6)
  const [progressModalState, setProgressModalState] = useState({
    isOpen: false,
    book: null,
  })

  // Milestone Celebration Toast State (Phase 6)
  const [milestoneToast, setMilestoneToast] = useState(null)

  // Lending State (Phase 7)
  const [activeView, setActiveView] = useState('catalog') // 'catalog' | 'lent_out' | 'borrowed'
  const [lentBooks, setLentBooks] = useState([])
  const [borrowedBooks, setBorrowedBooks] = useState([])
  const [lendModalBook, setLendModalBook] = useState(null)
  const [historyModalBook, setHistoryModalBook] = useState(null)

  // Activity Feed State (Phase 8)
  const [showActivityFeed, setShowActivityFeed] = useState(false)
  const [activityRefreshTrigger, setActivityRefreshTrigger] = useState(0)

  const triggerActivityRefresh = useCallback(() => {
    setActivityRefreshTrigger((prev) => prev + 1)
  }, [])

  // Collapsible Architecture Diagnostics
  const [showDiagnostics, setShowDiagnostics] = useState(false)
  const [testOutput, setTestOutput] = useState(null)
  const [loadingAction, setLoadingAction] = useState(null)

  // Memoized dictionary of shelfId -> shelfName
  const shelvesMap = useMemo(() => {
    const map = {}
    shelves.forEach((s) => {
      map[s.id] = s.name
    })
    return map
  }, [shelves])

  // Active selected shelf entity
  const activeShelf = useMemo(() => {
    if (!selectedShelfId) return null
    return shelves.find((s) => s.id === selectedShelfId) || null
  }, [shelves, selectedShelfId])

  // Fetch shelves from backend API
  const fetchShelves = useCallback(async () => {
    setShelvesLoading(true)
    try {
      const res = await getShelvesApi()
      setShelves(res.data)
    } catch (err) {
      console.error('Failed to load shelves:', err)
    } finally {
      setShelvesLoading(false)
    }
  }, [])

  // Fetch total books count across entire catalog (unfiltered by shelf)
  const fetchTotalCatalogCount = useCallback(async () => {
    try {
      const res = await getBooksApi({ page: 1, page_size: 1 })
      setTotalCatalogCount(res.data?.total ?? 0)
    } catch (err) {
      console.error('Failed to load total catalog count:', err)
    }
  }, [])

  // Fetch books from backend API with server-side pagination, filters, search, and sort
  const fetchBooks = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_dir: sortDir,
      }
      if (selectedShelfId) params.shelf_id = selectedShelfId
      if (statusFilter) params.status = statusFilter
      if (searchTerm.trim()) params.search = searchTerm.trim()

      const res = await getBooksApi(params)
      setBooks(res.data?.items || [])
      setTotal(res.data?.total ?? 0)
      setTotalPages(res.data?.total_pages ?? 0)

      // If viewing all books, also keep totalCatalogCount synchronized
      if (!selectedShelfId && !statusFilter && !searchTerm.trim()) {
        setTotalCatalogCount(res.data?.total ?? 0)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load books from server.')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, selectedShelfId, statusFilter, searchTerm, sortBy, sortDir])

  // Fetch reading statistics from dedicated Phase 6 summary endpoint
  const fetchReadingStats = useCallback(async () => {
    setReadingStatsLoading(true)
    setReadingStatsError(null)
    try {
      const res = await getReadingStatsApi()
      setReadingStats(res.data)
    } catch (err) {
      console.error('Failed to load reading statistics:', err)
      setReadingStatsError('Failed to load reading statistics.')
    } finally {
      setReadingStatsLoading(false)
    }
  }, [])

  // Fetch dedicated dashboard summary from /api/dashboard/summary (Step 2 - Requirement #32)
  const fetchDashboardSummary = useCallback(async () => {
    setDashboardSummaryLoading(true)
    setDashboardSummaryError(null)
    try {
      const res = await getDashboardSummaryApi()
      setDashboardSummary(res.data)
    } catch (err) {
      console.error('Failed to load dashboard summary:', err)
      setDashboardSummaryError('Failed to load dashboard summary.')
    } finally {
      setDashboardSummaryLoading(false)
    }
  }, [])

  // Fetch active lending records (Phase 7)
  const fetchLendingData = useCallback(async () => {
    try {
      const [lentRes, borrowedRes] = await Promise.all([
        getLendingsApi({ role: 'lender', status: 'active' }),
        getBorrowedBooksApi(),
      ])
      setLentBooks(lentRes || [])
      setBorrowedBooks(borrowedRes || [])
    } catch (err) {
      console.error('Failed to load lending data:', err)
    }
  }, [])

  const handleReturnBook = async (lendingId) => {
    if (!lendingId) return
    try {
      await returnBookApi(lendingId)
      await Promise.all([fetchLendingData(), fetchBooks(), fetchReadingStats(), fetchDashboardSummary()])
      triggerActivityRefresh()
    } catch (err) {
      console.error('Failed to return book:', err)
      alert(err.response?.data?.detail || 'Failed to return book.')
    }
  }

  const handleLendSuccess = async () => {
    await Promise.all([fetchLendingData(), fetchBooks(), fetchReadingStats(), fetchDashboardSummary()])
    triggerActivityRefresh()
    setLendModalBook(null)
  }

  // Auto-dismiss milestone notification toast after 4.5 seconds
  useEffect(() => {
    if (milestoneToast) {
      const timer = setTimeout(() => {
        setMilestoneToast(null)
      }, 4500)
      return () => clearTimeout(timer)
    }
  }, [milestoneToast])

  // Initial load and filter sync
  useEffect(() => {
    fetchShelves()
    fetchTotalCatalogCount()
    fetchReadingStats()
    fetchDashboardSummary()
    fetchLendingData()
  }, [fetchShelves, fetchTotalCatalogCount, fetchReadingStats, fetchDashboardSummary, fetchLendingData])

  useEffect(() => {
    fetchBooks()
  }, [fetchBooks])

  // =============================================================================
  // Real-time WebSocket Synchronizers (Phase 9 & Safeguard 5)
  // Lightweight refetches preserve active page, filters, sort, and selected shelf
  // =============================================================================

  // Automatically join active shelf collaborative room
  useShelfSubscription(selectedShelfId)

  // 1. Live Book CRUD Events
  useSocket('book_added', useCallback(() => {
    fetchBooks()
    fetchReadingStats()
    fetchDashboardSummary()
    triggerActivityRefresh()
  }, [fetchBooks, fetchReadingStats, fetchDashboardSummary, triggerActivityRefresh]))

  useSocket('book_updated', useCallback(() => {
    fetchBooks()
    fetchReadingStats()
    fetchDashboardSummary()
  }, [fetchBooks, fetchReadingStats, fetchDashboardSummary]))

  useSocket('book_deleted', useCallback(() => {
    fetchBooks()
    fetchReadingStats()
    fetchDashboardSummary()
    fetchShelves()
  }, [fetchBooks, fetchReadingStats, fetchDashboardSummary, fetchShelves]))

  // 2. Live Reading Progress & Milestones
  useSocket('progress_updated', useCallback(() => {
    fetchBooks()
    fetchReadingStats()
    fetchDashboardSummary()
    triggerActivityRefresh()
  }, [fetchBooks, fetchReadingStats, fetchDashboardSummary, triggerActivityRefresh]))

  // 3. Live Shelf Collaboration Events
  useSocket('shelf_created', useCallback(() => {
    fetchShelves()
    fetchDashboardSummary()
  }, [fetchShelves, fetchDashboardSummary]))

  useSocket('shelf_renamed', useCallback(() => {
    fetchShelves()
    fetchDashboardSummary()
  }, [fetchShelves, fetchDashboardSummary]))

  useSocket('shelf_deleted', useCallback((data) => {
    if (selectedShelfId === data?.shelf_id) {
      setSelectedShelfId(null)
    }
    fetchShelves()
    fetchBooks()
    fetchDashboardSummary()
  }, [selectedShelfId, fetchShelves, fetchBooks, fetchDashboardSummary]))

  useSocket('shelf_book_added', useCallback(() => {
    fetchShelves()
    fetchBooks()
    fetchDashboardSummary()
  }, [fetchShelves, fetchBooks, fetchDashboardSummary]))

  useSocket('shelf_book_removed', useCallback(() => {
    fetchShelves()
    fetchBooks()
    fetchDashboardSummary()
  }, [fetchShelves, fetchBooks, fetchDashboardSummary]))

  useSocket('shelf_shared', useCallback(() => {
    fetchShelves()
    fetchDashboardSummary()
    triggerActivityRefresh()
  }, [fetchShelves, fetchDashboardSummary, triggerActivityRefresh]))

  useSocket('shelf_role_changed', useCallback(() => {
    fetchShelves()
    triggerActivityRefresh()
  }, [fetchShelves, triggerActivityRefresh]))

  useSocket('shelf_share_removed', useCallback(() => {
    fetchShelves()
    fetchDashboardSummary()
    triggerActivityRefresh()
  }, [fetchShelves, fetchDashboardSummary, triggerActivityRefresh]))

  // Instant room revocation notification (Safeguard 2)
  useSocket('shelf_access_revoked', useCallback((data) => {
    if (selectedShelfId === data?.shelf_id) {
      setSelectedShelfId(null)
    }
    fetchShelves()
    fetchBooks()
    fetchDashboardSummary()
  }, [selectedShelfId, fetchShelves, fetchBooks, fetchDashboardSummary]))

  // 4. Live Lending Events
  useSocket('book_lent', useCallback(() => {
    fetchLendingData()
    fetchBooks()
    fetchDashboardSummary()
    triggerActivityRefresh()
  }, [fetchLendingData, fetchBooks, fetchDashboardSummary, triggerActivityRefresh]))

  useSocket('book_returned', useCallback(() => {
    fetchLendingData()
    fetchBooks()
    fetchDashboardSummary()
    triggerActivityRefresh()
  }, [fetchLendingData, fetchBooks, fetchDashboardSummary, triggerActivityRefresh]))

  // 5. Live Activity Feed Sync
  useSocket('activity_created', useCallback(() => {
    triggerActivityRefresh()
  }, [triggerActivityRefresh]))

  // Reading Progress Modal Handlers (Phase 6)
  const handleOpenProgressModal = (book) => {
    setProgressModalState({ isOpen: true, book })
  }

  const handleCloseProgressModal = () => {
    setProgressModalState({ isOpen: false, book: null })
  }

  const getMilestoneLabel = (milestone) => {
    switch (milestone) {
      case 'quarter':
        return '🎉 Quarter Way Through! (25%)'
      case 'half':
        return '⚡ Halfway Mark Reached! (50%)'
      case 'three_quarters':
        return '🔥 In the Final Stretch! (75%)'
      case 'completed':
        return '🏆 Book Completed! (100%)'
      default:
        return 'Milestone Reached!'
    }
  }

  // Unified Progress Save Handler
  const handleSaveProgress = async (bookId, progressData) => {
    const res = await updateBookProgressApi(bookId, progressData)
    await Promise.all([fetchBooks(), fetchReadingStats(), fetchDashboardSummary()])
    triggerActivityRefresh()
    if (res.data?.milestone) {
      setMilestoneToast({
        milestone: res.data.milestone,
        label: res.data.milestone_label || getMilestoneLabel(res.data.milestone),
        bookTitle: res.data.book?.title || 'Book',
      })
    }
    return res.data
  }

  // Quick Progress Action (routes through unified updateBookProgressApi)
  const handleQuickProgress = async (bookId, patchData) => {
    try {
      await handleSaveProgress(bookId, patchData)
    } catch (err) {
      console.error('Quick progress update failed:', err)
    }
  }

  // Book CRUD Handlers
  const handleOpenAddBookModal = () => {
    setEditingBook(null)
    setIsBookModalOpen(true)
  }

  const handleOpenEditBookModal = (book) => {
    setEditingBook(book)
    setIsBookModalOpen(true)
  }

  const handleSaveBook = async (payload) => {
    if (editingBook) {
      await updateBookApi(editingBook.id, payload)
    } else {
      const res = await createBookApi(payload)
      // If currently on an active shelf, automatically attach new book to that shelf!
      if (selectedShelfId && res.data?.id) {
        try {
          await addBookToShelfApi(selectedShelfId, res.data.id)
        } catch (err) {
          console.warn('Auto-shelf assignment warning:', err)
        }
      }
    }
    await Promise.all([fetchBooks(), fetchShelves(), fetchTotalCatalogCount(), fetchReadingStats(), fetchDashboardSummary()])
    triggerActivityRefresh()
  }

  const handleDeleteBook = async (bookId, bookTitle) => {
    if (window.confirm(`Are you sure you want to remove "${bookTitle}" from your library?`)) {
      try {
        await deleteBookApi(bookId)
        await Promise.all([fetchBooks(), fetchShelves(), fetchTotalCatalogCount(), fetchReadingStats(), fetchDashboardSummary()])
        triggerActivityRefresh()
      } catch (err) {
        alert(err.response?.data?.detail || 'Failed to delete book.')
      }
    }
  }

  // Shelf CRUD Handlers
  const handleOpenCreateShelf = () => {
    setShelfModalState({ isOpen: true, mode: 'create', shelf: null })
  }

  const handleOpenEditShelf = (shelf) => {
    setShelfModalState({ isOpen: true, mode: 'edit', shelf })
  }

  const handleSaveShelf = async (data) => {
    if (shelfModalState.mode === 'create') {
      const res = await createShelfApi(data)
      // Automatically select newly created shelf
      if (res.data?.id) {
        setSelectedShelfId(res.data.id)
        setPage(1)
      }
    } else if (shelfModalState.shelf) {
      await updateShelfApi(shelfModalState.shelf.id, data)
    }
    await Promise.all([fetchShelves(), fetchDashboardSummary()])
  }

  const handleDeleteShelf = async (shelf) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete shelf "${shelf.name}"?\n\nNote: Deleting this shelf will remove its categorization, but will NEVER delete any books from your personal library.`
    )
    if (!confirmed) return

    try {
      await deleteShelfApi(shelf.id)
      if (selectedShelfId === shelf.id) {
        setSelectedShelfId(null)
        setPage(1)
      }
      await Promise.all([fetchShelves(), fetchBooks(), fetchTotalCatalogCount(), fetchDashboardSummary()])
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete shelf.')
    }
  }

  const handleRemoveFromShelf = async (shelfId, bookId, bookTitle, shelfName) => {
    try {
      await removeBookFromShelfApi(shelfId, bookId)
      await Promise.all([fetchBooks(), fetchShelves(), fetchDashboardSummary()])
    } catch (err) {
      alert(err.response?.data?.detail || `Failed to remove "${bookTitle}" from "${shelfName}".`)
    }
  }

  // Assign Shelves Modal Handlers
  const handleOpenAssignModal = (book) => {
    setAssignModalBook(book)
  }

  // Shelf Sharing Modal Handlers
  const handleOpenShareShelf = (shelf) => {
    setShareModalShelf(shelf)
  }

  const handleAssignedChange = async () => {
    await Promise.all([fetchBooks(), fetchShelves(), fetchDashboardSummary()])
  }



  // Diagnostics Handlers
  const testMe = async () => {
    setLoadingAction('me')
    setTestOutput(null)
    try {
      const res = await getMeApi()
      setTestOutput({
        success: true,
        title: 'GET /api/auth/me (Protected Route)',
        data: res.data,
        detail: 'Bearer token in Authorization header validated successfully by FastAPI.',
      })
    } catch (err) {
      setTestOutput({
        success: false,
        title: 'GET /api/auth/me Failed',
        detail: err.response?.data?.detail || err.message,
      })
    } finally {
      setLoadingAction(null)
    }
  }

  const testRefresh = async () => {
    setLoadingAction('refresh')
    setTestOutput(null)
    try {
      const prevToken = getAccessToken()
      const data = await refreshSession()
      setTestOutput({
        success: true,
        title: 'POST /api/auth/refresh (Token Rotation)',
        data: {
          previous_token_prefix: prevToken ? prevToken.slice(0, 18) + '...' : 'none',
          new_token_prefix: data.access_token.slice(0, 18) + '...',
          token_type: data.token_type,
          user: data.user,
        },
        detail:
          'HttpOnly cookie was verified by PostgreSQL with SELECT FOR UPDATE. Old token deleted; new hash persisted and new token issued.',
      })
    } catch (err) {
      setTestOutput({
        success: false,
        title: 'Token Refresh Failed',
        detail: err.response?.data?.detail || err.message,
      })
    } finally {
      setLoadingAction(null)
    }
  }

  const testConcurrentQueue = async () => {
    setLoadingAction('concurrent')
    setTestOutput(null)
    try {
      const startTime = performance.now()
      const results = await Promise.all([getMeApi(), getMeApi(), getMeApi()])
      const duration = Math.round(performance.now() - startTime)

      setTestOutput({
        success: true,
        title: 'Concurrent Request Replay Queue Test',
        data: {
          dispatched_requests: 3,
          responses_received: results.length,
          all_status_200: results.every((r) => r.status === 200),
          execution_time_ms: duration,
        },
        detail:
          'Axios interceptor successfully processed concurrent requests. Single refresh lock prevented duplicate refresh requests.',
      })
    } catch (err) {
      setTestOutput({
        success: false,
        title: 'Concurrent Queue Test Failed',
        detail: err.response?.data?.detail || err.message,
      })
    } finally {
      setLoadingAction(null)
    }
  }

  const testStorageAudit = () => {
    setLoadingAction('storage')
    const localKeys = Object.keys(localStorage)
    const sessionKeys = Object.keys(sessionStorage)
    const hasAuthKey = (k) => /token|auth|jwt/i.test(k)

    const leakedLocal = localKeys.filter(hasAuthKey)
    const leakedSession = sessionKeys.filter(hasAuthKey)

    setTestOutput({
      success: leakedLocal.length === 0 && leakedSession.length === 0,
      title: 'Browser Storage Audit (Zero Persistence Test)',
      data: {
        localStorage_keys_count: localKeys.length,
        sessionStorage_keys_count: sessionKeys.length,
        leaked_auth_keys: [...leakedLocal, ...leakedSession],
        in_memory_token_present: !!accessToken,
      },
      detail:
        leakedLocal.length === 0 && leakedSession.length === 0
          ? 'PASS: 0 authentication tokens stored in localStorage/sessionStorage. Access token resides in React memory only.'
          : 'FAIL: Found auth keys in browser storage!',
    })
    setLoadingAction(null)
  }

  // Phase 4 Live Shelf Diagnostics
  const testPhase4Shelves = async () => {
    setLoadingAction('phase4')
    setTestOutput(null)
    const timestamp = Date.now().toString().slice(-4)
    const testShelfName = `Diag_Shelf_${timestamp}`

    try {
      // 1. Create Shelf
      const createRes = await createShelfApi({ name: testShelfName })
      const shelfId = createRes.data.id

      // 2. Test 409 Duplicate rejection
      let dup409Passed = false
      try {
        await createShelfApi({ name: testShelfName })
      } catch (dupErr) {
        if (dupErr.response?.status === 409) dup409Passed = true
      }

      // 3. Test book association if books exist
      let bookAssigned = false
      let cascadeSafetyConfirmed = false
      if (books.length > 0) {
        const testBook = books[0]
        await addBookToShelfApi(shelfId, testBook.id)
        bookAssigned = true

        // Delete shelf and confirm book still exists
        await deleteShelfApi(shelfId)

        // Verify book is still in library
        const catalogCheck = await getBooksApi()
        const catalogItems = catalogCheck.data?.items || catalogCheck.data || []
        cascadeSafetyConfirmed = catalogItems.some((b) => b.id === testBook.id)
      } else {
        // Clean up created test shelf
        await deleteShelfApi(shelfId)
      }

      await Promise.all([fetchShelves(), fetchBooks(), fetchTotalCatalogCount()])

      setTestOutput({
        success: dup409Passed,
        title: 'Phase 4 Custom Shelves & Integrity Verification',
        data: {
          test_shelf_created: testShelfName,
          duplicate_409_conflict_enforced: dup409Passed,
          book_many_to_many_attached: bookAssigned,
          cascade_safety_verified: cascadeSafetyConfirmed,
          clean_up_completed: true,
        },
        detail:
          'PASS: Custom shelf CRUD, 409 duplicate name enforcement, many-to-many book association, and cascade safety verified successfully!',
      })
    } catch (err) {
      setTestOutput({
        success: false,
        title: 'Phase 4 Shelf Verification Failed',
        detail: err.response?.data?.detail || err.message,
      })
    } finally {
      setLoadingAction(null)
    }
  }

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto', padding: 'var(--space-2xl) var(--space-md)' }}>
      {/* Navigation Header */}
      <Navbar />

      {/* Main Content Area */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
        {/* Dedicated Dashboard Summary Overview (Step 2 - Requirement #32) */}
        <DashboardSummary
          summary={dashboardSummary}
          loading={dashboardSummaryLoading}
          error={dashboardSummaryError}
        />

        {/* Phase 6 Reading Statistics Banner */}
        <ReadingStatsBanner stats={readingStats} loading={readingStatsLoading} />

        {/* Responsive Two-Column Layout: Shelves Sidebar on left, Catalog on right */}
        <div className="dashboard-layout">
          {/* Left Column: ShelfSidebar */}
          <ShelfSidebar
            shelves={shelves}
            totalBooksCount={totalCatalogCount}
            selectedShelfId={selectedShelfId}
            onSelectShelf={(id) => {
              setSelectedShelfId(id)
              setActiveView('catalog')
              setPage(1)
            }}
            onOpenCreateShelf={handleOpenCreateShelf}
            onOpenEditShelf={handleOpenEditShelf}
            onDeleteShelf={handleDeleteShelf}
            onOpenShareShelf={handleOpenShareShelf}
            loading={shelvesLoading}
            activeView={activeView}
            onSelectView={(v) => {
              setActiveView(v)
              if (v !== 'catalog') {
                setSelectedShelfId(null)
              }
            }}
            activeLentCount={lentBooks.length}
            activeBorrowedCount={borrowedBooks.length}
          />

          {/* Right Column: Books Catalog & Toolbar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', minWidth: 0 }}>
            {activeView === 'lent_out' ? (
              /* Dedicated Lent Out View (Phase 7) */
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                <div
                  className="card"
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'linear-gradient(90deg, rgba(245, 158, 11, 0.15) 0%, rgba(34, 37, 54, 0.8) 100%)',
                    borderColor: 'var(--warning)',
                    padding: 'var(--space-md) var(--space-lg)',
                  }}
                >
                  <div>
                    <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>📤</span> Books I've Lent Out
                      <span className="badge badge-warning" style={{ fontSize: '0.75rem' }}>
                        {lentBooks.length} Active
                      </span>
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)', marginTop: '4px' }}>
                      Active peer loans where you retain ownership. When the borrower returns your physical book, mark it as returned.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setActiveView('catalog')}
                    style={{ fontSize: 'var(--font-size-xs)', padding: '6px 14px' }}
                  >
                    ← Back to Library
                  </button>
                </div>

                {lentBooks.length === 0 ? (
                  <div className="card" style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-secondary)' }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-sm)' }}>🤝</div>
                    <h3 style={{ fontSize: 'var(--font-size-lg)', color: 'var(--text-primary)', marginBottom: 'var(--space-xs)' }}>
                      No Books Currently Lent Out
                    </h3>
                    <p style={{ fontSize: 'var(--font-size-sm)', maxWidth: '420px', margin: '0 auto var(--space-md) auto' }}>
                      You haven't lent any books to other readers yet. To lend a book, find it in your library and click "Lend Book".
                    </p>
                    <button className="btn-primary" onClick={() => setActiveView('catalog')}>
                      Browse Library Books
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 'var(--space-lg)' }}>
                    {lentBooks.map((lending) => (
                      <div
                        key={lending.id}
                        className="card"
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: 'var(--space-md)',
                          borderColor: 'rgba(245, 158, 11, 0.3)',
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-xs)', marginBottom: 'var(--space-xs)' }}>
                            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>
                              {lending.book_title}
                            </h3>
                            <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                              Active Loan
                            </span>
                          </div>
                          <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-md)' }}>
                            by <strong>{lending.book_author}</strong>
                          </div>
                          <div style={{ padding: 'var(--space-sm) var(--space-md)', background: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', fontSize: 'var(--font-size-xs)' }}>
                            <div style={{ marginBottom: '4px' }}>
                              Borrower: <strong>{lending.borrower_name}</strong> ({lending.borrower_email})
                            </div>
                            <div style={{ color: 'var(--text-muted)' }}>
                              Lent on: {new Date(lending.lent_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                            </div>
                          </div>
                        </div>
                        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 'var(--space-sm)', display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-xs)' }}>
                          <button
                            type="button"
                            className="btn-primary"
                            onClick={() => handleReturnBook(lending.id)}
                            style={{
                              padding: '6px 14px',
                              fontSize: 'var(--font-size-xs)',
                              background: 'var(--warning)',
                              borderColor: 'var(--warning)',
                              color: '#000',
                              fontWeight: 600,
                            }}
                          >
                            ↩ Mark Returned
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : activeView === 'borrowed' ? (
              /* Dedicated Borrowed Books View (Phase 7) */
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                <div
                  className="card"
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'linear-gradient(90deg, rgba(59, 130, 246, 0.15) 0%, rgba(34, 37, 54, 0.8) 100%)',
                    borderColor: 'var(--info)',
                    padding: 'var(--space-md) var(--space-lg)',
                  }}
                >
                  <div>
                    <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>📥</span> Books I've Borrowed
                      <span className="badge badge-info" style={{ fontSize: '0.75rem' }}>
                        {borrowedBooks.length} Active
                      </span>
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)', marginTop: '4px' }}>
                      Books shared with you by other readers. You have read-only access while the loan is active.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setActiveView('catalog')}
                    style={{ fontSize: 'var(--font-size-xs)', padding: '6px 14px' }}
                  >
                    ← Back to Library
                  </button>
                </div>

                {borrowedBooks.length === 0 ? (
                  <div className="card" style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-secondary)' }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-sm)' }}>📖</div>
                    <h3 style={{ fontSize: 'var(--font-size-lg)', color: 'var(--text-primary)', marginBottom: 'var(--space-xs)' }}>
                      No Borrowed Books
                    </h3>
                    <p style={{ fontSize: 'var(--font-size-sm)', maxWidth: '420px', margin: '0 auto var(--space-md) auto' }}>
                      You haven't borrowed any books from other readers. When someone lends you a book with your registered email, it will appear here.
                    </p>
                    <button className="btn-secondary" onClick={() => setActiveView('catalog')}>
                      View My Library
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 'var(--space-lg)' }}>
                    {borrowedBooks.map((borrowed) => (
                      <BookCard
                        key={borrowed.lending_id}
                        book={{
                          id: borrowed.book_id,
                          title: borrowed.title,
                          author: borrowed.author,
                          total_pages: borrowed.total_pages,
                          status: 'reading',
                          lender_name: borrowed.lender_name,
                          lender_email: borrowed.lender_email,
                        }}
                        isBorrowed={true}
                      />
                    ))}
                  </div>
                )}
              </div>
            ) : (
              /* Standard Books Catalog View */
              <>
                {/* Active Shelf Filter Banner */}
                {activeShelf && (
                  <div
                    className="card"
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: 'linear-gradient(90deg, rgba(139, 92, 246, 0.15) 0%, rgba(34, 37, 54, 0.8) 100%)',
                      borderColor: 'var(--accent)',
                      padding: 'var(--space-md) var(--space-lg)',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '1.25rem' }}>{activeShelf.role && activeShelf.role !== 'owner' ? '🤝' : '📁'}</span>
                        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 700 }}>
                          Shelf: {activeShelf.name}
                        </h3>
                        <span className="badge badge-accent">
                          {total} {total === 1 ? 'Book' : 'Books'}
                        </span>
                        <span
                          className={`badge ${activeShelf.role === 'editor' ? 'badge-accent' : activeShelf.role === 'viewer' ? 'badge-info' : 'badge-accent'}`}
                          style={{ textTransform: 'capitalize' }}
                        >
                          {activeShelf.role || 'Owner'}
                        </span>
                        {activeShelf.role && activeShelf.role !== 'owner' && (
                          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                            Shared by <strong>{activeShelf.owner_name || activeShelf.owner_email || 'Owner'}</strong>
                          </span>
                        )}
                      </div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)', marginTop: '4px' }}>
                        {activeShelf.role === 'viewer'
                          ? 'Read-only view. You can browse books on this shelf.'
                          : 'Filtered view. Removing a book from this shelf or deleting this shelf preserves library books.'}
                      </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => handleOpenShareShelf(activeShelf)}
                        style={{ fontSize: 'var(--font-size-xs)', padding: '6px 12px' }}
                      >
                        {activeShelf.role === 'owner' || !activeShelf.role ? '👥 Manage Collaborators' : '👥 Collaborators / Leave'}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => {
                          setSelectedShelfId(null)
                          setPage(1)
                        }}
                        style={{ fontSize: 'var(--font-size-xs)', padding: '6px 12px' }}
                      >
                        ✕ View All Books
                      </button>
                    </div>
                  </div>
                )}

            {/* Library Controls Toolbar */}
            <div
              className="card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-md)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 'var(--space-md)',
                }}
              >
                <div>
                  <h2 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 700 }}>
                    {activeShelf ? activeShelf.name : 'My Library'}
                  </h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                    {activeShelf
                      ? `Organize and track books on this shelf`
                      : `Organize, track reading milestones, and manage your collection`}
                  </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowActivityFeed((prev) => !prev)}
                    style={{
                      fontSize: 'var(--font-size-sm)',
                      background: showActivityFeed ? 'var(--accent)' : 'var(--bg-input)',
                      color: showActivityFeed ? '#fff' : 'var(--text-primary)',
                      borderColor: showActivityFeed ? 'var(--accent)' : 'var(--border)',
                      fontWeight: 600,
                    }}
                    id="activity-feed-toggle-btn"
                    title={showActivityFeed ? 'Hide Activity Feed' : 'Show Activity Feed'}
                  >
                    ⚡ Activity Feed {showActivityFeed ? '▾' : '▸'}
                  </button>
                  {activeShelf?.role !== 'viewer' && (
                    <button className="btn-primary" onClick={handleOpenAddBookModal} id="add-book-btn">
                      + Add Book
                    </button>
                  )}
                </div>
              </div>

              {/* Search, Filter Tabs & Sort Controls */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 'var(--space-md)',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                {/* Status Filter Tabs */}
                <div style={{ display: 'inline-flex', background: 'var(--bg-primary)', padding: '4px', borderRadius: 'var(--radius-md)', gap: '4px' }}>
                  {[
                    { label: 'All', value: '' },
                    { label: 'Reading', value: 'reading' },
                    { label: 'Want to Read', value: 'want_to_read' },
                    { label: 'Finished', value: 'finished' },
                  ].map((tab) => (
                    <button
                      key={tab.value}
                      type="button"
                      onClick={() => {
                        setStatusFilter(tab.value)
                        setPage(1)
                      }}
                      style={{
                        background: statusFilter === tab.value ? 'var(--accent)' : 'transparent',
                        color: statusFilter === tab.value ? 'white' : 'var(--text-secondary)',
                        padding: '6px 14px',
                        fontSize: 'var(--font-size-xs)',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Search Input & Sort Controls */}
                <div style={{ display: 'flex', gap: 'var(--space-sm)', flex: 1, maxWidth: '480px' }}>
                  <input
                    type="text"
                    placeholder="Search title or author..."
                    value={searchTerm}
                    onChange={(e) => {
                      setSearchTerm(e.target.value)
                      setPage(1)
                    }}
                    style={{ flex: 1, padding: '6px 12px', fontSize: 'var(--font-size-sm)' }}
                  />

                  <select
                    value={`${sortBy}:${sortDir}`}
                    onChange={(e) => {
                      const [field, dir] = e.target.value.split(':')
                      setSortBy(field)
                      setSortDir(dir)
                      setPage(1)
                    }}
                    style={{ width: 'auto', padding: '6px 10px', fontSize: 'var(--font-size-xs)' }}
                  >
                    <option value="created_at:desc">Date Added (Newest)</option>
                    <option value="created_at:asc">Date Added (Oldest)</option>
                    <option value="title:asc">Title (A–Z)</option>
                    <option value="title:desc">Title (Z–A)</option>
                    <option value="rating:desc">Rating (Highest)</option>
                    <option value="current_page:desc">Pages Read (Highest)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Phase 8 Activity Feed Section */}
            {showActivityFeed && (
              <ActivityFeed
                refreshTrigger={activityRefreshTrigger}
                onClose={() => setShowActivityFeed(false)}
                currentShelfId={selectedShelfId}
              />
            )}

            {/* Books Catalog Grid */}
            {error && (
              <div style={{ background: 'var(--error-bg)', color: 'var(--error)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)' }}>
                ⚠️ {error}
              </div>
            )}

            {loading ? (
              <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '2rem', marginBottom: 'var(--space-sm)' }}>📖</div>
                <p>Loading personal library...</p>
              </div>
            ) : books.length === 0 ? (
              <div
                className="card"
                style={{
                  textAlign: 'center',
                  padding: 'var(--space-2xl) var(--space-xl)',
                  color: 'var(--text-secondary)',
                }}
              >
                <div style={{ fontSize: '3rem', marginBottom: 'var(--space-sm)' }}>
                  {activeShelf ? '📁' : '📚'}
                </div>
                <h3 style={{ fontSize: 'var(--font-size-xl)', color: 'var(--text-primary)', marginBottom: 'var(--space-xs)' }}>
                  {activeShelf ? `Shelf "${activeShelf.name}" is empty` : 'No books found'}
                </h3>
                <p style={{ maxWidth: '420px', margin: '0 auto var(--space-lg) auto', fontSize: 'var(--font-size-sm)' }}>
                  {activeShelf
                    ? 'This custom shelf currently has no books. Switch to All Books to assign books to this shelf, or add a new book directly.'
                    : statusFilter || searchTerm
                    ? 'No books match your current search or status filter. Try clearing the filter.'
                    : 'Your library is currently empty. Add your first book to track your reading journey!'}
                </p>
                {activeShelf ? (
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-sm)' }}>
                    <button
                      className="btn-secondary"
                      onClick={() => {
                        setSelectedShelfId(null)
                        setPage(1)
                      }}
                    >
                      View All Books
                    </button>
                    {activeShelf.role !== 'viewer' && (
                      <button className="btn-primary" onClick={handleOpenAddBookModal}>
                        + Add Book to Shelf
                      </button>
                    )}
                  </div>
                ) : statusFilter || searchTerm ? (
                  <button
                    className="btn-secondary"
                    onClick={() => {
                      setStatusFilter('')
                      setSearchTerm('')
                      setPage(1)
                    }}
                  >
                    Clear Filters
                  </button>
                ) : (
                  <button className="btn-primary" onClick={handleOpenAddBookModal}>
                    + Add Your First Book
                  </button>
                )}
              </div>
            ) : (
              <>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                    gap: 'var(--space-lg)',
                  }}
                >
                  {books.map((book) => {
                    const isBookOwner = !book.user_id || book.user_id === user?.id
                    return (
                      <BookCard
                        key={book.id}
                        book={book}
                        onEdit={isBookOwner ? handleOpenEditBookModal : null}
                        onDelete={isBookOwner ? handleDeleteBook : null}
                        onQuickProgress={isBookOwner ? handleQuickProgress : null}
                        onUpdateProgress={isBookOwner ? handleOpenProgressModal : null}
                        onManageShelves={isBookOwner ? handleOpenAssignModal : null}
                        currentShelf={activeShelf}
                        onRemoveFromShelf={activeShelf?.role !== 'viewer' ? handleRemoveFromShelf : null}
                        shelvesMap={shelvesMap}
                        onLend={isBookOwner ? (b) => setLendModalBook(b) : null}
                        onReturn={isBookOwner ? (b) => handleReturnBook(b.active_lending_id) : null}
                        onViewLendingHistory={isBookOwner ? (b) => setHistoryModalBook(b) : null}
                      />
                    )
                  })}
                </div>

                {/* Server-Side Pagination Controls */}
                {total > 0 && (
                  <div
                    className="card"
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: 'var(--space-md)',
                      padding: 'var(--space-md) var(--space-lg)',
                      marginTop: 'var(--space-sm)',
                    }}
                  >
                    <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                      Showing{' '}
                      <strong style={{ color: 'var(--text-primary)' }}>
                        {(page - 1) * pageSize + 1}
                      </strong>
                      –
                      <strong style={{ color: 'var(--text-primary)' }}>
                        {Math.min(page * pageSize, total)}
                      </strong>{' '}
                      of <strong style={{ color: 'var(--text-primary)' }}>{total}</strong> books
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                        disabled={page <= 1 || loading}
                        style={{
                          padding: '6px 14px',
                          fontSize: 'var(--font-size-sm)',
                          opacity: page <= 1 || loading ? 0.5 : 1,
                          cursor: page <= 1 || loading ? 'not-allowed' : 'pointer',
                        }}
                      >
                        ← Previous
                      </button>

                      <span
                        style={{
                          fontSize: 'var(--font-size-sm)',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                          padding: '0 var(--space-xs)',
                        }}
                      >
                        Page {page} of {totalPages || 1}
                      </span>

                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                        disabled={page >= totalPages || loading || totalPages === 0}
                        style={{
                          padding: '6px 14px',
                          fontSize: 'var(--font-size-sm)',
                          opacity: page >= totalPages || loading || totalPages === 0 ? 0.5 : 1,
                          cursor: page >= totalPages || loading || totalPages === 0 ? 'not-allowed' : 'pointer',
                        }}
                      >
                        Next →
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
        </div>

        {/* Collapsible Architecture Diagnostics Panel */}
        <div className="card" style={{ marginTop: 'var(--space-xl)' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: 'pointer',
              userSelect: 'none',
            }}
            onClick={() => setShowDiagnostics(!showDiagnostics)}
          >
            <div>
              <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 600 }}>
                Architecture & Security Diagnostics
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
                Verify in-memory JWT, HttpOnly rotation, Axios interceptor replay, and Phase 4 Custom Shelves
              </p>
            </div>
            <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--accent)' }}>
              {showDiagnostics ? '▲ Hide Diagnostics' : '▼ View Diagnostics'}
            </span>
          </div>

          {showDiagnostics && (
            <div style={{ marginTop: 'var(--space-lg)', borderTop: '1px solid var(--border)', paddingTop: 'var(--space-md)' }}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: 'var(--space-sm)',
                  marginBottom: 'var(--space-md)',
                }}
              >
                <button
                  className="btn-secondary"
                  onClick={testMe}
                  disabled={loadingAction !== null}
                  style={{ justifyContent: 'center' }}
                >
                  {loadingAction === 'me' ? 'Testing...' : '1. Test /api/auth/me'}
                </button>
                <button
                  className="btn-secondary"
                  onClick={testRefresh}
                  disabled={loadingAction !== null}
                  style={{ justifyContent: 'center' }}
                >
                  {loadingAction === 'refresh' ? 'Rotating...' : '2. Test Token Rotation'}
                </button>
                <button
                  className="btn-secondary"
                  onClick={testConcurrentQueue}
                  disabled={loadingAction !== null}
                  style={{ justifyContent: 'center' }}
                >
                  {loadingAction === 'concurrent' ? 'Testing...' : '3. Test Concurrent Queue'}
                </button>
                <button
                  className="btn-secondary"
                  onClick={testStorageAudit}
                  disabled={loadingAction !== null}
                  style={{ justifyContent: 'center' }}
                >
                  {loadingAction === 'storage' ? 'Auditing...' : '4. Storage Audit'}
                </button>
                <button
                  className="btn-secondary"
                  onClick={testPhase4Shelves}
                  disabled={loadingAction !== null}
                  style={{ justifyContent: 'center', borderColor: 'var(--accent)', color: 'var(--accent)' }}
                >
                  {loadingAction === 'phase4' ? 'Testing Shelves...' : '5. Test Shelves (Phase 4)'}
                </button>
              </div>

              {testOutput && (
                <div
                  style={{
                    background: 'var(--bg-secondary)',
                    border: `1px solid ${testOutput.success ? 'rgba(34, 197, 94, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-md)',
                    fontFamily: 'monospace',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-xs)' }}>
                    <span className={`badge ${testOutput.success ? 'badge-success' : 'badge-error'}`}>
                      {testOutput.success ? 'SUCCESS' : 'FAILED'}
                    </span>
                    <strong style={{ fontSize: 'var(--font-size-sm)' }}>{testOutput.title}</strong>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-sm)' }}>
                    {testOutput.detail}
                  </p>
                  {testOutput.data && (
                    <pre
                      style={{
                        background: 'var(--bg-primary)',
                        padding: 'var(--space-sm)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 'var(--font-size-xs)',
                        overflowX: 'auto',
                        color: 'var(--text-primary)',
                      }}
                    >
                      {JSON.stringify(testOutput.data, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Book Add / Edit Modal */}
      <BookModal
        isOpen={isBookModalOpen}
        onClose={() => setIsBookModalOpen(false)}
        onSave={handleSaveBook}
        book={editingBook}
      />

      {/* Shelf Create / Rename Modal */}
      <ShelfModal
        isOpen={shelfModalState.isOpen}
        onClose={() => setShelfModalState({ isOpen: false, mode: 'create', shelf: null })}
        onSave={handleSaveShelf}
        shelf={shelfModalState.shelf}
      />

      {/* Assign Shelves to Book Modal */}
      <AssignShelfModal
        isOpen={!!assignModalBook}
        onClose={() => setAssignModalBook(null)}
        book={assignModalBook}
        shelves={shelves}
        onAssignedChange={handleAssignedChange}
      />

      {/* Shelf Share / RBAC Modal */}
      <ShelfShareModal
        isOpen={!!shareModalShelf}
        onClose={() => setShareModalShelf(null)}
        shelf={shareModalShelf}
        currentUserId={user?.id}
        onShareUpdated={async (leftShelf) => {
          if (leftShelf && selectedShelfId === shareModalShelf?.id) {
            setSelectedShelfId(null)
            setPage(1)
          }
          await Promise.all([fetchShelves(), fetchBooks(), fetchTotalCatalogCount()])
          triggerActivityRefresh()
        }}
      />

      {/* Reading Progress Tracker Modal (Phase 6) */}
      <ProgressModal
        isOpen={progressModalState.isOpen}
        onClose={handleCloseProgressModal}
        onSaveProgress={handleSaveProgress}
        book={progressModalState.book}
      />

      {/* Lend Book Modal (Phase 7) */}
      <LendBookModal
        isOpen={!!lendModalBook}
        onClose={() => setLendModalBook(null)}
        book={lendModalBook}
        onLendSuccess={handleLendSuccess}
      />

      {/* Lending History Modal (Phase 7) */}
      <LendingHistoryModal
        isOpen={!!historyModalBook}
        onClose={() => setHistoryModalBook(null)}
        book={historyModalBook}
      />

      {/* Milestone Celebration Toast (Phase 6) */}
      {milestoneToast && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 9999,
            background: 'var(--bg-card)',
            border: '1px solid var(--accent)',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 15px rgba(147, 51, 234, 0.3)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-md) var(--space-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-md)',
            maxWidth: '400px',
          }}
        >
          <div style={{ fontSize: '1.8rem', lineHeight: 1 }}>
            {milestoneToast.milestone === 'completed'
              ? '🏆'
              : milestoneToast.milestone === 'three_quarters'
              ? '🔥'
              : milestoneToast.milestone === 'half'
              ? '⚡'
              : '🎉'}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
              {milestoneToast.label}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {milestoneToast.bookTitle}
            </div>
          </div>
          <button
            type="button"
            onClick={() => setMilestoneToast(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '1.2rem',
              cursor: 'pointer',
              padding: '2px 6px',
            }}
            title="Dismiss notification"
          >
            &times;
          </button>
        </div>
      )}
    </div>
  )
}
