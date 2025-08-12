'use client'

import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'

/**
 * Login form component with email/password and 2FA support
 * @returns Login form with validation and error handling
 */
export default function LoginForm() {
  const { login, isLoading, error } = useAuth()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    twoFactorToken: ''
  })
  const [requires2FA, setRequires2FA] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError(null)

    const credentials = {
      email: formData.email,
      password: formData.password,
      ...(requires2FA && { two_factor_token: formData.twoFactorToken })
    }

    const result = await login(credentials)

    if (result.requires_2fa) {
      setRequires2FA(true)
    } else if (!result.success) {
      setLoginError(result.error || 'Login failed')
      if (result.error?.includes('2FA')) {
        setRequires2FA(false)
      }
    }
  }

  return (
    <div className="max-w-md mx-auto bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Sign In
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Access your trading dashboard
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {!requires2FA ? (
          <>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
                placeholder="trader@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Password
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
                placeholder="••••••••"
              />
            </div>
          </>
        ) : (
          <div>
            <label htmlFor="twoFactorToken" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Two-Factor Authentication Code
            </label>
            <input
              type="text"
              id="twoFactorToken"
              name="twoFactorToken"
              value={formData.twoFactorToken}
              onChange={handleInputChange}
              required
              maxLength={6}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white text-center text-lg tracking-widest font-mono"
              placeholder="123456"
            />
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>
        )}

        {(loginError || error) && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
            <p className="text-sm text-red-600 dark:text-red-400">
              {loginError || error}
            </p>
          </div>
        )}

        <div className="space-y-2">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            {isLoading ? (
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : requires2FA ? (
              'Verify Code'
            ) : (
              'Sign In'
            )}
          </button>

          {requires2FA && (
            <button
              type="button"
              onClick={() => {
                setRequires2FA(false)
                setFormData(prev => ({ ...prev, twoFactorToken: '' }))
                setLoginError(null)
              }}
              className="w-full py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Back to Login
            </button>
          )}
        </div>
      </form>
    </div>
  )
}