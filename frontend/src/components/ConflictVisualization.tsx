/**
 * Conflict Visualization Component for GraphMemory-IDE
 * 
 * Provides real-time conflict detection, visualization, and resolution UI.
 * Optimized for performance with React 18 concurrent features and deferred updates.
 * 
 * Features:
 * - Real-time conflict detection and highlighting
 * - Visual diff comparison between conflicting versions
 * - Interactive conflict resolution with multiple options
 * - Performance optimized with useDeferredValue
 * - Integration with WebSocket-CRDT bridge
 * 
 * Performance: Uses useDeferredValue for non-urgent conflict UI updates
 */

import React, { useMemo, memo, useDeferredValue, useCallback, useState, useTransition } from 'react'
import { ConflictInfo } from '../hooks/useCollaboration'
import { 
  AlertTriangle, 
  Users, 
  Clock, 
  Check, 
  X, 
  RotateCcw, 
  GitMerge,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import clsx from 'clsx'

interface ConflictVisualizationProps {
  conflicts: ConflictInfo[]
  onResolveConflict: (conflictId: string, resolution: 'local' | 'remote' | 'custom', customValue?: any) => void
  className?: string
  maxVisible?: number
  autoCollapse?: boolean
  showPreview?: boolean
}

interface ConflictItemProps {
  conflict: ConflictInfo
  onResolve: (resolution: 'local' | 'remote' | 'custom', customValue?: any) => void
  showPreview: boolean
  isExpanded: boolean
  onToggleExpanded: () => void
}

interface DiffViewProps {
  localValue: any
  remoteValue: any
  field: string
  onCustomValue?: (value: any) => void
}

const DiffView: React.FC<DiffViewProps> = memo(({
  localValue,
  remoteValue,
  field,
  onCustomValue
}) => {
  const [customValue, setCustomValue] = useState<string>('')
  const [showCustomEditor, setShowCustomEditor] = useState(false)
  
  // Convert values to strings for display
  const localStr = typeof localValue === 'string' ? localValue : JSON.stringify(localValue, null, 2)
  const remoteStr = typeof remoteValue === 'string' ? remoteValue : JSON.stringify(remoteValue, null, 2)
  
  // Simple diff highlighting (for production, consider using a proper diff library)
  const getDiffLines = useCallback((text1: string, text2: string) => {
    const lines1 = text1.split('\n')
    const lines2 = text2.split('\n')
    const maxLines = Math.max(lines1.length, lines2.length)
    
    const result = []
    for (let i = 0; i < maxLines; i++) {
      const line1 = lines1[i] || ''
      const line2 = lines2[i] || ''
      const isDifferent = line1 !== line2
      
      result.push({
        lineNumber: i + 1,
        local: line1,
        remote: line2,
        isDifferent
      })
    }
    
    return result
  }, [])
  
  const diffLines = useMemo(() => getDiffLines(localStr, remoteStr), [localStr, remoteStr, getDiffLines])
  
  const handleCustomSubmit = useCallback(() => {
    if (customValue.trim()) {
      onCustomValue?.(customValue)
      setShowCustomEditor(false)
      setCustomValue('')
    }
  }, [customValue, onCustomValue])
  
  return (
    <div className="diff-view bg-gray-50 rounded-lg p-4 space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Local version */}
        <div className="local-version">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full" />
            <span className="text-sm font-medium text-gray-700">Your version</span>
          </div>
          <div className="bg-white border border-blue-200 rounded p-3 max-h-64 overflow-y-auto">
            <pre className="text-sm whitespace-pre-wrap text-gray-800">
              {diffLines.map(line => (
                <div 
                  key={line.lineNumber}
                  className={clsx(
                    'flex',
                    line.isDifferent && 'bg-blue-50'
                  )}
                >
                  <span className="text-gray-400 w-8 text-xs">{line.lineNumber}</span>
                  <span className="flex-1">{line.local}</span>
                </div>
              ))}
            </pre>
          </div>
        </div>
        
        {/* Remote version */}
        <div className="remote-version">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 bg-red-500 rounded-full" />
            <span className="text-sm font-medium text-gray-700">Remote version</span>
          </div>
          <div className="bg-white border border-red-200 rounded p-3 max-h-64 overflow-y-auto">
            <pre className="text-sm whitespace-pre-wrap text-gray-800">
              {diffLines.map(line => (
                <div 
                  key={line.lineNumber}
                  className={clsx(
                    'flex',
                    line.isDifferent && 'bg-red-50'
                  )}
                >
                  <span className="text-gray-400 w-8 text-xs">{line.lineNumber}</span>
                  <span className="flex-1">{line.remote}</span>
                </div>
              ))}
            </pre>
          </div>
        </div>
      </div>
      
      {/* Custom resolution option */}
      <div className="custom-resolution">
        <button
          onClick={() => setShowCustomEditor(!showCustomEditor)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800"
        >
          <GitMerge className="w-4 h-4" />
          Create custom resolution
          {showCustomEditor ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        
        {showCustomEditor && (
          <div className="mt-3 space-y-3">
            <textarea
              value={customValue}
              onChange={(e) => setCustomValue(e.target.value)}
              placeholder="Enter your custom resolution..."
              className="w-full p-3 border border-gray-300 rounded-lg text-sm resize-none"
              rows={6}
            />
            <div className="flex gap-2">
              <button
                onClick={handleCustomSubmit}
                disabled={!customValue.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-green-700"
              >
                Apply Custom Resolution
              </button>
              <button
                onClick={() => {
                  setShowCustomEditor(false)
                  setCustomValue('')
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
})

DiffView.displayName = 'DiffView'

const ConflictItem: React.FC<ConflictItemProps> = memo(({
  conflict,
  onResolve,
  showPreview,
  isExpanded,
  onToggleExpanded
}) => {
  const [isPending, startTransition] = useTransition()
  
  const handleResolve = useCallback((resolution: 'local' | 'remote' | 'custom', customValue?: any) => {
    startTransition(() => {
      onResolve(resolution, customValue)
    })
  }, [onResolve])
  
  const getConflictTypeIcon = () => {
    switch (conflict.type) {
      case 'text':
        return <AlertTriangle className="w-4 h-4 text-orange-500" />
      case 'structure':
        return <GitMerge className="w-4 h-4 text-blue-500" />
      case 'metadata':
        return <Users className="w-4 h-4 text-purple-500" />
      default:
        return <AlertTriangle className="w-4 h-4 text-gray-500" />
    }
  }
  
  const getConflictTypeLabel = () => {
    switch (conflict.type) {
      case 'text':
        return 'Text Conflict'
      case 'structure':
        return 'Structure Conflict'
      case 'metadata':
        return 'Metadata Conflict'
      default:
        return 'Unknown Conflict'
    }
  }
  
  const formatTimestamp = (date: Date) => {
    const now = Date.now()
    const diff = now - date.getTime()
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    return `${Math.floor(diff / 3600000)}h ago`
  }
  
  if (conflict.resolved) {
    return (
      <div className="conflict-item resolved bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <Check className="w-5 h-5 text-green-600" />
          <div className="flex-1">
            <div className="text-sm font-medium text-green-800">
              {getConflictTypeLabel()} resolved
            </div>
            <div className="text-xs text-green-600 mt-1">
              Field: {conflict.field} • {formatTimestamp(conflict.timestamp)}
            </div>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="conflict-item bg-white border border-orange-200 rounded-lg shadow-sm">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getConflictTypeIcon()}
            <div>
              <div className="text-sm font-medium text-gray-900">
                {getConflictTypeLabel()}
              </div>
              <div className="text-xs text-gray-500 mt-1 flex items-center gap-3">
                <span>Field: {conflict.field}</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatTimestamp(conflict.timestamp)}
                </span>
                <span className="flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  {conflict.users.length} user{conflict.users.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {showPreview && (
              <button
                onClick={onToggleExpanded}
                className="p-1 text-gray-400 hover:text-gray-600"
                title={isExpanded ? 'Collapse' : 'Expand'}
              >
                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Resolution buttons */}
      <div className="p-4 bg-gray-50 flex gap-2 flex-wrap">
        <button
          onClick={() => handleResolve('local')}
          disabled={isPending}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          <Check className="w-4 h-4" />
          Use Your Version
        </button>
        
        <button
          onClick={() => handleResolve('remote')}
          disabled={isPending}
          className="flex items-center gap-2 px-3 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
        >
          <RotateCcw className="w-4 h-4" />
          Use Remote Version
        </button>
        
        {isPending && (
          <div className="flex items-center gap-2 px-3 py-2 text-sm text-gray-500">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
            Resolving...
          </div>
        )}
      </div>
      
      {/* Diff view */}
      {isExpanded && showPreview && (
        <div className="p-4 border-t border-gray-100">
          <DiffView
            localValue={conflict.localValue}
            remoteValue={conflict.remoteValue}
            field={conflict.field}
            onCustomValue={(customValue) => handleResolve('custom', customValue)}
          />
        </div>
      )}
    </div>
  )
})

ConflictItem.displayName = 'ConflictItem'

const ConflictVisualization: React.FC<ConflictVisualizationProps> = memo(({
  conflicts,
  onResolveConflict,
  className = '',
  maxVisible = 5,
  autoCollapse = true,
  showPreview = true
}) => {
  // Deferred conflicts for performance (non-urgent updates)
  const deferredConflicts = useDeferredValue(conflicts)
  
  // Expanded states for conflicts
  const [expandedConflicts, setExpandedConflicts] = useState<Set<string>>(new Set())
  
  // Process conflicts for display
  const processedConflicts = useMemo(() => {
    const activeConflicts = deferredConflicts.filter(c => !c.resolved)
    const resolvedConflicts = deferredConflicts.filter(c => c.resolved)
    
    // Sort by timestamp (newest first)
    const sortedActive = activeConflicts.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
    const sortedResolved = resolvedConflicts.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
    
    return {
      active: sortedActive.slice(0, maxVisible),
      resolved: sortedResolved.slice(0, 3), // Show last 3 resolved
      hiddenActiveCount: Math.max(0, sortedActive.length - maxVisible)
    }
  }, [deferredConflicts, maxVisible])
  
  const toggleExpanded = useCallback((conflictId: string) => {
    setExpandedConflicts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(conflictId)) {
        newSet.delete(conflictId)
      } else {
        newSet.add(conflictId)
      }
      return newSet
    })
  }, [])
  
  const handleResolveConflict = useCallback((conflictId: string, resolution: 'local' | 'remote' | 'custom', customValue?: any) => {
    onResolveConflict(conflictId, resolution, customValue)
    
    // Auto-collapse resolved conflicts after a delay
    if (autoCollapse) {
      setTimeout(() => {
        setExpandedConflicts(prev => {
          const newSet = new Set(prev)
          newSet.delete(conflictId)
          return newSet
        })
      }, 2000)
    }
  }, [onResolveConflict, autoCollapse])
  
  if (processedConflicts.active.length === 0 && processedConflicts.resolved.length === 0) {
    return (
      <div className={clsx('conflict-visualization-empty', className)}>
        <div className="text-center py-8 text-gray-500">
          <Check className="w-8 h-8 mx-auto mb-2 text-green-500" />
          <div className="text-sm">No conflicts detected</div>
          <div className="text-xs mt-1">All changes are synchronized</div>
        </div>
      </div>
    )
  }
  
  return (
    <div className={clsx('conflict-visualization space-y-4', className)}>
      {/* Active conflicts */}
      {processedConflicts.active.length > 0 && (
        <div className="active-conflicts">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            <h3 className="text-sm font-medium text-gray-900">
              Active Conflicts ({processedConflicts.active.length})
            </h3>
            {processedConflicts.hiddenActiveCount > 0 && (
              <span className="text-xs text-gray-500">
                +{processedConflicts.hiddenActiveCount} more
              </span>
            )}
          </div>
          
          <div className="space-y-3">
            {processedConflicts.active.map(conflict => (
              <ConflictItem
                key={conflict.id}
                conflict={conflict}
                onResolve={(resolution, customValue) => handleResolveConflict(conflict.id, resolution, customValue)}
                showPreview={showPreview}
                isExpanded={expandedConflicts.has(conflict.id)}
                onToggleExpanded={() => toggleExpanded(conflict.id)}
              />
            ))}
          </div>
        </div>
      )}
      
      {/* Recently resolved conflicts */}
      {processedConflicts.resolved.length > 0 && (
        <div className="resolved-conflicts">
          <div className="flex items-center gap-2 mb-3">
            <Check className="w-5 h-5 text-green-500" />
            <h3 className="text-sm font-medium text-gray-700">
              Recently Resolved ({processedConflicts.resolved.length})
            </h3>
          </div>
          
          <div className="space-y-2">
            {processedConflicts.resolved.map(conflict => (
              <ConflictItem
                key={conflict.id}
                conflict={conflict}
                onResolve={() => {}} // No-op for resolved conflicts
                showPreview={false}
                isExpanded={false}
                onToggleExpanded={() => {}}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
})

ConflictVisualization.displayName = 'ConflictVisualization'

export default ConflictVisualization

// Additional utility components
export const ConflictIndicator: React.FC<{ conflictCount: number; className?: string }> = memo(({ 
  conflictCount, 
  className = '' 
}) => {
  if (conflictCount === 0) {
    return (
      <div className={clsx('flex items-center gap-1 text-green-600 text-xs', className)}>
        <Check className="w-3 h-3" />
        <span>Synced</span>
      </div>
    )
  }
  
  return (
    <div className={clsx('flex items-center gap-1 text-orange-600 text-xs', className)}>
      <AlertTriangle className="w-3 h-3" />
      <span>{conflictCount} conflict{conflictCount !== 1 ? 's' : ''}</span>
    </div>
  )
})

ConflictIndicator.displayName = 'ConflictIndicator' 