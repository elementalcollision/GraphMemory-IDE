/**
 * Custom WebSocket Provider for GraphMemory-IDE
 * 
 * This provider bridges Yjs frontend CRDT operations with our existing
 * WebSocket-CRDT bridge backend (Week 1 implementation). It replaces
 * the standard y-websocket provider to integrate with our Phase 2.1
 * Memory Collaboration Engine.
 * 
 * Features:
 * - Direct integration with WebSocket-CRDT bridge
 * - Awareness synchronization for live cursors
 * - Performance optimization for <500ms real-time updates
 * - Automatic reconnection and state synchronization
 * 
 * Integration: server/collaboration/websocket_crdt_bridge.py
 * Performance Target: <500ms cross-client latency
 */

import * as Y from 'yjs'
import { Observable } from 'lib0/observable'
import * as encoding from 'lib0/encoding'
import * as decoding from 'lib0/decoding'
import * as syncProtocol from 'y-protocols/sync'
import * as awarenessProtocol from 'y-protocols/awareness'
import { Awareness } from 'y-protocols/awareness'

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: number
  message_id?: string
  user_id?: string
  room_id?: string
}

export interface CollaborationConfig {
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
  serverUrl?: string
}

export class CustomWebSocketProvider extends Observable<string> {
  private doc: Y.Doc
  private awareness: Awareness
  private config: CollaborationConfig
  private websocket: WebSocket | null = null
  private connected = false
  private reconnectTimeoutId: number | null = null
  private lastHeartbeat = Date.now()
  private heartbeatInterval: number | null = null
  
  // Performance tracking
  private messageLatencies: number[] = []
  private connectionStartTime = 0
  
  // Room and connection state
  private roomId: string
  private serverUrl: string

  constructor(doc: Y.Doc, config: CollaborationConfig) {
    super()
    
    this.doc = doc
    this.config = config
    this.roomId = `${config.tenantId}:${config.memoryId}`
    this.serverUrl = config.serverUrl || 'ws://localhost:8000'
    
    // Initialize awareness
    this.awareness = new Awareness(doc)
    this.awareness.setLocalState({
      user: {
        name: config.userInfo.name,
        email: config.userInfo.email,
        avatar: config.userInfo.avatar,
        color: config.userInfo.color || this.generateUserColor(config.userId),
      },
      cursor: null,
      selection: null,
    })
    
    // Set up Yjs document observers
    this.doc.on('update', this.handleDocumentUpdate.bind(this))
    this.awareness.on('update', this.handleAwarenessUpdate.bind(this))
    
    // Connect to WebSocket
    this.connect()
  }

  private generateUserColor(userId: string): string {
    // Generate consistent color for user based on userId
    const colors = [
      '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
      '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
    ]
    const hash = userId.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0)
      return a & a
    }, 0)
    return colors[Math.abs(hash) % colors.length]
  }

  private connect(): void {
    if (this.websocket && this.websocket.readyState === WebSocket.CONNECTING) {
      return
    }

    this.connectionStartTime = Date.now()
    const wsUrl = `${this.serverUrl}/ws/collaborate/${this.config.tenantId}/${this.config.memoryId}?token=${this.config.authToken}&user_id=${this.config.userId}`
    
    try {
      this.websocket = new WebSocket(wsUrl)
      this.websocket.binaryType = 'arraybuffer'
      
      this.websocket.onopen = this.handleWebSocketOpen.bind(this)
      this.websocket.onmessage = this.handleWebSocketMessage.bind(this)
      this.websocket.onclose = this.handleWebSocketClose.bind(this)
      this.websocket.onerror = this.handleWebSocketError.bind(this)
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.scheduleReconnect()
    }
  }

  private handleWebSocketOpen(): void {
    const connectionTime = Date.now() - this.connectionStartTime
    console.log(`WebSocket connected in ${connectionTime}ms`)
    
    // Track connection performance (target <100ms)
    if (connectionTime > 100) {
      console.warn(`Connection time ${connectionTime}ms exceeds 100ms target`)
    }
    
    this.connected = true
    this.emit('connected', [])
    
    // Send initial sync state
    this.sendYjsSync()
    
    // Start heartbeat
    this.startHeartbeat()
    
    // Clear reconnect timeout
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId)
      this.reconnectTimeoutId = null
    }
  }

  private handleWebSocketMessage(event: MessageEvent): void {
    const messageStartTime = Date.now()
    
    try {
      // Handle binary Yjs updates
      if (event.data instanceof ArrayBuffer) {
        this.handleYjsBinaryMessage(event.data)
        return
      }
      
      // Handle JSON messages from our WebSocket-CRDT bridge
      const message: WebSocketMessage = JSON.parse(event.data)
      
      switch (message.type) {
        case 'operation_applied':
          this.handleOperationApplied(message)
          break
        case 'operation_broadcast':
          this.handleOperationBroadcast(message)
          break
        case 'cursor_broadcast':
          this.handleCursorBroadcast(message)
          break
        case 'presence_broadcast':
          this.handlePresenceBroadcast(message)
          break
        case 'conflict_detected':
          this.handleConflictDetected(message)
          break
        case 'sync_state':
          this.handleSyncState(message)
          break
        case 'error':
          console.error('WebSocket error:', message.data)
          break
        default:
          console.warn('Unknown message type:', message.type)
      }
      
      // Track message processing latency
      const latency = Date.now() - messageStartTime
      this.messageLatencies.push(latency)
      if (this.messageLatencies.length > 100) {
        this.messageLatencies.shift()
      }
      
      // Performance warning
      if (latency > 50) {
        console.warn(`Message processing took ${latency}ms (>50ms target)`)
      }
      
    } catch (error) {
      console.error('Error handling WebSocket message:', error)
    }
  }

  private handleYjsBinaryMessage(data: ArrayBuffer): void {
    const uint8Array = new Uint8Array(data)
    const decoder = decoding.createDecoder(uint8Array)
    const encoder = encoding.createEncoder()
    const messageType = decoding.readVarUint(decoder)
    
    switch (messageType) {
      case syncProtocol.messageYjsSyncStep1:
        encoding.writeVarUint(encoder, syncProtocol.messageYjsSyncStep2)
        syncProtocol.writeSyncStep2(encoder, this.doc, decoding.readVarUint8Array(decoder))
        this.sendBinary(encoding.toUint8Array(encoder))
        break
      case syncProtocol.messageYjsSyncStep2:
        Y.applyUpdate(this.doc, decoding.readVarUint8Array(decoder))
        break
      case syncProtocol.messageYjsUpdate:
        Y.applyUpdate(this.doc, decoding.readVarUint8Array(decoder))
        break
      case awarenessProtocol.messageAwareness:
        awarenessProtocol.applyAwarenessUpdate(this.awareness, decoding.readVarUint8Array(decoder), this)
        break
    }
  }

  private handleOperationApplied(message: WebSocketMessage): void {
    // Operation was successfully processed by backend
    this.emit('operation-applied', [message.data])
  }

  private handleOperationBroadcast(message: WebSocketMessage): void {
    // Convert backend operation to Yjs update
    const operation = message.data
    
    // This will be converted to Yjs update format
    // For now, we emit for the editor to handle
    this.emit('remote-operation', [operation])
  }

  private handleCursorBroadcast(message: WebSocketMessage): void {
    // Update awareness with remote cursor position
    const { user_id, cursor_position, selection_range } = message.data
    
    const awarenessState = {
      cursor: cursor_position,
      selection: selection_range,
      user: this.awareness.getStates().get(this.awareness.clientID)?.user
    }
    
    // Apply remote awareness update
    this.awareness.setLocalStateField('cursor', cursor_position)
  }

  private handlePresenceBroadcast(message: WebSocketMessage): void {
    // Handle user presence updates
    this.emit('presence-update', [message.data])
  }

  private handleConflictDetected(message: WebSocketMessage): void {
    // Emit conflict for UI to handle
    this.emit('conflict-detected', [message.data])
  }

  private handleSyncState(message: WebSocketMessage): void {
    // Handle initial memory state sync
    const { state } = message.data
    
    // Apply initial state to Yjs document
    if (state) {
      // Convert memory state to Yjs operations
      const yText = this.doc.getText('content')
      yText.delete(0, yText.length)
      yText.insert(0, state.content || '')
      
      this.emit('sync-complete', [state])
    }
  }

  private handleDocumentUpdate(update: Uint8Array, origin: any): void {
    if (origin === this) return // Don't send updates from remote changes
    
    // Send Yjs update as WebSocket message to our CRDT bridge
    this.sendEditOperation(update)
  }

  private handleAwarenessUpdate({ added, updated, removed }: { added: number[], updated: number[], removed: number[] }): void {
    const changedClients = added.concat(updated, removed)
    const awareness = this.awareness
    
    // Send awareness updates for cursor tracking
    changedClients.forEach(clientId => {
      const state = awareness.getStates().get(clientId)
      if (state && clientId === awareness.clientID) {
        this.sendCursorUpdate(state)
      }
    })
  }

  private sendEditOperation(update: Uint8Array): void {
    if (!this.connected || !this.websocket) return
    
    // Convert Yjs update to our WebSocket-CRDT bridge format
    const message = {
      type: 'edit_operation',
      data: {
        operation_type: 'insert', // This should be derived from the update
        field_type: 'content',
        position: 0, // This should be derived from the update
        content: '', // This should be derived from the update
        length: 0, // This should be derived from the update
        metadata: {
          yjs_update: Array.from(update),
          source: 'yjs'
        }
      },
      timestamp: Date.now(),
      user_id: this.config.userId,
      room_id: this.roomId
    }
    
    this.websocket.send(JSON.stringify(message))
  }

  private sendCursorUpdate(awarenessState: any): void {
    if (!this.connected || !this.websocket) return
    
    const message = {
      type: 'cursor_update',
      data: {
        cursor_position: awarenessState.cursor,
        selection_range: awarenessState.selection,
        user_info: awarenessState.user
      },
      timestamp: Date.now(),
      user_id: this.config.userId,
      room_id: this.roomId
    }
    
    this.websocket.send(JSON.stringify(message))
  }

  private sendYjsSync(): void {
    if (!this.connected || !this.websocket) return
    
    const encoder = encoding.createEncoder()
    encoding.writeVarUint(encoder, syncProtocol.messageYjsSyncStep1)
    syncProtocol.writeSyncStep1(encoder, this.doc)
    this.sendBinary(encoding.toUint8Array(encoder))
  }

  private sendBinary(data: Uint8Array): void {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(data)
    }
  }

  private handleWebSocketClose(): void {
    console.log('WebSocket connection closed')
    this.connected = false
    this.emit('disconnected', [])
    this.stopHeartbeat()
    this.scheduleReconnect()
  }

  private handleWebSocketError(error: Event): void {
    console.error('WebSocket error:', error)
    this.emit('error', [error])
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeoutId) return
    
    const delay = Math.min(1000 * Math.pow(2, Math.floor(Math.random() * 5)), 30000)
    console.log(`Scheduling reconnect in ${delay}ms`)
    
    this.reconnectTimeoutId = window.setTimeout(() => {
      this.reconnectTimeoutId = null
      this.connect()
    }, delay)
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.connected && this.websocket) {
        this.websocket.send(JSON.stringify({
          type: 'ping',
          timestamp: Date.now()
        }))
        this.lastHeartbeat = Date.now()
      }
    }, 30000) // 30 second heartbeat
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  // Public API
  public getAwareness(): Awareness {
    return this.awareness
  }

  public isConnected(): boolean {
    return this.connected
  }

  public getPerformanceMetrics() {
    const avgLatency = this.messageLatencies.length > 0 
      ? this.messageLatencies.reduce((a, b) => a + b, 0) / this.messageLatencies.length 
      : 0
    
    return {
      connected: this.connected,
      averageLatency: avgLatency,
      maxLatency: Math.max(...this.messageLatencies, 0),
      messageCount: this.messageLatencies.length,
      targetCompliance: {
        latencyUnder50ms: avgLatency < 50,
        connectionHealthy: this.connected && (Date.now() - this.lastHeartbeat < 60000)
      }
    }
  }

  public destroy(): void {
    this.doc.off('update', this.handleDocumentUpdate.bind(this))
    this.awareness.off('update', this.handleAwarenessUpdate.bind(this))
    
    this.stopHeartbeat()
    
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId)
    }
    
    if (this.websocket) {
      this.websocket.close()
    }
    
    super.destroy()
  }
} 