import axios from 'axios'

// In-memory access token storage (strictly React memory — NO localStorage or sessionStorage)
let memoryAccessToken = null

// Concurrency management for refresh requests
let isRefreshing = false
let failedQueue = []

// Optional listener for authentication failure (used by AuthContext to reset state)
let onAuthFailureCallback = null

export const setAccessToken = (token) => {
  memoryAccessToken = token
}

export const getAccessToken = () => {
  return memoryAccessToken
}

export const setOnAuthFailure = (callback) => {
  onAuthFailureCallback = callback
}

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Crucial: ensures HttpOnly refresh_token cookie is sent and received
})

// Request Interceptor: Attach in-memory Bearer token
api.interceptors.request.use(
  (config) => {
    if (memoryAccessToken && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${memoryAccessToken}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response Interceptor: 401 handling with single-request refresh, queueing, and anti-loop guards
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (!error.response || error.response.status !== 401) {
      return Promise.reject(error)
    }

    // Anti-loop protection:
    // 1. Do not intercept if request has already been retried
    // 2. Do not intercept login, signup, or refresh endpoint failures (avoids recursive refresh loops)
    const isAuthEndpoint =
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/signup') ||
      originalRequest.url?.includes('/auth/refresh')

    if (originalRequest._retry || isAuthEndpoint) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      // Refresh is already in progress: queue this request until the refresh finishes
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
        .catch((err) => {
          return Promise.reject(err)
        })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      // Attempt token rotation via HttpOnly cookie
      const response = await api.post('/auth/refresh')
      const newAccessToken = response.data.access_token

      setAccessToken(newAccessToken)
      processQueue(null, newAccessToken)

      // Replay original request with the freshly minted access token
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
      return api(originalRequest)
    } catch (refreshError) {
      // Refresh failed or expired: flush queue with error and wipe memory token
      processQueue(refreshError, null)
      setAccessToken(null)
      if (typeof onAuthFailureCallback === 'function') {
        onAuthFailureCallback()
      }
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

export default api
