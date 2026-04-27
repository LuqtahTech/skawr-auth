import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { AuthClient } from '../utils/auth-client'
import { User, AuthContextType, AuthConfig } from '../types/auth'

interface AuthProviderProps {
  children: ReactNode
  config: AuthConfig
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children, config }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [authClient] = useState(() => new AuthClient(config))

  useEffect(() => {
    // Check if user is already authenticated
    if (authClient.isAuthenticated()) {
      authClient
        .getCurrentUser()
        .then(setUser)
        .catch(() => {
          // Token is invalid, logout
          authClient.logout()
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [authClient])

  const login = async (email: string, password: string) => {
    try {
      const response = await authClient.login({ email, password })
      setUser(response.user)
    } catch (error) {
      throw error
    }
  }

  const signup = async (email: string, password: string, name?: string) => {
    try {
      const response = await authClient.signup({ email, password, name })
      setUser(response.user)
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    authClient.logout()
    setUser(null)
  }

  const value: AuthContextType = {
    user,
    loading,
    login,
    signup,
    logout,
    isAuthenticated: authClient.isAuthenticated() && user !== null,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export { AuthClient }