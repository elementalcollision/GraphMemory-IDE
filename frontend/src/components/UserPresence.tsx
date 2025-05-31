/**
 * User Presence Component for GraphMemory-IDE
 * 
 * Displays live user avatars, online status, and collaborative activity.
 * Optimized for real-time updates with React 18 concurrent features.
 * 
 * Features:
 * - Live user avatars with status indicators
 * - Real-time activity tracking
 * - User cursor position indicators
 * - Performance optimized with useDeferredValue
 * - Responsive design for multiple screen sizes
 * 
 * Integration: CustomWebSocketProvider + Awareness API
 */

import React, { useMemo, memo, useDeferredValue, useCallback } from 'react'
import { UserPresence as UserPresenceType } from '../hooks/useCollaboration'
import { Users, Circle, Eye, EyeOff, Activity, Clock } from 'lucide-react'
import clsx from 'clsx'

interface UserPresenceProps {
  users: UserPresenceType[]
  currentUserId: string
  maxVisible?: number
  showActivity?: boolean
  showCursors?: boolean
  className?: string
  size?: 'sm' | 'md' | 'lg'
  layout?: 'horizontal' | 'vertical' | 'grid'
  onClick?: (user: UserPresenceType) => void
}

interface UserAvatarProps {
  user: UserPresenceType
  isCurrentUser: boolean
  size: 'sm' | 'md' | 'lg'
  showActivity: boolean
  showCursors: boolean
  onClick?: (user: UserPresenceType) => void
}

const UserAvatar: React.FC<UserAvatarProps> = memo(({
  user,
  isCurrentUser,
  size,
  showActivity,
  showCursors,
  onClick
}) => {
  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base'
  }
  
  const statusColors = {
    online: 'bg-green-500',
    away: 'bg-yellow-500',
    offline: 'bg-gray-400'
  }
  
  const getInitials = useCallback((name: string) => {
    return name
      .split(' ')
      .map(part => part.charAt(0))
      .join('')
      .substring(0, 2)
      .toUpperCase()
  }, [])
  
  const getActivityText = useCallback((user: UserPresenceType) => {
    const timeSinceLastSeen = Date.now() - user.lastSeen.getTime()
    
    if (user.status === 'online') {
      if (user.cursor) {
        return `Line ${user.cursor.line}, Col ${user.cursor.column}`
      }
      return 'Active now'
    }
    
    if (timeSinceLastSeen < 60000) { // Less than 1 minute
      return 'Just now'
    } else if (timeSinceLastSeen < 3600000) { // Less than 1 hour
      const minutes = Math.floor(timeSinceLastSeen / 60000)
      return `${minutes}m ago`
    } else {
      const hours = Math.floor(timeSinceLastSeen / 3600000)
      return `${hours}h ago`
    }
  }, [])
  
  const handleClick = useCallback(() => {
    onClick?.(user)
  }, [user, onClick])
  
  return (
    <div 
      className={clsx(
        'user-avatar relative group',
        onClick && 'cursor-pointer hover:scale-105 transition-transform',
        isCurrentUser && 'ring-2 ring-blue-500'
      )}
      onClick={handleClick}
      title={`${user.userInfo.name} (${user.status})`}
    >
      {/* Avatar */}
      <div 
        className={clsx(
          'rounded-full flex items-center justify-center font-medium text-white relative overflow-hidden',
          sizeClasses[size]
        )}
        style={{ backgroundColor: user.userInfo.color }}
      >
        {user.userInfo.avatar ? (
          <img 
            src={user.userInfo.avatar} 
            alt={user.userInfo.name}
            className="w-full h-full object-cover"
          />
        ) : (
          getInitials(user.userInfo.name)
        )}
        
        {/* Status indicator */}
        <div 
          className={clsx(
            'absolute -bottom-0.5 -right-0.5 rounded-full border-2 border-white',
            statusColors[user.status],
            size === 'sm' ? 'w-3 h-3' : size === 'md' ? 'w-3.5 h-3.5' : 'w-4 h-4'
          )}
        />
        
        {/* Cursor indicator for active users */}
        {showCursors && user.status === 'online' && user.cursor && (
          <div className="absolute -top-1 -right-1">
            <Circle 
              className={clsx(
                'text-white fill-current animate-pulse',
                size === 'sm' ? 'w-2 h-2' : 'w-3 h-3'
              )}
            />
          </div>
        )}
      </div>
      
      {/* Hover tooltip */}
      <div className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
        <div className="font-medium">{user.userInfo.name}</div>
        <div className="text-gray-300">{user.userInfo.email}</div>
        {showActivity && (
          <div className="text-gray-400 mt-1 flex items-center gap-1">
            {user.status === 'online' ? (
              <Activity className="w-3 h-3" />
            ) : (
              <Clock className="w-3 h-3" />
            )}
            {getActivityText(user)}
          </div>
        )}
        
        {/* Tooltip arrow */}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
      </div>
    </div>
  )
})

UserAvatar.displayName = 'UserAvatar'

const UserPresence: React.FC<UserPresenceProps> = memo(({
  users,
  currentUserId,
  maxVisible = 8,
  showActivity = true,
  showCursors = true,
  className = '',
  size = 'md',
  layout = 'horizontal',
  onClick
}) => {
  // Deferred users for performance optimization
  const deferredUsers = useDeferredValue(users)
  
  // Sort and filter users
  const processedUsers = useMemo(() => {
    const sortedUsers = [...deferredUsers].sort((a, b) => {
      // Current user first
      if (a.userId === currentUserId) return -1
      if (b.userId === currentUserId) return 1
      
      // Online users next
      if (a.status === 'online' && b.status !== 'online') return -1
      if (b.status === 'online' && a.status !== 'online') return 1
      
      // Then by last seen (most recent first)
      return b.lastSeen.getTime() - a.lastSeen.getTime()
    })
    
    const visibleUsers = sortedUsers.slice(0, maxVisible)
    const hiddenCount = Math.max(0, sortedUsers.length - maxVisible)
    
    return { visibleUsers, hiddenCount, totalUsers: sortedUsers.length }
  }, [deferredUsers, currentUserId, maxVisible])
  
  const layoutClasses = {
    horizontal: 'flex flex-row items-center gap-2',
    vertical: 'flex flex-col items-center gap-2',
    grid: 'grid grid-cols-4 gap-2'
  }
  
  const onlineCount = useMemo(() => 
    deferredUsers.filter(user => user.status === 'online').length,
    [deferredUsers]
  )
  
  if (processedUsers.totalUsers === 0) {
    return (
      <div className={clsx('user-presence-empty text-gray-500 text-sm', className)}>
        <Users className="w-4 h-4 inline mr-2" />
        No active collaborators
      </div>
    )
  }
  
  return (
    <div className={clsx('user-presence', layoutClasses[layout], className)}>
      {/* User avatars */}
      {processedUsers.visibleUsers.map(user => (
        <UserAvatar
          key={user.userId}
          user={user}
          isCurrentUser={user.userId === currentUserId}
          size={size}
          showActivity={showActivity}
          showCursors={showCursors}
          onClick={onClick}
        />
      ))}
      
      {/* Hidden users indicator */}
      {processedUsers.hiddenCount > 0 && (
        <div 
          className={clsx(
            'rounded-full bg-gray-200 flex items-center justify-center font-medium text-gray-600 border-2 border-gray-300',
            sizeClasses[size]
          )}
          title={`${processedUsers.hiddenCount} more user${processedUsers.hiddenCount === 1 ? '' : 's'}`}
        >
          +{processedUsers.hiddenCount}
        </div>
      )}
      
      {/* Online status summary */}
      {layout === 'horizontal' && (
        <div className="user-presence-summary flex items-center gap-2 ml-3 text-sm text-gray-600">
          <div className="flex items-center gap-1">
            <Circle className="w-2 h-2 text-green-500 fill-current" />
            <span>{onlineCount} online</span>
          </div>
          
          {processedUsers.totalUsers > onlineCount && (
            <div className="flex items-center gap-1">
              <Circle className="w-2 h-2 text-gray-400 fill-current" />
              <span>{processedUsers.totalUsers - onlineCount} away</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
})

UserPresence.displayName = 'UserPresence'

// Additional components for specific use cases
export const CompactUserPresence: React.FC<Omit<UserPresenceProps, 'layout' | 'size'>> = memo((props) => (
  <UserPresence {...props} layout="horizontal" size="sm" maxVisible={5} />
))

export const DetailedUserPresence: React.FC<Omit<UserPresenceProps, 'layout' | 'size'>> = memo((props) => (
  <UserPresence {...props} layout="vertical" size="lg" showActivity showCursors />
))

export const GridUserPresence: React.FC<Omit<UserPresenceProps, 'layout'>> = memo((props) => (
  <UserPresence {...props} layout="grid" />
))

CompactUserPresence.displayName = 'CompactUserPresence'
DetailedUserPresence.displayName = 'DetailedUserPresence'  
GridUserPresence.displayName = 'GridUserPresence'

export default UserPresence

// Additional hook for user presence functionality
export const useUserInteraction = (users: UserPresenceType[], currentUserId: string) => {
  const focusOnUser = useCallback((user: UserPresenceType) => {
    // Emit event to focus on user's cursor position
    if (user.cursor) {
      const event = new CustomEvent('focus-user-cursor', {
        detail: { userId: user.userId, cursor: user.cursor }
      })
      window.dispatchEvent(event)
    }
  }, [])
  
  const getUserActivity = useCallback((userId: string) => {
    const user = users.find(u => u.userId === userId)
    if (!user) return null
    
    return {
      isOnline: user.status === 'online',
      lastSeen: user.lastSeen,
      currentPosition: user.cursor,
      isCurrentUser: userId === currentUserId
    }
  }, [users, currentUserId])
  
  return {
    focusOnUser,
    getUserActivity,
    onlineUsers: users.filter(u => u.status === 'online'),
    totalUsers: users.length
  }
}

// CSS classes helper (for external styling)
export const presenceStyles = {
  container: 'user-presence',
  avatar: 'user-avatar',
  status: 'user-status',
  tooltip: 'user-tooltip',
  summary: 'user-presence-summary'
}

const sizeClasses = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base'
} 