'use client'

import { ReactNode } from 'react'
import { useAuth } from '@/context/AuthContext'
import LoginForm from './LoginForm'

interface ProtectedRouteProps {
  children: ReactNode
  requiredRole?: 'admin' | 'trader' | 'viewer'
}

/**
 * Protected route wrapper that requires authentication
 * @param children - Components to render when authenticated
 * @param requiredRole - Optional role requirement
 * @returns Children if authenticated, login form otherwise
 */
export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth()

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    )
  }

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
        <LoginForm />
      </div>
    )
  }

  // Check role requirement
  if (requiredRole && user && !hasRequiredRole(user.role, requiredRole)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="text-center max-w-md mx-auto bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
          <div className="text-red-500 text-6xl mb-4">🚫</div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Access Denied
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            You don&apos;t have permission to access this resource. Required role: {requiredRole}
          </p>
        </div>
      </div>
    )
  }

  // Render protected content
  return <>{children}</>
}

/**
 * Check if user has required role
 * @param userRole - User's current role
 * @param requiredRole - Required role
 * @returns Whether user has sufficient permissions
 */
function hasRequiredRole(
  userRole: 'admin' | 'trader' | 'viewer',
  requiredRole: 'admin' | 'trader' | 'viewer'
): boolean {
  const roleHierarchy = {
    admin: 3,
    trader: 2,
    viewer: 1
  }

  return roleHierarchy[userRole] >= roleHierarchy[requiredRole]
}