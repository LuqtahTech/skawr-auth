export interface User {
  id: string
  email: string
  name?: string
  company?: string
  email_verified: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface SignupRequest {
  email: string
  password: string
  name?: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, name?: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

export interface AuthConfig {
  apiBaseUrl: string
  tokenStorageKey?: string
}