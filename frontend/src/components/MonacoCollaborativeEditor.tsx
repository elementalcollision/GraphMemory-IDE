/**
 * Monaco Collaborative Editor for GraphMemory-IDE
 * 
 * A collaborative text editor using Monaco Editor with Yjs integration.
 * Features live cursors, real-time synchronization, and conflict visualization.
 * 
 * Features:
 * - Real-time collaborative editing with Monaco Editor
 * - Live cursor tracking and user presence
 * - Performance optimized for <500ms update latency
 * - Integrated with our WebSocket-CRDT bridge
 * - Conflict visualization and resolution
 * 
 * Performance: React 18 concurrent features + Monaco optimizations
 */

import React, { useEffect, useRef, useCallback, useMemo, memo, useTransition } from 'react'
import Editor, { Monaco } from '@monaco-editor/react'
import { MonacoBinding } from 'y-monaco'
import * as Y from 'yjs'
import { Awareness } from 'y-protocols/awareness'
import { CustomWebSocketProvider } from '../providers/CustomWebSocketProvider'
import { useAwareness } from '../hooks/useCollaboration'
import type { editor } from 'monaco-editor'

interface CursorInfo {
  userId: string
  userName: string
  userColor: string
  position: { lineNumber: number; column: number }
  selection?: {
    startLineNumber: number
    startColumn: number
    endLineNumber: number
    endColumn: number
  }
}

interface MonacoCollaborativeEditorProps {
  provider: CustomWebSocketProvider | null
  yText: Y.Text | null
  language?: string
  theme?: string
  readOnly?: boolean
  className?: string
  placeholder?: string
  onCursorChange?: (cursor: { line: number; column: number }) => void
  onSelectionChange?: (selection: { start: { line: number; column: number }; end: { line: number; column: number } }) => void
  height?: string
  options?: editor.IStandaloneEditorConstructionOptions
}

const MonacoCollaborativeEditor: React.FC<MonacoCollaborativeEditorProps> = memo(({
  provider,
  yText,
  language = 'markdown',
  theme = 'vs-dark',
  readOnly = false,
  className = '',
  placeholder = 'Start collaborative editing...',
  onCursorChange,
  onSelectionChange,
  height = '400px',
  options = {}
}) => {
  // Refs
  const editorRef = useRef<editor.IStandaloneCodeEditor>()
  const monacoRef = useRef<Monaco>()
  const bindingRef = useRef<MonacoBinding>()
  const cursorsRef = useRef<Map<string, CursorInfo>>(new Map())
  const decorationsRef = useRef<Map<string, string[]>>(new Map())
  
  // Performance hooks
  const [isPending, startTransition] = useTransition()
  
  // Awareness for live cursors
  const { users, setLocalCursor, setLocalSelection } = useAwareness(provider)
  
  // Monaco editor options with collaboration optimizations
  const editorOptions = useMemo(() => ({
    fontSize: 14,
    lineHeight: 20,
    fontFamily: '"JetBrains Mono", "Fira Code", "Monaco", monospace',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    wordWrap: 'on' as const,
    lineNumbers: 'on' as const,
    folding: true,
    links: true,
    colorDecorators: true,
    contextmenu: true,
    mouseWheelZoom: true,
    readOnly,
    automaticLayout: true,
    tabSize: 2,
    insertSpaces: true,
    detectIndentation: false,
    renderWhitespace: 'selection' as const,
    renderControlCharacters: false,
    renderIndentGuides: true,
    cursorBlinking: 'blink' as const,
    cursorSmoothCaretAnimation: 'on' as const,
    smoothScrolling: true,
    multiCursorModifier: 'ctrlCmd' as const,
    accessibilitySupport: 'auto' as const,
    quickSuggestions: {
      other: true,
      comments: true,
      strings: true,
    },
    ...options
  }), [readOnly, options])
  
  // Handle editor mount
  const handleEditorDidMount = useCallback((editor: editor.IStandaloneCodeEditor, monaco: Monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco
    
    // Set up Monaco-Yjs binding when both editor and yText are ready
    if (yText && provider) {
      bindingRef.current = new MonacoBinding(
        yText,
        editor.getModel()!,
        new Set([editor]),
        provider.getAwareness()
      )
      
      console.log('Monaco-Yjs binding established')
    }
    
    // Set up cursor and selection tracking
    editor.onDidChangeCursorPosition((e) => {
      const position = e.position
      const cursor = { line: position.lineNumber, column: position.column }
      
      // Update local awareness
      setLocalCursor(cursor)
      
      // Notify parent component
      onCursorChange?.(cursor)
    })
    
    editor.onDidChangeCursorSelection((e) => {
      const selection = e.selection
      const selectionData = {
        start: { line: selection.startLineNumber, column: selection.startColumn },
        end: { line: selection.endLineNumber, column: selection.endColumn }
      }
      
      // Update local awareness
      setLocalSelection(selectionData)
      
      // Notify parent component
      onSelectionChange?.(selectionData)
    })
    
    // Performance: Debounce expensive operations
    let updateCursorsTimeout: NodeJS.Timeout
    const debouncedUpdateCursors = () => {
      clearTimeout(updateCursorsTimeout)
      updateCursorsTimeout = setTimeout(() => {
        startTransition(() => {
          updateRemoteCursors()
        })
      }, 50) // 50ms debounce for smooth performance
    }
    
    // Listen for awareness changes
    const updateRemoteCursors = () => {
      if (!editorRef.current || !monacoRef.current) return
      
      const newCursors = new Map<string, CursorInfo>()
      const newDecorations = new Map<string, string[]>()
      
      users.forEach((state, clientId) => {
        if (!state?.user || clientId === provider?.getAwareness().clientID) return
        
        const { user, cursor, selection } = state
        if (!cursor) return
        
        const userId = user.name || `User-${clientId}`
        const cursorInfo: CursorInfo = {
          userId,
          userName: user.name || userId,
          userColor: user.color || '#666666',
          position: { lineNumber: cursor.line, column: cursor.column },
          selection: selection ? {
            startLineNumber: selection.start.line,
            startColumn: selection.start.column,
            endLineNumber: selection.end.line,
            endColumn: selection.end.column
          } : undefined
        }
        
        newCursors.set(userId, cursorInfo)
        
        // Create cursor decorations
        const decorations: editor.IModelDeltaDecoration[] = []
        
        // Cursor decoration
        decorations.push({
          range: new monacoRef.current!.Range(
            cursor.line,
            cursor.column,
            cursor.line,
            cursor.column
          ),
          options: {
            className: `yjs-cursor-${userId.replace(/[^a-zA-Z0-9]/g, '-')}`,
            beforeContentClassName: `yjs-cursor-line-${userId.replace(/[^a-zA-Z0-9]/g, '-')}`,
            stickiness: monacoRef.current!.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges
          }
        })
        
        // Selection decoration
        if (selection && (
          selection.start.line !== selection.end.line ||
          selection.start.column !== selection.end.column
        )) {
          decorations.push({
            range: new monacoRef.current!.Range(
              selection.start.line,
              selection.start.column,
              selection.end.line,
              selection.end.column
            ),
            options: {
              className: `yjs-selection-${userId.replace(/[^a-zA-Z0-9]/g, '-')}`,
              stickiness: monacoRef.current!.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges
            }
          })
        }
        
        // Apply decorations
        const decorationIds = editorRef.current!.deltaDecorations(
          decorationsRef.current.get(userId) || [],
          decorations
        )
        newDecorations.set(userId, decorationIds)
      })
      
      cursorsRef.current = newCursors
      decorationsRef.current = newDecorations
    }
    
    // Subscribe to awareness changes
    if (provider) {
      const awareness = provider.getAwareness()
      awareness.on('change', debouncedUpdateCursors)
    }
    
    // Initial cursor update
    debouncedUpdateCursors()
    
  }, [yText, provider, setLocalCursor, setLocalSelection, onCursorChange, onSelectionChange, users])
  
  // Handle editor unmount
  const handleEditorWillUnmount = useCallback(() => {
    // Clean up binding
    if (bindingRef.current) {
      bindingRef.current.destroy()
      bindingRef.current = undefined
    }
    
    // Clear decorations
    decorationsRef.current.clear()
    cursorsRef.current.clear()
    
    editorRef.current = undefined
    monacoRef.current = undefined
  }, [])
  
  // Effect to inject custom CSS for cursors
  useEffect(() => {
    const style = document.createElement('style')
    style.textContent = `
      /* Base cursor styles */
      .yjs-cursor-line::before {
        content: '';
        position: absolute;
        top: 0;
        width: 2px;
        height: 100%;
        background-color: var(--cursor-color, #666666);
        z-index: 10;
      }
      
      /* Selection styles */
      .yjs-selection {
        background-color: var(--selection-color, rgba(102, 102, 102, 0.2));
      }
      
      /* User-specific cursor colors */
      ${Array.from(cursorsRef.current.values()).map(cursor => `
        .yjs-cursor-${cursor.userId.replace(/[^a-zA-Z0-9]/g, '-')}::before {
          --cursor-color: ${cursor.userColor};
        }
        .yjs-selection-${cursor.userId.replace(/[^a-zA-Z0-9]/g, '-')} {
          --selection-color: ${cursor.userColor}33;
        }
      `).join('\n')}
    `
    
    document.head.appendChild(style)
    
    return () => {
      document.head.removeChild(style)
    }
  }, [users])
  
  // Loading state
  if (!yText || !provider) {
    return (
      <div 
        className={`monaco-editor-loading ${className}`}
        style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <div className="loading-spinner">
          <div>Loading collaborative editor...</div>
        </div>
      </div>
    )
  }
  
  return (
    <div className={`monaco-collaborative-editor ${className}`} style={{ height }}>
      <Editor
        height={height}
        language={language}
        theme={theme}
        options={editorOptions}
        onMount={handleEditorDidMount}
        beforeUnmount={handleEditorWillUnmount}
        loading={
          <div className="monaco-loading">
            <div>Loading editor...</div>
          </div>
        }
      />
      
      {/* Live cursor indicators */}
      <div className="live-cursors-overlay">
        {Array.from(cursorsRef.current.values()).map(cursor => (
          <div
            key={cursor.userId}
            className="cursor-indicator"
            style={{
              position: 'absolute',
              backgroundColor: cursor.userColor,
              color: 'white',
              padding: '2px 6px',
              borderRadius: '3px',
              fontSize: '12px',
              fontFamily: 'system-ui, sans-serif',
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              zIndex: 1000,
              transform: 'translateY(-100%)',
              // Position will be calculated dynamically
            }}
          >
            {cursor.userName}
          </div>
        ))}
      </div>
      
      {/* Performance indicator */}
      {isPending && (
        <div className="performance-indicator">
          <div style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: 'white',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '12px',
            zIndex: 1000
          }}>
            Syncing...
          </div>
        </div>
      )}
    </div>
  )
})

MonacoCollaborativeEditor.displayName = 'MonacoCollaborativeEditor'

export default MonacoCollaborativeEditor 