'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import Cookies from 'js-cookie'
import { AuthState, User, LoginCredentials, LoginResponse } from '@/types/auth'

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<LoginResponse>
  logout: () => void
  refreshToken: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

/**
 * Authentication provider component
 * @param children - Child components
 * @returns Auth context provider
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null
  })

  /**
   * Login user with credentials
   * @param credentials - Login credentials including optional 2FA token
   * @returns Login response with success status and user data
   */
  const login = async (credentials: LoginCredentials): Promise<LoginResponse> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))

    try {
      // In development, simulate successful login
      if (process.env.NODE_ENV === 'development') {
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // Check for demo credentials
        if (credentials.username === 'demo' && credentials.password === 'demo123') {
          const mockUser: User = {
            id: 'user-001',
            username: 'demo',
            email: 'demo@tradingsystem.com',
            role: 'admin',
            created_at: new Date().toISOString(),
            last_login: new Date().toISOString(),
            two_factor_enabled: false
          }
          
          const mockResponse: LoginResponse = {
            success: true,
            requires_2fa: false,
            user: mockUser,
            tokens: {
              access_token: 'mock-access-token',
              refresh_token: 'mock-refresh-token',
              expires_in: 3600
            }
          }
          
          // Store tokens
          Cookies.set('access_token', mockResponse.tokens!.access_token, {
            expires: 1, // 1 day for dev
            secure: false,
            sameSite: 'strict'
          })
          
          Cookies.set('refresh_token', mockResponse.tokens!.refresh_token, {
            expires: 30,
            secure: false,
            sameSite: 'strict'
          })

          setState({
            user: mockUser,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
          
          return mockResponse
        } else {
          throw new Error('Invalid credentials. Use demo/demo123 for development.')
        }
      }
      
      // Production API call
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      })

      const data: LoginResponse = await response.json()

      if (data.success && data.tokens && data.user) {
        // Store tokens in httpOnly cookies (simulated for now)
        Cookies.set('access_token', data.tokens.access_token, {
          expires: data.tokens.expires_in / (24 * 60 * 60), // Convert seconds to days
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'strict'
        })
        
        Cookies.set('refresh_token', data.tokens.refresh_token, {
          expires: 30, // 30 days
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'strict'
        })

        setState({
          user: data.user,
          isAuthenticated: true,
          isLoading: false,
          error: null
        })
      } else if (data.requires_2fa) {
        setState(prev => ({ ...prev, isLoading: false, error: null }))
      } else {
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: data.error || 'Login failed'
        }))
      }

      return data
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Network error'
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage
      }))
      
      return {
        success: false,
        requires_2fa: false,
        error: errorMessage
      }
    }
  }

  /**
   * Logout user and clear tokens
   */
  const logout = () => {
    Cookies.remove('access_token')
    Cookies.remove('refresh_token')
    
    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null
    })
  }

  /**
   * Refresh authentication token
   * @returns Success status
   */
  const refreshToken = async (): Promise<boolean> => {
    const refreshTokenValue = Cookies.get('refresh_token')
    
    if (!refreshTokenValue) {
      logout()
      return false
    }

    try {
      // TODO: Replace with actual API call
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshTokenValue }),
      })

      const data = await response.json()

      if (data.success && data.tokens) {
        Cookies.set('access_token', data.tokens.access_token, {
          expires: data.tokens.expires_in / (24 * 60 * 60),
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'strict'
        })
        
        return true
      } else {
        logout()
        return false
      }
    } catch (error) {
      logout()
      return false
    }
  }

  /**
   * Initialize authentication state from stored tokens
   */
  useEffect(() => {
    const initializeAuth = async () => {
      const accessToken = Cookies.get('access_token')
      
      if (accessToken) {
        try {
          // In development, use mock user if token exists
          if (process.env.NODE_ENV === 'development' && accessToken === 'mock-access-token') {
            const mockUser: User = {
              id: 'user-001',
              username: 'demo',
              email: 'demo@tradingsystem.com',
              role: 'admin',
              created_at: new Date().toISOString(),
              last_login: new Date().toISOString(),
              two_factor_enabled: false
            }
            
            setState({
              user: mockUser,
              isAuthenticated: true,
              isLoading: false,
              error: null
            })
            return
          }
          
          // Production API call
          const response = await fetch('/api/auth/me', {
            headers: {
              'Authorization': `Bearer ${accessToken}`,
            },
          })

          if (response.ok) {
            const user: User = await response.json()
            setState({
              user,
              isAuthenticated: true,
              isLoading: false,
              error: null
            })
          } else {
            // Try to refresh token
            const refreshSuccess = await refreshToken()
            if (!refreshSuccess) {
              setState(prev => ({ ...prev, isLoading: false }))
            }
          }
        } catch (error) {
          console.error('Auth initialization error:', error)
          setState(prev => ({ ...prev, isLoading: false }))
        }
      } else {
        setState(prev => ({ ...prev, isLoading: false }))
      }
    }

    initializeAuth()
  }, [])

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        refreshToken
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

/**
 * Hook to use authentication context
 * @returns Authentication context value
 * @throws Error if used outside AuthProvider
 */
export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}