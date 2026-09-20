import api from './client'

/**
 * Lend an owned book to another user by email.
 * @param {Object} data - { book_id, borrower_email }
 */
export const lendBookApi = async (data) => {
  const response = await api.post('/lending', data)
  return response.data
}

/**
 * Return an active book loan (Book owner only).
 * @param {string} lendingId
 */
export const returnBookApi = async (lendingId) => {
  const response = await api.post(`/lending/${lendingId}/return`)
  return response.data
}

/**
 * List lending records available to current user.
 * @param {Object} params - { role: 'all'|'lender'|'borrower', status: 'all'|'active'|'returned' }
 */
export const getLendingsApi = async (params = {}) => {
  const response = await api.get('/lending', { params })
  return response.data
}

/**
 * List books currently borrowed by authenticated user.
 */
export const getBorrowedBooksApi = async () => {
  const response = await api.get('/lending/borrowed')
  return response.data
}

/**
 * Get read-only detail of a book borrowed by authenticated user.
 * @param {string} bookId
 */
export const getBorrowedBookDetailApi = async (bookId) => {
  const response = await api.get(`/lending/borrowed/${bookId}`)
  return response.data
}

/**
 * Get complete lending history for a specific owned book.
 * @param {string} bookId
 */
export const getBookLendingHistoryApi = async (bookId) => {
  const response = await api.get(`/lending/book/${bookId}`)
  return response.data
}
