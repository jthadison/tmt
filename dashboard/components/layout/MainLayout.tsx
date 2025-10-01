import { ReactNode, useState, useEffect } from 'react'
import Header from './Header'
import Sidebar from './Sidebar'
import Footer from './Footer'
import StatusBar from '@/components/health/StatusBar'
import DetailedHealthPanel from '@/components/health/DetailedHealthPanel'

interface MainLayoutProps {
  children: ReactNode
}

/**
 * Main layout wrapper component
 * @param children - Page content to render
 * @returns Layout with header, sidebar, footer, and main content area
 */
export default function MainLayout({ children }: MainLayoutProps) {
  const [isDetailedHealthOpen, setIsDetailedHealthOpen] = useState(false)
  const [showMiniCards, setShowMiniCards] = useState(true)

  // Load user preference for mini cards
  useEffect(() => {
    const saved = localStorage.getItem('showMiniAgentCards')
    if (saved !== null) {
      setShowMiniCards(JSON.parse(saved))
    }
  }, [])

  // Save user preference when it changes
  useEffect(() => {
    localStorage.setItem('showMiniAgentCards', JSON.stringify(showMiniCards))
  }, [showMiniCards])

  const handleStatusBarClick = () => {
    setIsDetailedHealthOpen(!isDetailedHealthOpen)
  }

  const handleCloseHealthPanel = () => {
    setIsDetailedHealthOpen(false)
  }

  const handleAgentClick = (agentPort: number) => {
    setIsDetailedHealthOpen(true)
    // Optional: Scroll to agent section after panel opens
    setTimeout(() => {
      const element = document.querySelector(`[data-agent-port="${agentPort}"]`)
      element?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 300)
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      <Header />
      <StatusBar onExpandClick={handleStatusBarClick} />
      <DetailedHealthPanel
        isOpen={isDetailedHealthOpen}
        onClose={handleCloseHealthPanel}
      />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-950">
          <div className="container mx-auto px-4 py-8 pb-24">
            {children}
          </div>
        </main>
      </div>
      <Footer onAgentClick={handleAgentClick} showMiniCards={showMiniCards} />
    </div>
  )
}