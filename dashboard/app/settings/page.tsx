'use client'

import { useState } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/ui/Card'
import Grid from '@/components/ui/Grid'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { useTheme } from '@/context/ThemeContext'
import { useSettings } from '@/context/SettingsContext'
import ThemeToggle from '@/components/ui/ThemeToggle'

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { 
    settings, 
    updateSetting, 
    resetSettings, 
    saveSettings: saveSettingsToStorage, 
    hasUnsavedChanges,
    lastSaved 
  } = useSettings()
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [activeTab, setActiveTab] = useState<'general' | 'trading' | 'display' | 'alerts' | 'api'>('general')

  // Handle setting change
  const handleSettingChange = (key: keyof typeof settings, value: unknown) => {
    updateSetting(key, value)
  }

  // Save settings
  const saveSettings = async () => {
    setSaveStatus('saving')
    try {
      await saveSettingsToStorage()
      
      // Apply theme change immediately
      if (settings.theme !== theme) {
        setTheme(settings.theme)
      }
      
      setSaveStatus('saved')
      
      // Reset status after 2 seconds
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (error) {
      console.error('Error saving settings:', error)
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 2000)
    }
  }

  // Reset settings wrapper
  const handleResetSettings = () => {
    resetSettings()
  }

  const tabs = [
    { id: 'general' as const, name: 'General', icon: '🔧' },
    { id: 'trading' as const, name: 'Trading', icon: '💹' },
    { id: 'display' as const, name: 'Display', icon: '🖥️' },
    { id: 'alerts' as const, name: 'Alerts', icon: '🔔' },
    { id: 'api' as const, name: 'API', icon: '🔑' }
  ]

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">Settings</h1>
              <p className="text-gray-400 mt-1">Configure your trading system preferences</p>
            </div>
            
            <div className="flex items-center space-x-3">
              {lastSaved && (
                <span className="text-sm text-gray-400">
                  Last saved: {lastSaved.toLocaleTimeString()}
                </span>
              )}
              {hasUnsavedChanges && (
                <button
                  onClick={handleResetSettings}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  Reset
                </button>
              )}
              <button
                onClick={saveSettings}
                disabled={!hasUnsavedChanges || saveStatus === 'saving'}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
              >
                {saveStatus === 'saving' ? 'Saving...' : 
                 saveStatus === 'saved' ? 'Saved ✓' : 
                 saveStatus === 'error' ? 'Error ✗' : 'Save Changes'}
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="border-b border-gray-800">
            <nav className="flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.name}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="space-y-6">
            {activeTab === 'general' && (
              <Grid cols={{ default: 1, lg: 2 }}>
                <Card title="System Preferences">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Theme
                      </label>
                      <div className="flex items-center space-x-4">
                        <ThemeToggle />
                        <span className="text-sm text-gray-400">
                          Current: {theme === 'system' ? 'Auto' : theme === 'dark' ? 'Dark' : 'Light'}
                        </span>
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Refresh Interval (seconds)
                      </label>
                      <select
                        value={settings.refreshInterval}
                        onChange={(e) => handleSettingChange('refreshInterval', parseInt(e.target.value))}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      >
                        <option value={5}>5 seconds</option>
                        <option value={10}>10 seconds</option>
                        <option value={30}>30 seconds</option>
                        <option value={60}>1 minute</option>
                        <option value={300}>5 minutes</option>
                      </select>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Enable Notifications
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.notifications}
                        onChange={(e) => handleSettingChange('notifications', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Sound Alerts
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.soundAlerts}
                        onChange={(e) => handleSettingChange('soundAlerts', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </Card>

                <Card title="Dashboard Preferences">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Show OANDA Integration
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.showOandaIntegration}
                        onChange={(e) => handleSettingChange('showOandaIntegration', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Show Health Checks
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.showHealthChecks}
                        onChange={(e) => handleSettingChange('showHealthChecks', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Auto Refresh
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.autoRefresh}
                        onChange={(e) => handleSettingChange('autoRefresh', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Compact Mode
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.compactMode}
                        onChange={(e) => handleSettingChange('compactMode', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </Card>
              </Grid>
            )}

            {activeTab === 'trading' && (
              <Grid cols={{ default: 1, lg: 2 }}>
                <Card title="Risk Management">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Default Risk Per Trade (%)
                      </label>
                      <input
                        type="number"
                        min="0.1"
                        max="10"
                        step="0.1"
                        value={settings.defaultRiskPerTrade}
                        onChange={(e) => handleSettingChange('defaultRiskPerTrade', parseFloat(e.target.value))}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Max Daily Loss ($)
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="10"
                        value={settings.maxDailyLoss}
                        onChange={(e) => handleSettingChange('maxDailyLoss', parseInt(e.target.value))}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Emergency Stop Loss ($)
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="10"
                        value={settings.emergencyStopLoss}
                        onChange={(e) => handleSettingChange('emergencyStopLoss', parseInt(e.target.value))}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      />
                    </div>
                  </div>
                </Card>

                <Card title="Trading Preferences">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Base Currency
                      </label>
                      <select
                        value={settings.currency}
                        onChange={(e) => handleSettingChange('currency', e.target.value)}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      >
                        <option value="USD">USD - US Dollar</option>
                        <option value="EUR">EUR - Euro</option>
                        <option value="GBP">GBP - British Pound</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Decimal Places
                      </label>
                      <select
                        value={settings.decimalPlaces}
                        onChange={(e) => handleSettingChange('decimalPlaces', parseInt(e.target.value))}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      >
                        <option value={0}>0</option>
                        <option value={2}>2</option>
                        <option value={4}>4</option>
                        <option value={5}>5</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Timezone
                      </label>
                      <select
                        value={settings.timezone}
                        onChange={(e) => handleSettingChange('timezone', e.target.value)}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      >
                        <option value="America/New_York">Eastern Time (ET)</option>
                        <option value="America/Chicago">Central Time (CT)</option>
                        <option value="America/Denver">Mountain Time (MT)</option>
                        <option value="America/Los_Angeles">Pacific Time (PT)</option>
                        <option value="Europe/London">London (GMT)</option>
                        <option value="Europe/Frankfurt">Frankfurt (CET)</option>
                        <option value="Asia/Tokyo">Tokyo (JST)</option>
                      </select>
                    </div>
                  </div>
                </Card>
              </Grid>
            )}

            {activeTab === 'display' && (
              <Card title="Display Settings">
                <Grid cols={{ default: 1, lg: 2 }}>
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium text-white">Layout Options</h3>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Compact Dashboard View
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.compactMode}
                        onChange={(e) => handleSettingChange('compactMode', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Auto-refresh Data
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.autoRefresh}
                        onChange={(e) => handleSettingChange('autoRefresh', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <h3 className="text-lg font-medium text-white">Currency Format</h3>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Display Currency
                      </label>
                      <select
                        value={settings.currency}
                        onChange={(e) => handleSettingChange('currency', e.target.value)}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      >
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Decimal Precision
                      </label>
                      <select
                        value={settings.decimalPlaces}
                        onChange={(e) => handleSettingChange('decimalPlaces', parseInt(e.target.value))}
                        className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                      >
                        <option value={0}>Whole numbers (1,234)</option>
                        <option value={2}>Two decimals (1,234.56)</option>
                        <option value={4}>Four decimals (1,234.5678)</option>
                        <option value={5}>Five decimals (1,234.56789)</option>
                      </select>
                    </div>
                  </div>
                </Grid>
              </Card>
            )}

            {activeTab === 'alerts' && (
              <Grid cols={{ default: 1, lg: 2 }}>
                <Card title="Notification Preferences">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Email Notifications
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.emailNotifications}
                        onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Push Notifications
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.pushNotifications}
                        onChange={(e) => handleSettingChange('pushNotifications', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Sound Alerts
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.soundAlerts}
                        onChange={(e) => handleSettingChange('soundAlerts', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </Card>

                <Card title="Alert Types">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Risk Level Alerts
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.riskLevelAlerts}
                        onChange={(e) => handleSettingChange('riskLevelAlerts', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-300">
                        Profit Target Alerts
                      </label>
                      <input
                        type="checkbox"
                        checked={settings.profitTargetAlerts}
                        onChange={(e) => handleSettingChange('profitTargetAlerts', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    <div className="pt-4 border-t border-gray-700">
                      <p className="text-sm text-gray-400">
                        Configure when and how you receive alerts about your trading activity.
                      </p>
                    </div>
                  </div>
                </Card>
              </Grid>
            )}

            {activeTab === 'api' && (
              <Card title="API Configuration">
                <div className="space-y-6">
                  <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded">
                    <p className="text-yellow-400 text-sm">
                      ⚠️ API credentials are stored locally in your browser. Never share these credentials.
                    </p>
                  </div>
                  
                  <Grid cols={{ default: 1, lg: 2 }}>
                    <div className="space-y-4">
                      <h3 className="text-lg font-medium text-white">OANDA Configuration</h3>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Environment
                        </label>
                        <select
                          value={settings.oandaEnvironment}
                          onChange={(e) => handleSettingChange('oandaEnvironment', e.target.value)}
                          className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                        >
                          <option value="practice">Practice (Demo)</option>
                          <option value="live">Live Trading</option>
                        </select>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Key
                        </label>
                        <input
                          type="password"
                          value={settings.oandaApiKey}
                          onChange={(e) => handleSettingChange('oandaApiKey', e.target.value)}
                          placeholder="Enter your OANDA API key"
                          className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Account ID
                        </label>
                        <input
                          type="text"
                          value={settings.oandaAccountId}
                          onChange={(e) => handleSettingChange('oandaAccountId', e.target.value)}
                          placeholder="Enter your OANDA account ID"
                          className="w-full p-2 bg-gray-800 border border-gray-600 rounded text-white"
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <h3 className="text-lg font-medium text-white">Connection Status</h3>
                      
                      <div className="p-4 bg-gray-800 rounded">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">OANDA API</span>
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                            <span className="text-sm text-yellow-400">Not Connected</span>
                          </div>
                        </div>
                        <p className="text-xs text-gray-400">
                          Configure your API credentials to connect to OANDA
                        </p>
                      </div>
                      
                      <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded">
                        <h4 className="text-sm font-medium text-blue-400 mb-2">Getting Started</h4>
                        <ol className="text-xs text-gray-400 space-y-1">
                          <li>1. Log into your OANDA account</li>
                          <li>2. Generate an API key in account settings</li>
                          <li>3. Copy your account ID from the dashboard</li>
                          <li>4. Enter the credentials above and save</li>
                        </ol>
                      </div>
                    </div>
                  </Grid>
                </div>
              </Card>
            )}
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}