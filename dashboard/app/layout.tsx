import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { ThemeProvider } from '@/context/ThemeContext'
import { AuthProvider } from '@/context/AuthContext'
import { SettingsProvider } from '@/context/SettingsContext'
import { HealthDataProvider } from '@/context/HealthDataContext'
import { NotificationProvider } from '@/context/NotificationContext'
import ErrorBoundary from '@/components/ui/ErrorBoundary'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Adaptive Trading System',
  description: 'Professional trading dashboard for prop firm accounts',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>
          <AuthProvider>
            <SettingsProvider>
              <ThemeProvider>
                <HealthDataProvider>
                  <NotificationProvider>
                    {children}
                  </NotificationProvider>
                </HealthDataProvider>
              </ThemeProvider>
            </SettingsProvider>
          </AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  )
}
