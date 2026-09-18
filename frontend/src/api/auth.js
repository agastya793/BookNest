import api from './client'

/**
 * Authentication API Service Wrappers
 */

/**
 * Register a new user account.
 * Supports both signupApi({ name, email, password }) and signupApi(name, email, password).
 */
export const signupApi = (userDataOrName, email, password) => {
  const payload =
    typeof userDataOrName === 'object' && userDataOrName !== null
      ? userDataOrName
      : { name: userDataOrName, email, password }
  return api.post('/auth/signup', payload)
}

/**
 * Authenticate an existing user.
 * Supports both loginApi({ email, password }) and loginApi(email, password).
 */
export const loginApi = (credentialsOrEmail, password) => {
  const payload =
    typeof credentialsOrEmail === 'object' && credentialsOrEmail !== null
      ? credentialsOrEmail
      : { email: credentialsOrEmail, password }
  return api.post('/auth/login', payload)
}

/**
 * Rotate the current HttpOnly refresh token and obtain a new access token.
 */
export const refreshApi = () => {
  return api.post('/auth/refresh')
}

/**
 * Log out the current session, revoking the refresh token in PostgreSQL and clearing the cookie.
 */
export const logoutApi = () => {
  return api.post('/auth/logout')
}

/**
 * Fetch current authenticated user profile using Bearer access token.
 */
export const getMeApi = () => {
  return api.get('/auth/me')
}
