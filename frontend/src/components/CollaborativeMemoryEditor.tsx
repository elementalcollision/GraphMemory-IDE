/**
 * Collaborative Memory Editor for GraphMemory-IDE
 * 
 * Main component that orchestrates all collaborative editing features.
 * Integrates Monaco Editor, User Presence, Conflict Resolution, and WebSocket-CRDT bridge.
 * 
 * Features:
 * - Complete collaborative memory editing interface
 * - Real-time synchronization with backend CRDT engine
 * - Live user presence and cursor tracking
 * - Conflict detection and resolution UI
 * - Performance optimized for <500ms real-time updates
 * - Responsive design for desktop and mobile
 * 
 * Week 2 Target: 1,200+ lines of production-ready collaborative UI
 */

import React, { useState, useCallback, useMemo, memo, Suspense } from 'react'
import MonacoCollaborativeEditor from './MonacoCollaborativeEditor'
import UserPresence, { CompactUserPresence } from './UserPresence'
import ConflictVisualization, { ConflictIndicator } from './ConflictVisualization'
import { useCollaborativeMemory, useMonacoCollaboration, CollaborationConfig } from '../hooks/useCollaboration'
import { 
  Save, 
  Share2, 
  Settings, 
  Activity, 
  FileText, 
  Tag, 
  Users, 
  AlertTriangle,
  Wifi,
  WifiOff,
  Maximize2,
  Minimize2,
  Eye,
  EyeOff,
  MoreVertical
} from 'lucide-react'
import clsx from 'clsx'

interface CollaborativeMemoryEditorProps {
  memoryId: string
  tenantId: string
  userId: string
  userInfo: {
    name: string
    email: string
    avatar?: string
    color?: string
  }
  authToken: string
  className?: string
  readOnly?: boolean
  onSave?: (data: any) => Promise<void>
  onShare?: () => void
  onSettings?: () => void
}

interface MemoryMetadata {
  title: string
  tags: string[]
  metadata: Record<string, any>
}

const LoadingSpinner: React.FC = memo(() => (
  <div className="flex items-center justify-center p-8">
    <div className="flex items-center gap-3">
      <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      <span className="text-gray-600">Connecting to collaboration server...</span>
    </div>
  </div>
))

const ErrorDisplay: React.FC<{ error: string; onRetry?: () => void }> = memo(({ error, onRetry }) => (
  <div className="flex items-center justify-center p-8">
    <div className="text-center max-w-md">
      <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">Connection Error</h3>
      <p className="text-gray-600 mb-4">{error}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Retry Connection
        </button>
      )}
    </div>
  </div>
))

const MemoryHeader: React.FC<{
  title: string
  onTitleChange: (title: string) => void
  isConnected: boolean
  conflictCount: number
  onlineUsers: number
  readOnly: boolean
  onSave?: () => void
  onShare?: () => void
  onSettings?: () => void
  isSaving?: boolean
}> = memo(({
  title,
  onTitleChange,
  isConnected,
  conflictCount,
  onlineUsers,
  readOnly,
  onSave,
  onShare,
  onSettings,
  isSaving = false
}) => {
  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [tempTitle, setTempTitle] = useState(title)
  
  const handleTitleSubmit = useCallback(() => {
    if (tempTitle.trim() && tempTitle !== title) {
      onTitleChange(tempTitle.trim())
    }
    setIsEditingTitle(false)
  }, [tempTitle, title, onTitleChange])
  
  const handleTitleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleTitleSubmit()
    } else if (e.key === 'Escape') {
      setTempTitle(title)
      setIsEditingTitle(false)
    }
  }, [handleTitleSubmit, title])
  
  return (
    <div className="memory-header bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Title and status */}
        <div className="flex items-center gap-4 flex-1 min-w-0">
          {isEditingTitle && !readOnly ? (
            <input
              type="text"
              value={tempTitle}
              onChange={(e) => setTempTitle(e.target.value)}
              onBlur={handleTitleSubmit}
              onKeyDown={handleTitleKeyDown}
              className="text-xl font-semibold bg-transparent border-none outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1 flex-1 min-w-0"
              autoFocus
            />
          ) : (
            <h1
              className={clsx(
                'text-xl font-semibold text-gray-900 flex-1 min-w-0 truncate',
                !readOnly && 'cursor-pointer hover:bg-gray-50 rounded px-2 py-1'
              )}
              onClick={() => !readOnly && setIsEditingTitle(true)}
              title={title}
            >
              {title || 'Untitled Memory'}
            </h1>
          )}
          
          {/* Connection status */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              {isConnected ? (
                <Wifi className="w-4 h-4 text-green-500" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" />
              )}
              <span className={clsx(
                'text-xs',
                isConnected ? 'text-green-600' : 'text-red-600'
              )}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            
            <ConflictIndicator conflictCount={conflictCount} />
            
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Users className="w-3 h-3" />
              <span>{onlineUsers} online</span>
            </div>
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-2 ml-4">
          {onSave && !readOnly && (
            <button
              onClick={onSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          )}
          
          {onShare && (
            <button
              onClick={onShare}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
          )}
          
          {onSettings && (
            <button
              onClick={onSettings}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              <Settings className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
})

const MemoryMetadataPanel: React.FC<{
  metadata: MemoryMetadata
  onAddTag: (tag: string) => void
  onRemoveTag: (tag: string) => void
  onUpdateMetadata: (key: string, value: any) => void
  readOnly: boolean
  isVisible: boolean
  onToggleVisibility: () => void
}> = memo(({
  metadata,
  onAddTag,
  onRemoveTag,
  onUpdateMetadata,
  readOnly,
  isVisible,
  onToggleVisibility
}) => {
  const [newTag, setNewTag] = useState('')
  
  const handleAddTag = useCallback(() => {
    if (newTag.trim() && !metadata.tags.includes(newTag.trim())) {
      onAddTag(newTag.trim())
      setNewTag('')
    }
  }, [newTag, metadata.tags, onAddTag])
  
  const handleTagKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAddTag()
    }
  }, [handleAddTag])
  
  return (
    <div className="metadata-panel bg-gray-50 border-b border-gray-200">
      <div className="px-6 py-3">
        <button
          onClick={onToggleVisibility}
          className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          Memory Details
        </button>
      </div>
      
      {isVisible && (
        <div className="px-6 pb-4 space-y-4">
          {/* Tags */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">Tags</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {metadata.tags.map(tag => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                >
                  <Tag className="w-3 h-3" />
                  {tag}
                  {!readOnly && (
                    <button
                      onClick={() => onRemoveTag(tag)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      ×
                    </button>
                  )}
                </span>
              ))}
            </div>
            
            {!readOnly && (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={handleTagKeyDown}
                  placeholder="Add tag..."
                  className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded"
                />
                <button
                  onClick={handleAddTag}
                  disabled={!newTag.trim()}
                  className="px-3 py-1 bg-blue-600 text-white text-xs rounded disabled:opacity-50"
                >
                  Add
                </button>
              </div>
            )}
          </div>
          
          {/* Additional metadata can be added here */}
          <div className="text-xs text-gray-500">
            <div>Created: {metadata.metadata.created || 'Unknown'}</div>
            <div>Modified: {metadata.metadata.lastModified || 'Unknown'}</div>
            <div>Version: {metadata.metadata.version || 1}</div>
          </div>
        </div>
      )}
    </div>
  )
})

const CollaborativeMemoryEditor: React.FC<CollaborativeMemoryEditorProps> = memo(({
  memoryId,
  tenantId,
  userId,
  userInfo,
  authToken,
  className = '',
  readOnly = false,
  onSave,
  onShare,
  onSettings
}) => {
  // Local state
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showSidebar, setShowSidebar] = useState(true)
  const [showMetadata, setShowMetadata] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  
  // Collaboration configuration
  const config = useMemo<CollaborationConfig>(() => ({
    memoryId,
    tenantId,
    userId,
    userInfo,
    authToken,
    serverUrl: 'ws://localhost:8000'
  }), [memoryId, tenantId, userId, userInfo, authToken])
  
  // Main collaboration hook
  const collaboration = useCollaborativeMemory(config)
  const {
    memoryState,
    isConnected,
    users,
    conflicts,
    isLoading,
    error,
    performance,
    updateTitle,
    updateContent,
    addTag,
    removeTag,
    updateMetadata,
    resolveConflict,
    getProvider
  } = collaboration
  
  // Monaco integration
  const { yText, isReady: isMonacoReady } = useMonacoCollaboration(getProvider(), 'content')
  
  // Event handlers
  const handleSave = useCallback(async () => {
    if (!onSave) return
    
    setIsSaving(true)
    try {
      await onSave({
        title: memoryState.title,
        content: memoryState.content,
        tags: memoryState.tags,
        metadata: memoryState.metadata
      })
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setIsSaving(false)
    }
  }, [onSave, memoryState])
  
  const handleUserClick = useCallback((user: any) => {
    // Focus on user's cursor position
    console.log('Focusing on user:', user.userInfo.name)
  }, [])
  
  const handleCursorChange = useCallback((cursor: { line: number; column: number }) => {
    // Handle cursor position changes
    console.log('Cursor moved to:', cursor)
  }, [])
  
  const handleSelectionChange = useCallback((selection: any) => {
    // Handle selection changes
    console.log('Selection changed:', selection)
  }, [])
  
  // Memoized values
  const onlineUsers = useMemo(() => users.filter(u => u.status === 'online'), [users])
  const activeConflicts = useMemo(() => conflicts.filter(c => !c.resolved), [conflicts])
  
  // Error state
  if (error) {
    return (
      <div className={clsx('collaborative-memory-editor', className)}>
        <ErrorDisplay error={error} onRetry={() => window.location.reload()} />
      </div>
    )
  }
  
  // Loading state
  if (isLoading || !isMonacoReady) {
    return (
      <div className={clsx('collaborative-memory-editor', className)}>
        <LoadingSpinner />
      </div>
    )
  }
  
  return (
    <div className={clsx(
      'collaborative-memory-editor flex flex-col h-full bg-white',
      isFullscreen && 'fixed inset-0 z-50',
      className
    )}>
      {/* Header */}
      <MemoryHeader
        title={memoryState.title}
        onTitleChange={updateTitle}
        isConnected={isConnected}
        conflictCount={activeConflicts.length}
        onlineUsers={onlineUsers.length}
        readOnly={readOnly}
        onSave={handleSave}
        onShare={onShare}
        onSettings={onSettings}
        isSaving={isSaving}
      />
      
      {/* Metadata panel */}
      <MemoryMetadataPanel
        metadata={{
          title: memoryState.title,
          tags: memoryState.tags,
          metadata: memoryState.metadata
        }}
        onAddTag={addTag}
        onRemoveTag={removeTag}
        onUpdateMetadata={updateMetadata}
        readOnly={readOnly}
        isVisible={showMetadata}
        onToggleVisibility={() => setShowMetadata(!showMetadata)}
      />
      
      {/* Main content area */}
      <div className="flex flex-1 min-h-0">
        {/* Editor */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Editor toolbar */}
          <div className="editor-toolbar bg-gray-50 border-b border-gray-200 px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <CompactUserPresence
                users={users}
                currentUserId={userId}
                onClick={handleUserClick}
                className="user-presence-compact"
              />
              
              {/* Performance indicator */}
              {performance.targetCompliance === false && (
                <div className="flex items-center gap-1 text-xs text-orange-600">
                  <Activity className="w-3 h-3" />
                  <span>High latency: {Math.round(performance.latency)}ms</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded"
                title={showSidebar ? 'Hide sidebar' : 'Show sidebar'}
              >
                <MoreVertical className="w-4 h-4" />
              </button>
              
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded"
                title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
            </div>
          </div>
          
          {/* Monaco Editor */}
          <div className="flex-1 min-h-0">
            <Suspense fallback={<LoadingSpinner />}>
              <MonacoCollaborativeEditor
                provider={getProvider()}
                yText={yText}
                language="markdown"
                theme="vs-dark"
                readOnly={readOnly}
                height="100%"
                onCursorChange={handleCursorChange}
                onSelectionChange={handleSelectionChange}
                options={{
                  lineNumbers: 'on',
                  minimap: { enabled: false },
                  fontSize: 14,
                  wordWrap: 'on',
                  scrollBeyondLastLine: false
                }}
              />
            </Suspense>
          </div>
        </div>
        
        {/* Sidebar */}
        {showSidebar && (
          <div className="w-80 border-l border-gray-200 bg-gray-50 flex flex-col">
            {/* Conflicts panel */}
            {activeConflicts.length > 0 && (
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  Conflicts ({activeConflicts.length})
                </h3>
                <ConflictVisualization
                  conflicts={conflicts}
                  onResolveConflict={resolveConflict}
                  maxVisible={3}
                  showPreview={true}
                  autoCollapse={true}
                />
              </div>
            )}
            
            {/* User presence panel */}
            <div className="flex-1 p-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Collaborators ({users.length})
              </h3>
              <UserPresence
                users={users}
                currentUserId={userId}
                layout="vertical"
                size="md"
                showActivity={true}
                showCursors={true}
                onClick={handleUserClick}
              />
            </div>
            
            {/* Activity feed (future enhancement) */}
            <div className="p-4 border-t border-gray-200">
              <h3 className="text-sm font-medium text-gray-900 mb-2 flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Recent Activity
              </h3>
              <div className="text-xs text-gray-500">
                Activity feed coming soon...
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Performance overlay (development only) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 bg-black bg-opacity-75 text-white text-xs p-2 rounded">
          <div>Latency: {Math.round(performance.latency)}ms</div>
          <div>Messages: {performance.messageCount}</div>
          <div>Connected: {isConnected ? 'Yes' : 'No'}</div>
          <div>Users: {users.length}</div>
        </div>
      )}
    </div>
  )
})

CollaborativeMemoryEditor.displayName = 'CollaborativeMemoryEditor'

export default CollaborativeMemoryEditor 