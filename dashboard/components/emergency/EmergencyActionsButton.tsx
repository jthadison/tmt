'use client';

/**
 * Emergency Actions Button Component
 * Button in header to open the Emergency Actions Panel
 */

import React, { useState } from 'react';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';
import EmergencyActionsPanel from './EmergencyActionsPanel';

// Heroicon
const BoltIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

export default function EmergencyActionsButton() {
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  // Keyboard shortcut: Alt+E
  useKeyboardShortcut(['Alt', 'E'], () => {
    setIsPanelOpen((prev) => !prev);
  });

  return (
    <>
      <div className="relative group">
        <button
          onClick={() => setIsPanelOpen(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-lg shadow-lg border-2 border-amber-500 transition-all hover:scale-105"
          aria-label="Open emergency actions panel"
          title="Emergency Actions Panel (Alt+E)"
          data-emergency-actions-button
        >
          <BoltIcon className="w-5 h-5" />
          <span className="hidden sm:inline">Emergency Actions</span>
        </button>

        {/* Tooltip */}
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 border border-gray-700">
          Emergency Actions Panel (Alt+E)
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
            <div className="border-4 border-transparent border-t-gray-900"></div>
          </div>
        </div>
      </div>

      {/* Emergency Actions Panel */}
      <EmergencyActionsPanel isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} />
    </>
  );
}
