/**
 * Main App Component for GraphMemory-IDE Frontend
 * 
 * Demonstrates the collaborative memory editor with sample configuration.
 * This serves as the entry point for the React collaborative UI.
 */

import React, { useState, useCallback } from 'react'
import CollaborativeMemoryEditor from './components/CollaborativeMemoryEditor'
import { v4 as uuidv4 } from 'uuid'

// Sample configuration for development/demo
const SAMPLE_CONFIG = {
  memoryId: 'memory-001',
  tenantId: 'tenant-demo',
  userId: 'user-' + Math.random().toString(36).substr(2, 9),
  userInfo: {
    name: 'Demo User',
    email: 'demo@graphmemory.com',
    avatar: undefined,
    color: '#4F46E5'
  },
  authToken: 'demo-token-' + Date.now()
}

function App() {
  const [config, setConfig] = useState(SAMPLE_CONFIG)
  const [isConfigOpen, setIsConfigOpen] = useState(false)

  const handleSave = useCallback(async (data: any) => {
    console.log('Saving memory data:', data)
    // Simulate save delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('Memory saved successfully')
  }, [])

  const handleShare = useCallback(() => {
    console.log('Sharing memory:', config.memoryId)
    // Implement sharing logic
  }, [config.memoryId])

  const handleSettings = useCallback(() => {
    setIsConfigOpen(true)
  }, [])

  const updateConfig = useCallback((updates: Partial<typeof config>) => {
    setConfig(prev => ({ ...prev, ...updates }))
  }, [])

  return (
    <div className="App h-screen bg-gray-100">
      {/* Demo header */}
      <div className="bg-blue-600 text-white px-6 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">GraphMemory-IDE</h1>
            <p className="text-blue-100 text-sm">Collaborative Memory Editor Demo</p>
          </div>
          <button
            onClick={() => setIsConfigOpen(true)}
            className="px-3 py-1 bg-blue-500 hover:bg-blue-400 rounded text-sm"
          >
            Configure
          </button>
        </div>
      </div>

      {/* Main editor */}
      <div className="h-[calc(100vh-64px)]">
        <CollaborativeMemoryEditor
          memoryId={config.memoryId}
          tenantId={config.tenantId}
          userId={config.userId}
          userInfo={config.userInfo}
          authToken={config.authToken}
          onSave={handleSave}
          onShare={handleShare}
          onSettings={handleSettings}
          className="h-full"
        />
      </div>

      {/* Configuration modal */}
      {isConfigOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 max-w-full mx-4">
            <h2 className="text-lg font-semibold mb-4">Configuration</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Memory ID
                </label>
                <input
                  type="text"
                  value={config.memoryId}
                  onChange={(e) => updateConfig({ memoryId: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tenant ID
                </label>
                <input
                  type="text"
                  value={config.tenantId}
                  onChange={(e) => updateConfig({ tenantId: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  User Name
                </label>
                <input
                  type="text"
                  value={config.userInfo.name}
                  onChange={(e) => updateConfig({ 
                    userInfo: { ...config.userInfo, name: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  User Email
                </label>
                <input
                  type="email"
                  value={config.userInfo.email}
                  onChange={(e) => updateConfig({ 
                    userInfo: { ...config.userInfo, email: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  User Color
                </label>
                <input
                  type="color"
                  value={config.userInfo.color}
                  onChange={(e) => updateConfig({ 
                    userInfo: { ...config.userInfo, color: e.target.value }
                  })}
                  className="w-full h-10 border border-gray-300 rounded-lg"
                />
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => setIsConfigOpen(false)}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Apply
              </button>
              <button
                onClick={() => {
                  setConfig(SAMPLE_CONFIG)
                  setIsConfigOpen(false)
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App 