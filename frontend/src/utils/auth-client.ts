import axios, { AxiosResponse } from 'axios'
import {
  User,
  AuthResponse,
  SignupRequest,
  LoginRequest,
  AuthConfig,
  TokenPair,
  ProductEnrollment,
} from '../types/auth'

const DEFAULT_TOKEN_KEY = 'auth_token'
const DEFAULT_REFRESH_KEY = 'auth_refresh_token'

export class AuthClient {
  private apiBaseUrl: string
  private tokenStorageKey: string
  private refreshTokenStorageKey: string
  private accessToken: string | null = null
  private refreshToken: string | null = null
  private refreshInFlight: Promise<string | null> | null = null

  constructor(config: AuthConfig) {
    this.apiBaseUrl = config.apiBaseUrl
    this.tokenStorageKey = config.tokenStorageKey || DEFAULT_TOKEN_KEY
    this.refreshTokenStorageKey = config.refreshTokenStorageKey || DEFAULT_REFRESH_KEY

    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem(this.tokenStorageKey)
      this.refreshToken = localStorage.getItem(this.refreshTokenStorageKey)
    }
  }

  async signup(data: SignupRequest): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await axios.post(
      `${this.apiBaseUrl}/auth/signup`,
      data
    )
    this.persistTokens(response.data.access_token, response.data.refresh_token)
    return response.data
  }

  async login(data: LoginRequest & { product?: string }): Promise<AuthResponse> {
    const { product, ...loginData } = data
    let url = `${this.apiBaseUrl}/auth/login`
    if (product) {
      url += `?product=${encodeURIComponent(product)}`
    }
    const response: AxiosResponse<AuthResponse> = await axios.post(url, loginData)
    this.persistTokens(response.data.access_token, response.data.refresh_token)
    return response.data
  }

  getEnrolledProducts(): ProductEnrollment[] {
    const payload = this._decodeTokenPayload()
    if (!payload || !payload.product_enrollments) {
      return []
    }
    return payload.product_enrollments as ProductEnrollment[]
  }

  hasProductAccess(product: string): boolean {
    const payload = this._decodeTokenPayload()
    if (!payload) {
      return false
    }
    // Backward compat: if token has no product_enrollments claim, return true (legacy token = access everywhere)
    if (!payload.product_enrollments) {
      return true
    }
    const enrollments = payload.product_enrollments as ProductEnrollment[]
    return enrollments.some((e) => e.product === product)
  }

  private _decodeTokenPayload(): Record<string, any> | null {
    if (!this.accessToken) {
      return null
    }
    try {
      const parts = this.accessToken.split('.')
      if (parts.length !== 3) {
        return null
      }
      // Base64url decode the payload (middle part)
      let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
      // Pad with '=' to make it a valid base64 string
      while (base64.length % 4 !== 0) {
        base64 += '='
      }
      const jsonStr = atob(base64)
      return JSON.parse(jsonStr)
    } catch {
      return null
    }
  }

  async getCurrentUser(): Promise<User> {
    const res = await this.fetch(`${this.apiBaseUrl}/auth/me`)
    if (!res.ok) {
      throw new Error(`Failed to load user (${res.status})`)
    }
    return (await res.json()) as User
  }

  logout(): void {
    this.accessToken = null
    this.refreshToken = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem(this.tokenStorageKey)
      localStorage.removeItem(this.refreshTokenStorageKey)
    }
  }

  getAccessToken(): string | null {
    return this.accessToken
  }

  isAuthenticated(): boolean {
    return this.accessToken !== null
  }

  /**
   * Authenticated fetch wrapper:
   * - Attaches the access token
   * - On 401, tries to refresh once and retries
   * - On hard failure, calls logout() so the UI can react
   */
  async fetch(input: string, init: RequestInit = {}): Promise<Response> {
    const doFetch = (token: string | null) => {
      const headers = new Headers(init.headers || {})
      if (token) headers.set('Authorization', `Bearer ${token}`)
      if (init.body && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
      }
      return fetch(input, { ...init, headers })
    }

    let response = await doFetch(this.accessToken)
    if (response.status !== 401 || !this.refreshToken) {
      return response
    }

    const newAccess = await this.refreshAccessToken()
    if (!newAccess) {
      this.logout()
      return response
    }

    response = await doFetch(newAccess)
    if (response.status === 401) {
      this.logout()
    }
    return response
  }

  /** Single-flight refresh: many concurrent 401s share one /auth/refresh call. */
  async refreshAccessToken(): Promise<string | null> {
    if (!this.refreshToken) return null
    if (this.refreshInFlight) return this.refreshInFlight

    this.refreshInFlight = (async () => {
      try {
        const response: AxiosResponse<TokenPair> = await axios.post(
          `${this.apiBaseUrl}/auth/refresh`,
          { refresh_token: this.refreshToken }
        )
        this.persistTokens(response.data.access_token, response.data.refresh_token)
        return response.data.access_token
      } catch {
        return null
      } finally {
        this.refreshInFlight = null
      }
    })()

    return this.refreshInFlight
  }

  private persistTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken
    this.refreshToken = refreshToken
    if (typeof window !== 'undefined') {
      localStorage.setItem(this.tokenStorageKey, accessToken)
      localStorage.setItem(this.refreshTokenStorageKey, refreshToken)
    }
  }
}
