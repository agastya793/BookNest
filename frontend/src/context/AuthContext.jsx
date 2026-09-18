import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { setAccessToken as syncClientToken, setOnAuthFailure } from '../api/client'
import { signupApi, loginApi, refreshApi, logoutApi } from '../api/auth'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [accessToken, setAccessTokenState] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Synchronize token state with Axios client memory store
  const updateAccessToken = useCallback((token) => {
    syncClientToken(token)
    setAccessTokenState(token)
  }, [])

  // Clear auth state if refresh fails or session is revoked
  const handleAuthFailure = useCallback(() => {
    updateAccessToken(null)
    setUser(null)
  }, [updateAccessToken])

  useEffect(() => {
    setOnAuthFailure(handleAuthFailure)
  }, [handleAuthFailure])

  // Silent session restoration on startup via HttpOnly refresh_token cookie
  useEffect(() => {
    let isMounted = true

    const restoreSession = async () => {
      try {
        const response = await refreshApi()
        if (isMounted && response.data) {
          updateAccessToken(response.data.access_token)
          setUser(response.data.user)
        }
      } catch {
        // No valid or existing refresh cookie — user starts in logged-out state
        if (isMounted) {
          updateAccessToken(null)
          setUser(null)
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    restoreSession()

    return () => {
      isMounted = false
    }
  }, [updateAccessToken])

  // Log in existing user
  const login = async (email, password) => {
    setError(null)
    try {
      const response = await loginApi({ email, password })
      updateAccessToken(response.data.access_token)
      setUser(response.data.user)
      return response.data
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed. Please check your credentials.'
      setError(msg)
      throw new Error(msg)
    }
  }

  // Register new user
  const signup = async (name, email, password) => {
    setError(null)
    try {
      const response = await signupApi({ name, email, password })
      updateAccessToken(response.data.access_token)
      setUser(response.data.user)
      return response.data
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        (Array.isArray(err.response?.data?.detail)
          ? err.response.data.detail.map((e) => e.msg).join(', ')
          : 'Registration failed.')
      setError(msg)
      throw new Error(msg)
    }
  }

  // Log out and revoke refresh token in database & cookie
  const logout = async () => {
    try {
      await logoutApi()
    } catch (err) {
      console.warn('Logout API error:', err)
    } finally {
      updateAccessToken(null)
      setUser(null)
      setError(null)
    }
  }

  // Manual refresh helper (used in testing and explicit renewals)
  const refreshSession = async () => {
    try {
      const response = await refreshApi()
      updateAccessToken(response.data.access_token)
      setUser(response.data.user)
      return response.data
    } catch (err) {
      handleAuthFailure()
      throw err
    }
  }

  const value = {
    user,
    accessToken,
    loading,
    error,
    login,
    signup,
    logout,
    refreshSession,
    isAuthenticated: !!user,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext
