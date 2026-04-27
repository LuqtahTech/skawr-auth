import axios, { AxiosResponse } from 'axios'
import { User, AuthResponse, SignupRequest, LoginRequest, AuthConfig } from '../types/auth'

export class AuthClient {
  private apiBaseUrl: string
  private tokenStorageKey: string
  private token: string | null = null

  constructor(config: AuthConfig) {
    this.apiBaseUrl = config.apiBaseUrl
    this.tokenStorageKey = config.tokenStorageKey || 'auth_token'

    // Initialize token from localStorage on client
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem(this.tokenStorageKey)
    }
  }

  async signup(data: SignupRequest): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await axios.post(
      `${this.apiBaseUrl}/auth/signup`,
      data
    )

    this.setToken(response.data.access_token)
    return response.data
  }

  async login(data: LoginRequest): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await axios.post(
      `${this.apiBaseUrl}/auth/login`,
      data
    )

    this.setToken(response.data.access_token)
    return response.data
  }

  async getCurrentUser(): Promise<User> {
    if (!this.token) {
      throw new Error('No authentication token')
    }

    const response: AxiosResponse<User> = await axios.get(
      `${this.apiBaseUrl}/auth/me`,
      {
        headers: {
          Authorization: `Bearer ${this.token}`,
        },
      }
    )

    return response.data
  }

  logout(): void {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem(this.tokenStorageKey)
    }
  }

  private setToken(token: string): void {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem(this.tokenStorageKey, token)
    }
  }

  getToken(): string | null {
    return this.token
  }

  isAuthenticated(): boolean {
    return this.token !== null
  }

  // Create axios instance with auth header for API calls
  createAuthenticatedClient() {
    return axios.create({
      baseURL: this.apiBaseUrl,
      headers: {
        Authorization: this.token ? `Bearer ${this.token}` : undefined,
      },
    })
  }
}