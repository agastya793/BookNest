import api from './client'

/**
 * Shelves API Service
 * Handles custom shelf collections and many-to-many book associations
 * for the authenticated user.
 */

/**
 * Fetch all shelves belonging to the authenticated user with book counts.
 * Uses LEFT OUTER JOIN on backend to include empty shelves (count = 0).
 */
export const getShelvesApi = () => {
  return api.get('/shelves')
}

/**
 * Fetch details of a single shelf including its associated books.
 * @param {string} shelfId - Shelf UUID.
 */
export const getShelfDetailApi = (shelfId) => {
  return api.get(`/shelves/${shelfId}`)
}

/**
 * Create a new custom shelf for the authenticated user.
 * @param {Object} data - Payload: { name: string }.
 */
export const createShelfApi = (data) => {
  return api.post('/shelves', data)
}

/**
 * Update / rename an existing custom shelf.
 * @param {string} shelfId - Shelf UUID.
 * @param {Object} data - Payload: { name: string }.
 */
export const updateShelfApi = (shelfId, data) => {
  return api.patch(`/shelves/${shelfId}`, data)
}

/**
 * Delete a custom shelf.
 * Associations in shelf_books are cascade deleted, leaving books intact.
 * @param {string} shelfId - Shelf UUID.
 */
export const deleteShelfApi = (shelfId) => {
  return api.delete(`/shelves/${shelfId}`)
}

/**
 * Assign a book to a custom shelf.
 * @param {string} shelfId - Shelf UUID.
 * @param {string} bookId - Book UUID.
 */
export const addBookToShelfApi = (shelfId, bookId) => {
  return api.post(`/shelves/${shelfId}/books`, { book_id: bookId })
}

/**
 * Remove a book from a custom shelf.
 * Association is removed, book remains intact in personal library.
 * @param {string} shelfId - Shelf UUID.
 * @param {string} bookId - Book UUID.
 */
export const removeBookFromShelfApi = (shelfId, bookId) => {
  return api.delete(`/shelves/${shelfId}/books/${bookId}`)
}

/**
 * Invite a collaborator to a custom shelf.
 * @param {string} shelfId - Shelf UUID.
 * @param {Object} data - Payload: { email: string, role: 'editor' | 'viewer' }.
 */
export const shareShelfApi = (shelfId, data) => {
  return api.post(`/shelves/${shelfId}/shares`, data)
}

/**
 * Fetch all collaborators assigned to a shelf.
 * @param {string} shelfId - Shelf UUID.
 */
export const getShelfSharesApi = (shelfId) => {
  return api.get(`/shelves/${shelfId}/shares`)
}

/**
 * Update a collaborator's role on a shelf.
 * @param {string} shelfId - Shelf UUID.
 * @param {string} shareId - ShelfShare UUID.
 * @param {string} role - Target role: 'editor' | 'viewer'.
 */
export const updateShelfShareRoleApi = (shelfId, shareId, role) => {
  return api.patch(`/shelves/${shelfId}/shares/${shareId}`, { role })
}

/**
 * Remove a collaborator from a shelf, or leave a shared shelf.
 * @param {string} shelfId - Shelf UUID.
 * @param {string} shareId - ShelfShare UUID.
 */
export const removeShelfShareApi = (shelfId, shareId) => {
  return api.delete(`/shelves/${shelfId}/shares/${shareId}`)
}

