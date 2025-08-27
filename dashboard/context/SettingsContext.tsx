'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface SettingsData {
  // System Preferences
  theme: 'light' | 'dark' | 'system'
  refreshInterval: number
  notifications: boolean
  soundAlerts: boolean
  
  // Trading Configuration
  defaultRiskPerTrade: number
  maxDailyLoss: number
  emergencyStopLoss: number
  
  // Display Preferences
  currency: 'USD' | 'EUR' | 'GBP'
  decimalPlaces: number
  timezone: string
  
  // Dashboard Preferences
  showOandaIntegration: boolean
  showHealthChecks: boolean
  autoRefresh: boolean
  compactMode: boolean
  
  // Alert Preferences
  emailNotifications: boolean
  pushNotifications: boolean
  riskLevelAlerts: boolean
  profitTargetAlerts: boolean
  
  // API Configuration
  oandaApiKey: string
  oandaAccountId: string
  oandaEnvironment: 'practice' | 'live'
}

const defaultSettings: SettingsData = {
  theme: 'dark',
  refreshInterval: 30,
  notifications: true,
  soundAlerts: false,
  defaultRiskPerTrade: 1.0,
  maxDailyLoss: 500,
  emergencyStopLoss: 1000,
  currency: 'USD',
  decimalPlaces: 2,
  timezone: 'America/New_York',
  showOandaIntegration: true,
  showHealthChecks: true,
  autoRefresh: true,
  compactMode: false,
  emailNotifications: true,
  pushNotifications: false,
  riskLevelAlerts: true,
  profitTargetAlerts: true,
  oandaApiKey: '',
  oandaAccountId: '',
  oandaEnvironment: 'practice'
}

interface SettingsContextType {
  settings: SettingsData
  updateSetting: <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => void
  updateMultipleSettings: (updates: Partial<SettingsData>) => void
  resetSettings: () => void
  saveSettings: () => Promise<void>
  hasUnsavedChanges: boolean
  lastSaved: Date | null
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

interface SettingsProviderProps {
  children: ReactNode
}

export function SettingsProvider({ children }: SettingsProviderProps) {
  const [settings, setSettings] = useState<SettingsData>(defaultSettings)
  const [initialSettings, setInitialSettings] = useState<SettingsData>(defaultSettings)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = localStorage.getItem('tradingSystemSettings')
    const savedDate = localStorage.getItem('tradingSystemSettingsLastSaved')
    
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings)
        const mergedSettings = { ...defaultSettings, ...parsed }
        setSettings(mergedSettings)
        setInitialSettings(mergedSettings)
        setHasUnsavedChanges(false)
        
        if (savedDate) {
          setLastSaved(new Date(savedDate))
        }
      } catch (error) {
        console.error('Error loading settings:', error)
      }
    }
  }, [])

  // Check for unsaved changes
  useEffect(() => {
    const hasChanges = JSON.stringify(settings) !== JSON.stringify(initialSettings)
    setHasUnsavedChanges(hasChanges)
  }, [settings, initialSettings])

  const updateSetting = <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const updateMultipleSettings = (updates: Partial<SettingsData>) => {
    setSettings(prev => ({ ...prev, ...updates }))
  }

  const resetSettings = () => {
    setSettings(defaultSettings)
  }

  const saveSettings = async () => {
    try {
      localStorage.setItem('tradingSystemSettings', JSON.stringify(settings))
      const now = new Date()
      localStorage.setItem('tradingSystemSettingsLastSaved', now.toISOString())
      
      setInitialSettings(settings)
      setHasUnsavedChanges(false)
      setLastSaved(now)
      
      // Dispatch custom event for other components to react to setting changes
      window.dispatchEvent(new CustomEvent('settingsChanged', { 
        detail: { settings, timestamp: now }
      }))
      
    } catch (error) {
      console.error('Error saving settings:', error)
      throw error
    }
  }

  const value: SettingsContextType = {
    settings,
    updateSetting,
    updateMultipleSettings,
    resetSettings,
    saveSettings,
    hasUnsavedChanges,
    lastSaved
  }

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}

// Hook for reading settings only (for components that don't need to update)
export function useSettingsReadOnly() {
  const { settings } = useSettings()
  return settings
}

// Hook for specific setting
export function useSetting<K extends keyof SettingsData>(key: K) {
  const { settings, updateSetting } = useSettings()
  return [settings[key], (value: SettingsData[K]) => updateSetting(key, value)] as const
}

// Helper functions for common operations
export const formatCurrency = (amount: number, settings: SettingsData): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: settings.currency,
    minimumFractionDigits: settings.decimalPlaces,
    maximumFractionDigits: settings.decimalPlaces
  }).format(amount)
}

export const formatTimezone = (date: Date, timezone: string): string => {
  return date.toLocaleString('en-US', {
    timeZone: timezone,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}