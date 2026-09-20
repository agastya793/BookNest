import { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react'
import { io } from 'socket.io-client'
import { useAuth } from './AuthContext'

const SocketContext = createContext(null)

export const SocketProvider = ({ children }) => {
  const { user, accessToken, isAuthenticated } = useAuth()
  const [isConnected, setIsConnected] = useState(false)
  const [socketId, setSocketId] = useState(null)
  const socketRef = useRef(null)

  useEffect(() => {
    // Only connect when user is actively authenticated with a valid access token (Safeguard 6)
    if (!isAuthenticated || !accessToken) {
      if (socketRef.current) {
        socketRef.current.disconnect()
        socketRef.current = null
      }
      setIsConnected(false)
      setSocketId(null)
      return
    }

    // Clean up existing socket before creating new one
    if (socketRef.current) {
      socketRef.current.disconnect()
    }

    // Connect via Vite proxy /socket.io endpoint passing short-lived access JWT in handshake
    const socket = io(window.location.origin, {
      path: '/socket.io',
      auth: {
        token: accessToken,
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    })

    socketRef.current = socket

    socket.on('connect', () => {
      setIsConnected(true)
      setSocketId(socket.id)
    })

    socket.on('disconnect', (reason) => {
      setIsConnected(false)
      setSocketId(null)
    })

    socket.on('connect_error', (err) => {
      console.warn('[Socket] Connection error:', err.message)
      setIsConnected(false)
    })

    return () => {
      socket.disconnect()
      socketRef.current = null
      setIsConnected(false)
      setSocketId(null)
    }
  }, [isAuthenticated, accessToken, user?.id])

  // Helper to join collaborative shelf room
  const joinShelf = useCallback((shelfId) => {
    if (socketRef.current && shelfId) {
      socketRef.current.emit('join_shelf', { shelf_id: shelfId })
    }
  }, [])

  // Helper to leave collaborative shelf room
  const leaveShelf = useCallback((shelfId) => {
    if (socketRef.current && shelfId) {
      socketRef.current.emit('leave_shelf', { shelf_id: shelfId })
    }
  }, [])

  const value = {
    socket: socketRef.current,
    isConnected,
    socketId,
    joinShelf,
    leaveShelf,
  }

  return <SocketContext.Provider value={value}>{children}</SocketContext.Provider>
}

export const useSocketContext = () => {
  const context = useContext(SocketContext)
  return context || { socket: null, isConnected: false, socketId: null, joinShelf: () => {}, leaveShelf: () => {} }
}

export default SocketContext
