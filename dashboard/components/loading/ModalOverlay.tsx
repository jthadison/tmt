/**
 * Modal Overlay Component
 * Story 9.1: Full-screen loading overlay for critical operations
 */

'use client';

import { useEffect } from 'react';

interface ModalOverlayProps {
  message: string;
  isOpen: boolean;
  preventClose?: boolean;
}

export function ModalOverlay({
  message,
  isOpen,
  preventClose = true,
}: ModalOverlayProps) {
  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  // Trap focus within modal
  useEffect(() => {
    if (isOpen && preventClose) {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          e.preventDefault();
        }
      };

      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, preventClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-message"
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-xl max-w-md">
        <div className="flex flex-col items-center gap-4">
          <svg
            className="animate-spin h-12 w-12 text-blue-600"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            data-testid="modal-spinner"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <p
            id="modal-message"
            className="text-lg font-medium text-gray-900 dark:text-white text-center"
          >
            {message}
          </p>
        </div>
      </div>
    </div>
  );
}
