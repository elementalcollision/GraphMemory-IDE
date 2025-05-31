/**
 * React Collaboration Hooks for GraphMemory-IDE
 * 
 * Custom hooks that integrate React 18 with Yjs CRDT and our WebSocket-CRDT bridge.
 * Optimized for <500ms real-time update performance using React 18 concurrent features.
 * 
 * Features:
 * - useCollaborativeMemory: Main hook for memory collaboration
 * - useAwareness: Live cursors and presence tracking
 * - useConflictState: Conflict detection and resolution
 * - Performance optimization with useDeferredValue and useTransition
 * 
 * Integration: CustomWebSocketProvider + Yjs + React 18
 */

import { useEffect, useState, useRef, useMemo, useCallback, useDeferredValue, useTransition, useSyncExternalStore } from 'react'
import * as Y from 'yjs'
import { Awareness } from 'y-protocols/awareness'
import { CustomWebSocketProvider, CollaborationConfig } from '../providers/CustomWebSocketProvider'

// Types
export interface MemoryState {
  title: string
  content: string
  tags: string[]
  metadata: Record<string, any>
  version: number
  lastModified: string
  lastModifiedBy: string
  collaborators: string[]
}

export interface UserPresence {
  userId: string
  userInfo: {
    name: string
    email: string
    avatar?: string
    color: string
  }
  cursor?: {
    line: number
    column: number
  }
  selection?: {
    start: { line: number; column: number }
    end: { line: number; column: number }
  }
  status: 'online' | 'away' | 'offline'
  lastSeen: Date
}

export interface ConflictInfo {
  id: string
  type: 'text' | 'structure' | 'metadata'
  field: string
  localValue: any
  remoteValue: any
  timestamp: Date
  users: string[]
  resolved: boolean
}

export interface CollaborationState {
  memoryState: MemoryState
  isConnected: boolean
  users: UserPresence[]
  conflicts: ConflictInfo[]
  isLoading: boolean
  error: string | null
  performance: {
    latency: number
    messageCount: number
    targetCompliance: boolean
  }
}

/**
 * Main collaboration hook - integrates React with Yjs and WebSocket-CRDT bridge
 */
export function useCollaborativeMemory(config: CollaborationConfig): CollaborationState & {
  updateTitle: (title: string) => void
  updateContent: (content: string) => void
  addTag: (tag: string) => void
  removeTag: (tag: string) => void
  updateMetadata: (key: string, value: any) => void
  resolveConflict: (conflictId: string, resolution: 'local' | 'remote' | 'custom', customValue?: any) => void
  getYDoc: () => Y.Doc
  getProvider: () => CustomWebSocketProvider | null
} {
  // Yjs setup
  const ydoc = useRef<Y.Doc>()
  const provider = useRef<CustomWebSocketProvider>()
  
  // React state
  const [isConnected, setIsConnected] = useState(false)
  const [users, setUsers] = useState<UserPresence[]>([])
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [performance, setPerformance] = useState({
    latency: 0,
    messageCount: 0,
    targetCompliance: true
  })
  
  // Performance optimization hooks
  const [isPending, startTransition] = useTransition()
  
  // Initialize Yjs document and provider
  useEffect(() => {
    // Create Yjs document
    ydoc.current = new Y.Doc()
    
    // Create our custom provider
    provider.current = new CustomWebSocketProvider(ydoc.current, config)
    
    // Set up event listeners
    const handleConnected = () => {
      setIsConnected(true)
      setIsLoading(false)
      setError(null)
    }
    
    const handleDisconnected = () => {
      setIsConnected(false)
    }
    
    const handleError = (err: any) => {
      setError(err.message || 'Connection error')
      setIsLoading(false)
    }
    
    const handleConflictDetected = (conflictData: any) => {
      startTransition(() => {
        setConflicts(prev => [...prev, {
          id: conflictData.id || Date.now().toString(),
          type: conflictData.type || 'text',
          field: conflictData.field || 'content',
          localValue: conflictData.localValue,
          remoteValue: conflictData.remoteValue,
          timestamp: new Date(),
          users: conflictData.users || [],
          resolved: false
        }])
      })
    }
    
    const handlePresenceUpdate = (presenceData: any) => {
      startTransition(() => {
        setUsers(prev => {
          const existing = prev.find(u => u.userId === presenceData.user_id)
          const updated: UserPresence = {
            userId: presenceData.user_id,
            userInfo: presenceData.user_info || existing?.userInfo || {
              name: 'Unknown User',
              email: '',
              color: '#666666'
            },
            cursor: presenceData.cursor_position,
            selection: presenceData.selection_range,
            status: presenceData.status || 'online',
            lastSeen: new Date()
          }
          
          if (existing) {
            return prev.map(u => u.userId === presenceData.user_id ? updated : u)
          } else {
            return [...prev, updated]
          }
        })
      })
    }
    
    // Subscribe to provider events
    provider.current.on('connected', handleConnected)
    provider.current.on('disconnected', handleDisconnected)
    provider.current.on('error', handleError)
    provider.current.on('conflict-detected', handleConflictDetected)
    provider.current.on('presence-update', handlePresenceUpdate)
    
    // Performance monitoring
    const performanceInterval = setInterval(() => {
      if (provider.current) {
        const metrics = provider.current.getPerformanceMetrics()
        setPerformance({
          latency: metrics.averageLatency,
          messageCount: metrics.messageCount,
          targetCompliance: metrics.targetCompliance.latencyUnder50ms
        })
      }
    }, 5000)
    
    return () => {
      clearInterval(performanceInterval)
      provider.current?.destroy()
    }
  }, [config.memoryId, config.tenantId, config.userId])
  
  // Subscribe to Yjs memory state changes
  const memoryState = useSyncExternalStore(
    useCallback((callback) => {
      if (!ydoc.current) return () => {}
      
      const yTitle = ydoc.current.getText('title')
      const yContent = ydoc.current.getText('content')
      const yTags = ydoc.current.getArray('tags')
      const yMetadata = ydoc.current.getMap('metadata')
      
      const handleUpdate = () => callback()
      
      yTitle.observe(handleUpdate)
      yContent.observe(handleUpdate)
      yTags.observe(handleUpdate)
      yMetadata.observe(handleUpdate)
      
      return () => {
        yTitle.unobserve(handleUpdate)
        yContent.unobserve(handleUpdate)
        yTags.unobserve(handleUpdate)
        yMetadata.unobserve(handleUpdate)
      }
    }, []),
    () => {
      if (!ydoc.current) {
        return {
          title: '',
          content: '',
          tags: [],
          metadata: {},
          version: 0,
          lastModified: new Date().toISOString(),
          lastModifiedBy: config.userId,
          collaborators: []
        }
      }
      
      const yTitle = ydoc.current.getText('title')
      const yContent = ydoc.current.getText('content')
      const yTags = ydoc.current.getArray('tags')
      const yMetadata = ydoc.current.getMap('metadata')
      
      return {
        title: yTitle.toString(),
        content: yContent.toString(),
        tags: yTags.toArray() as string[],
        metadata: yMetadata.toJSON(),
        version: ydoc.current.getMap('meta').get('version') || 1,
        lastModified: ydoc.current.getMap('meta').get('lastModified') || new Date().toISOString(),
        lastModifiedBy: ydoc.current.getMap('meta').get('lastModifiedBy') || config.userId,
        collaborators: users.map(u => u.userId)
      }
    }
  )
  
  // Deferred conflicts for performance (non-urgent updates)
  const deferredConflicts = useDeferredValue(conflicts)
  
  // Update functions
  const updateTitle = useCallback((title: string) => {
    if (!ydoc.current) return
    
    startTransition(() => {
      const yTitle = ydoc.current!.getText('title')
      yTitle.delete(0, yTitle.length)
      yTitle.insert(0, title)
      
      // Update metadata
      const yMeta = ydoc.current!.getMap('meta')
      yMeta.set('lastModified', new Date().toISOString())
      yMeta.set('lastModifiedBy', config.userId)
    })
  }, [config.userId])
  
  const updateContent = useCallback((content: string) => {
    if (!ydoc.current) return
    
    const yContent = ydoc.current.getText('content')
    yContent.delete(0, yContent.length)
    yContent.insert(0, content)
    
    // Update metadata
    const yMeta = ydoc.current.getMap('meta')
    yMeta.set('lastModified', new Date().toISOString())
    yMeta.set('lastModifiedBy', config.userId)
  }, [config.userId])
  
  const addTag = useCallback((tag: string) => {
    if (!ydoc.current) return
    
    startTransition(() => {
      const yTags = ydoc.current!.getArray('tags')
      if (!yTags.toArray().includes(tag)) {
        yTags.push([tag])
      }
    })
  }, [])
  
  const removeTag = useCallback((tag: string) => {
    if (!ydoc.current) return
    
    startTransition(() => {
      const yTags = ydoc.current!.getArray('tags')
      const tags = yTags.toArray()
      const index = tags.indexOf(tag)
      if (index !== -1) {
        yTags.delete(index, 1)
      }
    })
  }, [])
  
  const updateMetadata = useCallback((key: string, value: any) => {
    if (!ydoc.current) return
    
    startTransition(() => {
      const yMetadata = ydoc.current!.getMap('metadata')
      yMetadata.set(key, value)
    })
  }, [])
  
  const resolveConflict = useCallback((conflictId: string, resolution: 'local' | 'remote' | 'custom', customValue?: any) => {
    startTransition(() => {
      setConflicts(prev => prev.map(conflict => 
        conflict.id === conflictId 
          ? { ...conflict, resolved: true }
          : conflict
      ))
    })
    
    // Apply resolution to Yjs document
    const conflict = conflicts.find(c => c.id === conflictId)
    if (conflict && ydoc.current) {
      let valueToApply: any
      
      switch (resolution) {
        case 'local':
          valueToApply = conflict.localValue
          break
        case 'remote':
          valueToApply = conflict.remoteValue
          break
        case 'custom':
          valueToApply = customValue
          break
      }
      
      // Apply to appropriate Yjs structure
      if (conflict.field === 'title') {
        const yTitle = ydoc.current.getText('title')
        yTitle.delete(0, yTitle.length)
        yTitle.insert(0, valueToApply)
      } else if (conflict.field === 'content') {
        const yContent = ydoc.current.getText('content')
        yContent.delete(0, yContent.length)
        yContent.insert(0, valueToApply)
      }
    }
  }, [conflicts])
  
  const getYDoc = useCallback(() => ydoc.current!, [])
  const getProvider = useCallback(() => provider.current || null, [])
  
  return {
    memoryState,
    isConnected,
    users,
    conflicts: deferredConflicts,
    isLoading: isLoading || isPending,
    error,
    performance,
    updateTitle,
    updateContent,
    addTag,
    removeTag,
    updateMetadata,
    resolveConflict,
    getYDoc,
    getProvider
  }
}

/**
 * Hook for awareness (live cursors and presence)
 */
export function useAwareness(provider: CustomWebSocketProvider | null): {
  users: Map<number, any>
  setLocalCursor: (cursor: { line: number; column: number } | null) => void
  setLocalSelection: (selection: { start: { line: number; column: number }; end: { line: number; column: number } } | null) => void
  setUserInfo: (userInfo: { name: string; email: string; avatar?: string; color?: string }) => void
} {
  const [users, setUsers] = useState<Map<number, any>>(new Map())
  
  // Subscribe to awareness changes
  useEffect(() => {
    if (!provider) return
    
    const awareness = provider.getAwareness()
    
    const handleAwarenessChange = () => {
      setUsers(new Map(awareness.getStates()))
    }
    
    awareness.on('change', handleAwarenessChange)
    handleAwarenessChange() // Initial state
    
    return () => {
      awareness.off('change', handleAwarenessChange)
    }
  }, [provider])
  
  const setLocalCursor = useCallback((cursor: { line: number; column: number } | null) => {
    if (!provider) return
    
    const awareness = provider.getAwareness()
    awareness.setLocalStateField('cursor', cursor)
  }, [provider])
  
  const setLocalSelection = useCallback((selection: { start: { line: number; column: number }; end: { line: number; column: number } } | null) => {
    if (!provider) return
    
    const awareness = provider.getAwareness()
    awareness.setLocalStateField('selection', selection)
  }, [provider])
  
  const setUserInfo = useCallback((userInfo: { name: string; email: string; avatar?: string; color?: string }) => {
    if (!provider) return
    
    const awareness = provider.getAwareness()
    awareness.setLocalStateField('user', userInfo)
  }, [provider])
  
  return {
    users,
    setLocalCursor,
    setLocalSelection,
    setUserInfo
  }
}

/**
 * Hook for Monaco Editor integration with performance optimization
 */
export function useMonacoCollaboration(
  provider: CustomWebSocketProvider | null,
  fieldName: string = 'content'
): {
  yText: Y.Text | null
  isReady: boolean
} {
  const [yText, setYText] = useState<Y.Text | null>(null)
  const [isReady, setIsReady] = useState(false)
  
  useEffect(() => {
    if (!provider) return
    
    const ydoc = provider.getAwareness().doc
    const text = ydoc.getText(fieldName)
    
    setYText(text)
    setIsReady(true)
    
    return () => {
      setYText(null)
      setIsReady(false)
    }
  }, [provider, fieldName])
  
  return { yText, isReady }
} 