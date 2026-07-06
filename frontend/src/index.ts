// Export everything from the shared auth library
export * from './types/auth'
export * from './utils/auth-client'
export * from './contexts/AuthContext'
export * from './components/ProductSwitcher'
export * from './components/SharedLoginPage'

// Re-export common components
export { AuthProvider, useAuth, AuthClient } from './contexts/AuthContext'
export { ProductSwitcher } from './components/ProductSwitcher'
export { SharedLoginPage } from './components/SharedLoginPage'