import api from '../api/client'
import { useAuth } from '../context/AuthContext'

/**
 * Custom hook providing access to the configured Axios client instance
 * and authenticated user context.
 */
export const useApi = () => {
  const { user, isAuthenticated, logout } = useAuth()

  return {
    api,
    user,
    isAuthenticated,
    logout,
  }
}

export default useApi
