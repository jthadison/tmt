'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import ThemeToggle from '@/components/ui/ThemeToggle'
import { useAuth } from '@/context/AuthContext'
import EmergencyStopButton from '@/components/emergency/EmergencyStopButton'

/**
 * Header component for the trading dashboard
 * @returns Header component with navigation and user controls
 */
export default function Header() {
  const { user, logout } = useAuth()
  const pathname = usePathname()

  const handleLogout = () => {
    logout()
  }

  const isActive = (path: string) => {
    if (path === '/') {
      return pathname === '/'
    }
    return pathname.startsWith(path)
  }

  const getLinkClasses = (path: string) => {
    const baseClasses = "hover:text-gray-300 transition-colors px-2 py-1 rounded"
    const activeClasses = "text-white bg-blue-600"
    const inactiveClasses = "text-gray-300"
    
    return `${baseClasses} ${isActive(path) ? activeClasses : inactiveClasses}`
  }

  return (
    <header className="bg-gray-900 dark:bg-gray-900 text-white border-b border-gray-800 dark:border-gray-700">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="text-xl font-bold hover:text-gray-300 transition-colors">
              Adaptive Trading System
            </Link>
            <nav className="hidden md:flex space-x-4">
              <Link href="/" className={getLinkClasses('/')}>
                Dashboard
              </Link>
              <Link href="/oanda" className={getLinkClasses('/oanda')}>
                OANDA
              </Link>
              <Link href="/brokers" className={getLinkClasses('/brokers')}>
                Brokers
              </Link>
              <Link href="/performance-analytics" className={getLinkClasses('/performance-analytics')}>
                Analytics
              </Link>
            </nav>
          </div>
          <div className="flex items-center space-x-4">
            <EmergencyStopButton />
            <ThemeToggle />
            <button className="p-2 hover:bg-gray-800 dark:hover:bg-gray-700 rounded transition-colors">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </button>
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-300">
                {user?.name || user?.email}
              </span>
              <button
                onClick={handleLogout}
                className="p-2 hover:bg-gray-800 dark:hover:bg-gray-700 rounded transition-colors"
                title="Logout"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}