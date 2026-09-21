import api from './client'

/**
 * Dashboard API Service
 * Fetches server-aggregated personal library summary metrics for the authenticated user.
 */
export const getDashboardSummaryApi = () => {
  return api.get('/dashboard/summary')
}
