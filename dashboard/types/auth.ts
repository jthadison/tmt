/**
 * Authentication types and interfaces
 */

export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'trader' | 'viewer'
  two_factor_enabled: boolean
  created_at: string
  last_login: string
}

export interface LoginCredentials {
  email: string
  password: string
  two_factor_token?: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  expires_in: number
}

export interface TwoFactorSetup {
  secret: string
  qr_code: string
  backup_codes: string[]
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

export interface LoginResponse {
  success: boolean
  requires_2fa: boolean
  tokens?: AuthTokens
  user?: User
  error?: string
}