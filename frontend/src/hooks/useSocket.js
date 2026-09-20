import { useEffect, useRef } from 'react'
import { useSocketContext } from '../context/SocketContext'

/**
 * Custom hook to subscribe to a specific Socket.IO event with automatic cleanup.
 * 
 * @param {string} eventName - The name of the event to listen for
 * @param {Function} callback - Handler called when event is received
 * @param {Array} deps - Optional additional dependencies
 */
export const useSocket = (eventName, callback, deps = []) => {
  const { socket, isConnected } = useSocketContext()
  const savedCallback = useRef(callback)

  useEffect(() => {
    savedCallback.current = callback
  }, [callback])

  useEffect(() => {
    if (!socket || !eventName) return

    const handler = (...args) => {
      if (savedCallback.current) {
        savedCallback.current(...args)
      }
    }

    socket.on(eventName, handler)

    return () => {
      socket.off(eventName, handler)
    }
  }, [socket, isConnected, eventName, ...deps])
}

/**
 * Custom hook to automatically join and leave a collaborative shelf room.
 * 
 * @param {string|null} shelfId - UUID of the active shelf to subscribe to
 */
export const useShelfSubscription = (shelfId) => {
  const { joinShelf, leaveShelf, isConnected } = useSocketContext()

  useEffect(() => {
    if (!shelfId || !isConnected) return

    joinShelf(shelfId)

    return () => {
      leaveShelf(shelfId)
    }
  }, [shelfId, isConnected, joinShelf, leaveShelf])
}

export default useSocket
