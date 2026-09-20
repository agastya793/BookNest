import api from './client'

/**
 * Activity Feed API Service
 * Fetches chronologically ordered activity events accessible to the authenticated user.
 * Supports server-side pagination, action filtering, and shelf-scoped filtering.
 *
 * @param {Object} [params] - Query parameters
 * @param {number} [params.page=1] - 1-indexed page number
 * @param {number} [params.page_size=20] - Number of items per page (max 100)
 * @param {string} [params.action] - Optional action filter (e.g. book_added, status_changed, etc.)
 * @param {string} [params.shelf_id] - Optional shelf UUID filter
 */
export const getActivitiesApi = (params = {}) => {
  return api.get('/activities', { params })
}
