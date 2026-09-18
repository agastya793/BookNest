import api from './client'

/**
 * Books API Service
 * Handles personal catalog CRUD operations for the authenticated user.
 */

/**
 * Fetch books belonging to the authenticated user.
 * @param {Object} [params] - Optional query parameters.
 * @param {string} [params.status] - Filter by: 'want_to_read', 'reading', 'finished'.
 * @param {string} [params.search] - Search keyword across title and author.
 * @param {string} [params.sort_by] - Sort column: 'created_at', 'updated_at', 'title', 'author', 'rating', 'current_page'.
 * @param {string} [params.sort_dir] - Sort direction: 'asc', 'desc'.
 */
export const getBooksApi = (params = {}) => {
  return api.get('/books', { params })
}

/**
 * Fetch details of a single book by ID.
 * @param {string} bookId - Book UUID.
 */
export const getBookApi = (bookId) => {
  return api.get(`/books/${bookId}`)
}

/**
 * Add a new book to the user's library.
 * @param {Object} bookData - Book creation payload.
 */
export const createBookApi = (bookData) => {
  return api.post('/books', bookData)
}

/**
 * Partially update a book.
 * @param {string} bookId - Book UUID.
 * @param {Object} bookData - Partial update payload.
 */
export const updateBookApi = (bookId, bookData) => {
  return api.patch(`/books/${bookId}`, bookData)
}

/**
 * Delete a book from the user's library.
 * @param {string} bookId - Book UUID.
 */
export const deleteBookApi = (bookId) => {
  return api.delete(`/books/${bookId}`)
}
