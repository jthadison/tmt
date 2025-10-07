import { createContext, useContext, useState, ReactNode } from 'react'
import { ToastContainer } from './ToastContainer'

type ToastType = 'error' | 'warning' | 'info' | 'success'

export interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number
}

interface ToastContextType {
  showToast: (type: ToastType, message: string, duration?: number) => void
  dismissToast: (id: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = (type: ToastType, message: string, duration = 5000) => {
    const id = Math.random().toString(36).substr(2, 9)
    const newToast: Toast = { id, type, message, duration }

    setToasts(prev => [...prev.slice(-2), newToast]) // Max 3 toasts

    if (duration > 0) {
      setTimeout(() => dismissToast(id), duration)
    }
  }

  const dismissToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }

  return (
    <ToastContext.Provider value={{ showToast, dismissToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  )
}
