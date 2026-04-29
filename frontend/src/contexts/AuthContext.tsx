'use client'

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { AuthClient } from '../utils/auth-client'
import { User, AuthContextType, AuthConfig } from '../types/auth'

interface AuthProviderProps {
  children: ReactNode
  config: AuthConfig
  /** Called when the session ends because of a hard auth failure (e.g. refresh failed). */
  onSessionExpired?: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children, config, onSessionExpired }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [authClient] = useState(() => new AuthClient(config))

  useEffect(() => {
    let cancelled = false
    if (authClient.isAuthenticated()) {
      authClient
        .getCurrentUser()
        .then((u) => {
          if (!cancelled) setUser(u)
        })
        .catch(() => {
          authClient.logout()
          if (!cancelled) {
            setUser(null)
            onSessionExpired?.()
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    } else {
      setLoading(false)
    }
    return () => {
      cancelled = true
    }
  }, [authClient, onSessionExpired])

  const login = async (email: string, password: string) => {
    const response = await authClient.login({ email, password })
    setUser(response.user)
  }

  const signup = async (email: string, password: string, name?: string) => {
    const response = await authClient.signup({ email, password, name })
    setUser(response.user)
  }

  const logout = useCallback(() => {
    authClient.logout()
    setUser(null)
  }, [authClient])

  const apiFetch = useCallback(
    async (input: string, init?: RequestInit) => {
      const res = await authClient.fetch(input, init)
      // After fetch, if the client was logged out (refresh failed), reflect it in state.
      if (!authClient.isAuthenticated() && user !== null) {
        setUser(null)
        onSessionExpired?.()
      }
      return res
    },
    [authClient, user, onSessionExpired]
  )

  const getAccessToken = useCallback(() => authClient.getAccessToken(), [authClient])

  const value: AuthContextType = {
    user,
    loading,
    login,
    signup,
    logout,
    isAuthenticated: authClient.isAuthenticated() && user !== null,
    apiFetch,
    getAccessToken,
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
