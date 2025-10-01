import { ReactNode, useState } from 'react'
import Header from './Header'
import Sidebar from './Sidebar'
import StatusBar from '@/components/health/StatusBar'

interface MainLayoutProps {
  children: ReactNode
}

/**
 * Main layout wrapper component
 * @param children - Page content to render
 * @returns Layout with header, sidebar, and main content area
 */
export default function MainLayout({ children }: MainLayoutProps) {
  const [isDetailedHealthOpen, setIsDetailedHealthOpen] = useState(false)

  const handleStatusBarClick = () => {
    // TODO: Open DetailedHealthPanel when Story 1.2 is implemented
    setIsDetailedHealthOpen(!isDetailedHealthOpen)
    console.log('Status bar clicked - DetailedHealthPanel will be implemented in Story 1.2')
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      <Header />
      <StatusBar onExpandClick={handleStatusBarClick} />
      <div className="flex h-[calc(100vh-8rem)]">
        <Sidebar />
        <main className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-950">
          <div className="container mx-auto px-4 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}