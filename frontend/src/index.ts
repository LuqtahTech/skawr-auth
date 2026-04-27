// Export everything from the shared auth library
export * from './types/auth'
export * from './utils/auth-client'
export * from './contexts/AuthContext'

// Re-export common components
export { AuthProvider, useAuth, AuthClient } from './contexts/AuthContext'