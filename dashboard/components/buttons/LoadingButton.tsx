/**
 * Loading Button Component
 * Story 9.1: Button with 3-stage state transitions (idle → loading → success → idle)
 */

'use client';

import { useState } from 'react';

interface LoadingButtonProps {
  onClick: () => Promise<void>;
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  successMessage?: string;
  successDuration?: number; // milliseconds
  className?: string;
  disabled?: boolean;
}

type ButtonState = 'idle' | 'loading' | 'success' | 'error';

export function LoadingButton({
  onClick,
  children,
  variant = 'primary',
  successMessage,
  successDuration = 1000,
  className = '',
  disabled = false,
}: LoadingButtonProps) {
  const [state, setState] = useState<ButtonState>('idle');

  const handleClick = async () => {
    if (state === 'loading' || disabled) return;

    setState('loading');

    try {
      await onClick();
      setState('success');

      // Reset to idle after success duration
      setTimeout(() => {
        setState('idle');
      }, successDuration);
    } catch (error) {
      setState('error');
      // Reset to idle after showing error
      setTimeout(() => {
        setState('idle');
      }, 2000);
    }
  };

  const variantClasses = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-white',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
  };

  const isDisabled = state === 'loading' || state === 'success' || disabled;

  return (
    <button
      onClick={handleClick}
      disabled={isDisabled}
      data-testid="loading-button"
      data-state={state}
      className={`
        px-4 py-2 rounded font-medium transition-all
        disabled:opacity-50 disabled:cursor-not-allowed
        flex items-center justify-center gap-2
        ${variantClasses[variant]}
        ${className}
      `}
    >
      {state === 'loading' && (
        <svg
          className="h-4 w-4 animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          data-testid="spinner-icon"
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
      )}

      {state === 'success' && (
        <svg
          className="h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          data-testid="check-icon"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      )}

      {state === 'error' && (
        <svg
          className="h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          data-testid="error-icon"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      )}

      <span>
        {state === 'idle' && children}
        {state === 'loading' && 'Processing...'}
        {state === 'success' && (successMessage || 'Success!')}
        {state === 'error' && 'Failed'}
      </span>
    </button>
  );
}
