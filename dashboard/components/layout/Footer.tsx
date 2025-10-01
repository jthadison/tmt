/**
 * Footer Component
 * Global footer with connection quality indicator and mini agent health cards
 */

'use client'

import React, { useState } from 'react'
import ConnectionQualityIndicator from '@/components/health/ConnectionQualityIndicator'
import MiniAgentHealthCards from '@/components/health/MiniAgentHealthCards'

interface FooterProps {
  onAgentClick?: (agentPort: number) => void
  showMiniCards?: boolean
}

/**
 * Footer component
 */
export default function Footer({ onAgentClick, showMiniCards = true }: FooterProps) {
  return (
    <footer className="bg-gray-900 border-t border-gray-800">
      <div className="max-w-7xl mx-auto px-4 py-3 space-y-3">
        {/* Mini Agent Health Cards (optional) */}
        {showMiniCards && (
          <MiniAgentHealthCards onAgentClick={onAgentClick} />
        )}

        {/* Footer Bottom Row */}
        <div className="flex items-center justify-between">
          {/* Left side - Copyright/info */}
          <div className="text-xs text-gray-500">
            © 2025 TMT Trading System
          </div>

          {/* Right side - Connection Quality */}
          <ConnectionQualityIndicator />
        </div>
      </div>
    </footer>
  )
}
