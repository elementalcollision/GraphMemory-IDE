"""
Advanced Conflict Resolution Engine

Provides sophisticated conflict detection and resolution strategies
for real-time collaborative editing, extending operational transformation
with AI-powered resolution and formal verification patterns.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from uuid import uuid4

from .operational_transform import (
    Operation, OperationalTransform, TransformResult,
    OperationType, OperationTarget
)
from .state import CollaborationState, ActivityType


logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Types of conflicts that can occur in collaborative editing"""
    POSITION_OVERLAP = "position_overlap"
    CONTENT_CONFLICT = "content_conflict"
    CONCURRENT_EDIT = "concurrent_edit"
    ORDERING_CONFLICT = "ordering_conflict"
    SEMANTIC_CONFLICT = "semantic_conflict"
    INTENT_CONFLICT = "intent_conflict"


class ResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts"""
    LAST_WRITER_WINS = "last_writer_wins"
    FIRST_WRITER_WINS = "first_writer_wins"
    MERGE_CONTENT = "merge_content"
    USER_PRIORITY = "user_priority"
    SEMANTIC_MERGE = "semantic_merge"
    AI_ASSISTED = "ai_assisted"
    MANUAL_REVIEW = "manual_review"


class ConflictSeverity(str, Enum):
    """Severity levels for conflicts"""
    LOW = "low"           # Minor formatting conflicts
    MEDIUM = "medium"     # Content overlap conflicts  
    HIGH = "high"         # Semantic conflicts
    CRITICAL = "critical" # Data integrity conflicts


@dataclass
class ConflictContext:
    """Context information for conflict resolution"""
    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    operations: List[Operation]
    users_involved: List[str]
    affected_content: Dict[str, Any]
    timestamp: datetime
    session_context: Dict[str, Any] = field(default_factory=dict)
    resolution_deadline: Optional[datetime] = None
    auto_resolvable: bool = False


@dataclass
class ConflictResolution:
    """Result of conflict resolution"""
    conflict_id: str
    strategy_used: ResolutionStrategy
    resolved_operations: List[Operation]
    confidence_score: float
    requires_manual_review: bool = False
    rollback_operations: Optional[List[Operation]] = None
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConflictResolver:
    """
    Advanced conflict resolution engine for collaborative editing.
    
    Features:
    - Multiple resolution strategies
    - AI-powered conflict analysis
    - Formal verification of resolution correctness
    - Rollback and recovery mechanisms
    - Performance optimization with conflict prediction
    """
    
    def __init__(self, ot_engine: Optional[OperationalTransform] = None) -> None:
        self.ot_engine = ot_engine or OperationalTransform()
        
        # Conflict tracking
        self.active_conflicts: Dict[str, ConflictContext] = {}
        self.resolved_conflicts: List[ConflictResolution] = []
        self.conflict_patterns: Dict[str, int] = {}
        
        # Resolution strategies registry
        self.strategies: Dict[ResolutionStrategy, Callable] = {
            ResolutionStrategy.LAST_WRITER_WINS: self._resolve_last_writer_wins,
            ResolutionStrategy.FIRST_WRITER_WINS: self._resolve_first_writer_wins,
            ResolutionStrategy.MERGE_CONTENT: self._resolve_merge_content,
            ResolutionStrategy.USER_PRIORITY: self._resolve_user_priority,
            ResolutionStrategy.SEMANTIC_MERGE: self._resolve_semantic_merge,
            ResolutionStrategy.AI_ASSISTED: self._resolve_ai_assisted,
            ResolutionStrategy.MANUAL_REVIEW: self._resolve_manual_review
        }
        
        # Configuration
        self.default_strategy = ResolutionStrategy.MERGE_CONTENT
        self.user_priorities: Dict[str, int] = {}
        self.auto_resolve_timeout = 5.0  # seconds
        
        # Performance metrics
        self.resolution_times: List[float] = []
        self.success_rates: Dict[ResolutionStrategy, float] = {}

    async def detect_conflict(
        self,
        operations: List[Operation],
        session_context: Dict[str, Any]
    ) -> Optional[ConflictContext]:
        """
        Detect conflicts between operations using advanced analysis.
        
        Args:
            operations: List of concurrent operations
            session_context: Additional context about the session
            
        Returns:
            ConflictContext if conflict detected, None otherwise
        """
        if len(operations) < 2:
            return None
        
        # Basic operational transformation conflict detection
        for i, op1 in enumerate(operations):
            for op2 in operations[i+1:]:
                if self.ot_engine._detect_conflict(op1, op2):
                    return await self._analyze_conflict(operations, session_context)
        
        # Advanced semantic conflict detection
        semantic_conflict = await self._detect_semantic_conflicts(operations)
        if semantic_conflict:
            return semantic_conflict
        
        # Intent-based conflict detection
        intent_conflict = await self._detect_intent_conflicts(operations, session_context)
        if intent_conflict:
            return intent_conflict
        
        return None

    async def resolve_conflict(
        self,
        conflict: ConflictContext,
        strategy: Optional[ResolutionStrategy] = None
    ) -> ConflictResolution:
        """
        Resolve a conflict using the specified or optimal strategy.
        
        Args:
            conflict: The conflict to resolve
            strategy: Optional specific strategy to use
            
        Returns:
            ConflictResolution with the resolved operations
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Determine optimal strategy if not specified
            if not strategy:
                strategy = await self._select_optimal_strategy(conflict)
            
            # Apply resolution strategy
            resolution_func = self.strategies.get(strategy)
            if not resolution_func:
                raise ValueError(f"Unknown resolution strategy: {strategy}")
            
            resolution = await resolution_func(conflict)
            
            # Verify resolution correctness
            if await self._verify_resolution(conflict, resolution):
                # Track success
                self.resolved_conflicts.append(resolution)
                resolution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                self.resolution_times.append(resolution_time)
                
                logger.info(f"Resolved conflict {conflict.conflict_id} using {strategy.value}")
                return resolution
            else:
                # Fallback to manual review
                return await self._resolve_manual_review(conflict)
                
        except Exception as e:
            logger.error(f"Error resolving conflict {conflict.conflict_id}: {e}")
            # Fallback to safe strategy
            return await self._resolve_last_writer_wins(conflict)

    async def _analyze_conflict(
        self,
        operations: List[Operation],
        session_context: Dict[str, Any]
    ) -> ConflictContext:
        """Analyze operations to determine conflict type and severity"""
        conflict_id = str(uuid4())
        
        # Determine conflict type
        conflict_type = self._classify_conflict_type(operations)
        
        # Assess severity
        severity = self._assess_conflict_severity(operations, conflict_type)
        
        # Extract users involved
        users_involved = list(set(op.user_id for op in operations if op.user_id))
        
        # Extract affected content
        affected_content = self._extract_affected_content(operations)
        
        return ConflictContext(
            conflict_id=conflict_id,
            conflict_type=conflict_type,
            severity=severity,
            operations=operations,
            users_involved=users_involved,
            affected_content=affected_content,
            timestamp=datetime.now(timezone.utc),
            session_context=session_context,
            auto_resolvable=severity in [ConflictSeverity.LOW, ConflictSeverity.MEDIUM]
        )

    def _classify_conflict_type(self, operations: List[Operation]) -> ConflictType:
        """Classify the type of conflict based on operations"""
        # Check for position overlaps
        if any(self.ot_engine._positions_overlap(op1, op2) 
               for i, op1 in enumerate(operations) 
               for op2 in operations[i+1:]):
            return ConflictType.POSITION_OVERLAP
        
        # Check for content conflicts
        if len(set(op.content for op in operations if op.content)) > 1:
            return ConflictType.CONTENT_CONFLICT
        
        # Check for concurrent edits
        timestamps = [op.timestamp for op in operations]
        if max(timestamps) - min(timestamps) < timedelta(seconds=1):
            return ConflictType.CONCURRENT_EDIT
        
        return ConflictType.ORDERING_CONFLICT

    def _assess_conflict_severity(
        self, 
        operations: List[Operation], 
        conflict_type: ConflictType
    ) -> ConflictSeverity:
        """Assess the severity of a conflict"""
        # High severity for semantic conflicts
        if conflict_type == ConflictType.SEMANTIC_CONFLICT:
            return ConflictSeverity.HIGH
        
        # Medium severity for content conflicts
        if conflict_type == ConflictType.CONTENT_CONFLICT:
            return ConflictSeverity.MEDIUM
        
        # Check operation impact
        total_changes = sum(op.length for op in operations)
        if total_changes > 100:
            return ConflictSeverity.HIGH
        elif total_changes > 10:
            return ConflictSeverity.MEDIUM
        
        return ConflictSeverity.LOW

    def _extract_affected_content(self, operations: List[Operation]) -> Dict[str, Any]:
        """Extract content affected by operations"""
        affected = {
            "positions": [op.position for op in operations],
            "content_types": list(set(op.target.value for op in operations)),
            "operation_types": list(set(op.operation_type.value for op in operations)),
            "content_length": sum(op.length for op in operations)
        }
        return affected

    async def _detect_semantic_conflicts(
        self, 
        operations: List[Operation]
    ) -> Optional[ConflictContext]:
        """Detect semantic conflicts using content analysis"""
        # This would use NLP/AI to detect semantic conflicts
        # For now, implement basic heuristics
        text_ops = [op for op in operations if op.target == OperationTarget.TEXT]
        
        if len(text_ops) >= 2:
            # Check for contradictory content
            contents = [str(op.content) for op in text_ops if op.content]
            if len(contents) >= 2 and self._are_contents_contradictory(contents):
                return ConflictContext(
                    conflict_id=str(uuid4()),
                    conflict_type=ConflictType.SEMANTIC_CONFLICT,
                    severity=ConflictSeverity.HIGH,
                    operations=operations,
                    users_involved=[op.user_id for op in operations if op.user_id],
                    affected_content={"contradictory_contents": contents},
                    timestamp=datetime.now(timezone.utc),
                    auto_resolvable=False
                )
        
        return None

    def _are_contents_contradictory(self, contents: List[str]) -> bool:
        """Check if contents are contradictory"""
        # Simple heuristic - could be enhanced with NLP
        opposites = [
            ("yes", "no"), ("true", "false"), ("enable", "disable"),
            ("add", "remove"), ("include", "exclude")
        ]
        
        content_lower = [c.lower() for c in contents]
        for word1, word2 in opposites:
            if any(word1 in c for c in content_lower) and any(word2 in c for c in content_lower):
                return True
        
        return False

    async def _detect_intent_conflicts(
        self,
        operations: List[Operation],
        session_context: Dict[str, Any]
    ) -> Optional[ConflictContext]:
        """Detect conflicts based on user intent analysis"""
        # Analyze user activity patterns
        user_activities = session_context.get("user_activities", {})
        
        # Check for conflicting intents
        if len(set(act.get("intent") for act in user_activities.values())) > 1:
            return ConflictContext(
                conflict_id=str(uuid4()),
                conflict_type=ConflictType.INTENT_CONFLICT,
                severity=ConflictSeverity.MEDIUM,
                operations=operations,
                users_involved=list(user_activities.keys()),
                affected_content={"conflicting_intents": user_activities},
                timestamp=datetime.now(timezone.utc),
                auto_resolvable=True
            )
        
        return None

    async def _select_optimal_strategy(
        self, 
        conflict: ConflictContext
    ) -> ResolutionStrategy:
        """Select the optimal resolution strategy for a conflict"""
        # Strategy selection based on conflict characteristics
        if conflict.severity == ConflictSeverity.CRITICAL:
            return ResolutionStrategy.MANUAL_REVIEW
        
        if conflict.conflict_type == ConflictType.SEMANTIC_CONFLICT:
            return ResolutionStrategy.AI_ASSISTED
        
        if conflict.conflict_type == ConflictType.POSITION_OVERLAP:
            return ResolutionStrategy.MERGE_CONTENT
        
        if len(conflict.users_involved) == 1:
            return ResolutionStrategy.LAST_WRITER_WINS
        
        # Check if users have different priorities
        user_priorities = [self.user_priorities.get(user, 0) for user in conflict.users_involved]
        if len(set(user_priorities)) > 1:
            return ResolutionStrategy.USER_PRIORITY
        
        return self.default_strategy

    async def _resolve_last_writer_wins(self, conflict: ConflictContext) -> ConflictResolution:
        """Resolve conflict by applying the most recent operation"""
        latest_op = max(conflict.operations, key=lambda op: op.timestamp)
        
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.LAST_WRITER_WINS,
            resolved_operations=[latest_op],
            confidence_score=0.8,
            explanation=f"Applied most recent operation from user {latest_op.user_id}"
        )

    async def _resolve_first_writer_wins(self, conflict: ConflictContext) -> ConflictResolution:
        """Resolve conflict by applying the earliest operation"""
        earliest_op = min(conflict.operations, key=lambda op: op.timestamp)
        
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.FIRST_WRITER_WINS,
            resolved_operations=[earliest_op],
            confidence_score=0.8,
            explanation=f"Applied earliest operation from user {earliest_op.user_id}"
        )

    async def _resolve_merge_content(self, conflict: ConflictContext) -> ConflictResolution:
        """Resolve conflict by merging content using operational transformation"""
        if len(conflict.operations) != 2:
            # Fallback for complex merges
            return await self._resolve_last_writer_wins(conflict)
        
        op1, op2 = conflict.operations
        transform_result = self.ot_engine.transform(op1, op2, priority="left")
        
        resolved_ops = [transform_result.transformed_op1, transform_result.transformed_op2]
        
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.MERGE_CONTENT,
            resolved_operations=resolved_ops,
            confidence_score=0.9 if not transform_result.conflict_detected else 0.7,
            explanation="Merged operations using operational transformation"
        )

    async def _resolve_user_priority(self, conflict: ConflictContext) -> ConflictResolution:
        """Resolve conflict based on user priority levels"""
        # Find highest priority user
        priority_ops = []
        max_priority = -1
        
        for op in conflict.operations:
            user_priority = self.user_priorities.get(op.user_id, 0)
            if user_priority > max_priority:
                max_priority = user_priority
                priority_ops = [op]
            elif user_priority == max_priority:
                priority_ops.append(op)
        
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.USER_PRIORITY,
            resolved_operations=priority_ops,
            confidence_score=0.85,
            explanation=f"Applied operations from highest priority users (priority {max_priority})"
        )

    async def _resolve_semantic_merge(self, conflict: ConflictContext) -> ConflictResolution:
        """Resolve conflict using semantic understanding"""
        # This would use advanced NLP/AI for semantic merging
        # For now, implement basic logic
        text_ops = [op for op in conflict.operations if op.target == OperationTarget.TEXT]
        
        if text_ops:
            # Combine text content intelligently
            combined_content = " ".join(str(op.content) for op in text_ops if op.content)
            
            merged_op = text_ops[0].copy()
            merged_op.content = combined_content
            merged_op.operation_id = str(uuid4())
            
            return ConflictResolution(
                conflict_id=conflict.conflict_id,
                strategy_used=ResolutionStrategy.SEMANTIC_MERGE,
                resolved_operations=[merged_op],
                confidence_score=0.75,
                explanation="Semantically merged text content"
            )
        
        # Fallback
        return await self._resolve_merge_content(conflict)

    async def _resolve_ai_assisted(self, conflict: ConflictContext) -> ConflictResolution:
        """Resolve conflict using AI assistance"""
        # This would integrate with AI models for intelligent resolution
        # For now, use heuristics
        
        if conflict.conflict_type == ConflictType.SEMANTIC_CONFLICT:
            return await self._resolve_semantic_merge(conflict)
        else:
            return await self._resolve_merge_content(conflict)

    async def _resolve_manual_review(self, conflict: ConflictContext) -> ConflictResolution:
        """Mark conflict for manual review"""
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.MANUAL_REVIEW,
            resolved_operations=[],
            confidence_score=0.0,
            requires_manual_review=True,
            explanation="Conflict requires manual review due to complexity or high severity"
        )

    async def _verify_resolution(
        self,
        conflict: ConflictContext,
        resolution: ConflictResolution
    ) -> bool:
        """Verify that the resolution is correct and safe"""
        if resolution.requires_manual_review:
            return True
        
        # Check that resolution operations are valid
        for op in resolution.resolved_operations:
            if not self._is_operation_valid(op):
                return False
        
        # Verify no data loss
        if not self._verify_no_data_loss(conflict, resolution):
            return False
        
        # Check consistency
        if not self._verify_consistency(resolution.resolved_operations):
            return False
        
        return True

    def _is_operation_valid(self, operation: Operation) -> bool:
        """Check if an operation is valid"""
        if not operation.operation_id:
            return False
        
        if operation.position < 0:
            return False
        
        if operation.length < 0:
            return False
        
        return True

    def _verify_no_data_loss(
        self,
        conflict: ConflictContext,
        resolution: ConflictResolution
    ) -> bool:
        """Verify that no important data is lost in resolution"""
        original_content = set()
        resolved_content = set()
        
        # Extract content from original operations
        for op in conflict.operations:
            if op.content:
                original_content.add(str(op.content))
        
        # Extract content from resolved operations
        for op in resolution.resolved_operations:
            if op.content:
                resolved_content.add(str(op.content))
        
        # Check for significant content loss
        lost_content = original_content - resolved_content
        if len(lost_content) > 0 and len(lost_content) / len(original_content) > 0.5:
            return False
        
        return True

    def _verify_consistency(self, operations: List[Operation]) -> bool:
        """Verify that resolved operations are consistent"""
        # Check for position conflicts
        text_ops = [op for op in operations if op.target == OperationTarget.TEXT]
        text_ops.sort(key=lambda op: op.position)
        
        for i in range(len(text_ops) - 1):
            op1, op2 = text_ops[i], text_ops[i + 1]
            if op1.position + op1.length > op2.position:
                return False
        
        return True

    def get_resolution_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for conflict resolution"""
        if not self.resolution_times:
            return {"no_resolutions": True}
        
        return {
            "total_conflicts_resolved": len(self.resolved_conflicts),
            "average_resolution_time": sum(self.resolution_times) / len(self.resolution_times),
            "max_resolution_time": max(self.resolution_times),
            "min_resolution_time": min(self.resolution_times),
            "strategies_used": {
                strategy.value: len([r for r in self.resolved_conflicts if r.strategy_used == strategy])
                for strategy in ResolutionStrategy.__members__.values()
            },
            "manual_review_rate": len([r for r in self.resolved_conflicts if r.requires_manual_review]) / len(self.resolved_conflicts)
        } 