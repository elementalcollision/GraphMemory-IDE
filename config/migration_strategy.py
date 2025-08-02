"""
Migration Strategy Implementation for GraphMemory-IDE

This module implements the comprehensive migration strategy for transitioning
components between CPython and Codon runtimes with feature flags, gradual
rollouts, rollback mechanisms, and performance monitoring.

Based on Task 3-B requirements and industry best practices.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis
from prometheus_client import Counter, Gauge, Histogram

from .component_mapping import (
    MIGRATION_STRATEGY_CONFIG,
    ComponentMapping,
    MigrationPhase,
    ThreadSafetyLevel,
    get_component_mapping,
)

logger = logging.getLogger(__name__)

# Prometheus metrics for migration monitoring
MIGRATION_SUCCESS_COUNTER = Counter(
    "component_migration_success_total",
    "Total successful component migrations",
    ["component", "runtime"],
)

MIGRATION_FAILURE_COUNTER = Counter(
    "component_migration_failure_total",
    "Total failed component migrations",
    ["component", "runtime", "error_type"],
)

MIGRATION_DURATION = Histogram(
    "component_migration_duration_seconds",
    "Time spent on component migration",
    ["component", "runtime"],
)

ROLLBACK_COUNTER = Counter(
    "component_migration_rollback_total",
    "Total component migration rollbacks",
    ["component", "runtime", "reason"],
)

PERFORMANCE_DEGRADATION = Gauge(
    "component_performance_degradation_percent",
    "Performance degradation percentage during migration",
    ["component", "runtime"],
)


class MigrationStatus(Enum):
    """Migration status enumeration"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"


@dataclass
class MigrationMetrics:
    """Migration performance metrics"""

    start_time: datetime
    end_time: Optional[datetime] = None
    performance_baseline: float = 0.0
    current_performance: float = 0.0
    error_count: int = 0
    success_count: int = 0
    rollback_triggered: bool = False
    user_satisfaction_score: float = 0.0


@dataclass
class RollbackTrigger:
    """Rollback trigger configuration"""

    performance_threshold: float
    error_rate_threshold: float
    memory_usage_threshold: float
    cpu_usage_threshold: float
    user_satisfaction_threshold: float


class FeatureFlagManager:
    """Manages feature flags for component migration"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.feature_flags = MIGRATION_STRATEGY_CONFIG["feature_flags"]
        self.cache: Dict[str, bool] = {}

    async def is_feature_enabled(self, feature_flag: str) -> bool:
        """Check if a feature flag is enabled"""
        # Check cache first
        if feature_flag in self.cache:
            return self.cache[feature_flag]

        # Check environment variable
        env_var = self.feature_flags.get(feature_flag, {}).get("environment_var")
        if env_var and os.getenv(env_var, "").lower() in ("true", "1", "yes"):
            self.cache[feature_flag] = True
            return True

        # Check Redis if available
        if self.redis_client:
            try:
                redis_value = await self.redis_client.get(
                    f"feature_flag:{feature_flag}"
                )
                if redis_value:
                    enabled = redis_value.lower() == "true"
                    self.cache[feature_flag] = enabled
                    return enabled
            except Exception as e:
                logger.warning(
                    f"Failed to check Redis for feature flag {feature_flag}: {e}"
                )

        # Return default value
        default_value = self.feature_flags.get(feature_flag, {}).get("default", False)
        self.cache[feature_flag] = default_value
        return default_value

    async def set_feature_flag(self, feature_flag: str, enabled: bool) -> bool:
        """Set a feature flag value"""
        try:
            self.cache[feature_flag] = enabled

            # Update Redis if available
            if self.redis_client:
                await self.redis_client.set(
                    f"feature_flag:{feature_flag}",
                    str(enabled).lower(),
                    ex=3600,  # 1 hour TTL
                )

            logger.info(f"Feature flag {feature_flag} set to {enabled}")
            return True
        except Exception as e:
            logger.error(f"Failed to set feature flag {feature_flag}: {e}")
            return False


class PerformanceMonitor:
    """Monitors component performance during migration"""

    def __init__(self):
        self.metrics_history: Dict[str, List[MigrationMetrics]] = {}
        self.rollback_triggers = MIGRATION_STRATEGY_CONFIG["rollback_triggers"]

    async def measure_performance(
        self, component_name: str, measurement_func: Callable
    ) -> float:
        """Measure component performance"""
        start_time = time.time()

        try:
            result = await measurement_func()
            duration = time.time() - start_time

            # Record metrics
            if component_name not in self.metrics_history:
                self.metrics_history[component_name] = []

            metrics = MigrationMetrics(
                start_time=datetime.now(), current_performance=result, success_count=1
            )
            self.metrics_history[component_name].append(metrics)

            return result
        except Exception as e:
            logger.error(f"Performance measurement failed for {component_name}: {e}")
            return 0.0

    def should_rollback(
        self,
        component_name: str,
        current_performance: float,
        baseline_performance: float,
    ) -> bool:
        """Determine if rollback is needed based on performance"""
        if baseline_performance == 0:
            return False

        degradation_percent = (
            baseline_performance - current_performance
        ) / baseline_performance

        # Update Prometheus metric
        PERFORMANCE_DEGRADATION.labels(
            component=component_name, runtime="migration"
        ).set(degradation_percent * 100)

        # Check against rollback threshold
        mapping = get_component_mapping(component_name)
        if mapping:
            threshold = mapping.migration_strategy.rollback_threshold
            return degradation_percent > (1 - threshold)

        return False


class GradualRolloutManager:
    """Manages gradual rollout of component migrations"""

    def __init__(self, feature_flag_manager: FeatureFlagManager):
        self.feature_flag_manager = feature_flag_manager
        self.rollout_config = MIGRATION_STRATEGY_CONFIG["gradual_rollout"]
        self.rollout_state: Dict[str, Dict[str, Any]] = {}

    async def should_migrate_component(self, component_name: str, user_id: str) -> bool:
        """Determine if component should be migrated for this user"""
        mapping = get_component_mapping(component_name)
        if not mapping:
            return False

        # Check if feature flag is enabled
        feature_enabled = await self.feature_flag_manager.is_feature_enabled(
            mapping.migration_strategy.feature_flag
        )
        if not feature_enabled:
            return False

        # Get rollout state for component
        if component_name not in self.rollout_state:
            self.rollout_state[component_name] = {
                "current_percentage": self.rollout_config["initial_percentage"],
                "last_evaluation": datetime.now(),
                "success_count": 0,
                "failure_count": 0,
            }

        # Calculate user hash for consistent rollout
        user_hash = hash(user_id) % 100
        current_percentage = self.rollout_state[component_name]["current_percentage"]

        return user_hash < current_percentage

    async def update_rollout_percentage(
        self, component_name: str, success: bool
    ) -> None:
        """Update rollout percentage based on success/failure"""
        if component_name not in self.rollout_state:
            return

        state = self.rollout_state[component_name]

        if success:
            state["success_count"] += 1
        else:
            state["failure_count"] += 1

        # Evaluate if we should increase rollout percentage
        total_attempts = state["success_count"] + state["failure_count"]
        success_rate = (
            state["success_count"] / total_attempts if total_attempts > 0 else 0
        )

        # Check if enough time has passed and success criteria met
        time_since_evaluation = datetime.now() - state["last_evaluation"]
        evaluation_period = timedelta(
            hours=self.rollout_config["evaluation_period_hours"]
        )

        if (
            time_since_evaluation >= evaluation_period
            and success_rate
            >= self.rollout_config["success_criteria"]["performance_threshold"]
        ):

            # Increase rollout percentage
            current_percentage = state["current_percentage"]
            increment = self.rollout_config["increment_percentage"]
            new_percentage = min(100.0, current_percentage + increment)

            state["current_percentage"] = new_percentage
            state["last_evaluation"] = datetime.now()

            logger.info(
                f"Rollout percentage for {component_name} increased to {new_percentage}%"
            )

    async def get_rollout_status(self, component_name: str) -> Dict[str, Any]:
        """Get current rollout status for component"""
        if component_name not in self.rollout_state:
            return {"current_percentage": 0.0, "status": "not_started"}

        state = self.rollout_state[component_name]
        return {
            "current_percentage": state["current_percentage"],
            "success_count": state["success_count"],
            "failure_count": state["failure_count"],
            "last_evaluation": state["last_evaluation"].isoformat(),
            "status": "active" if state["current_percentage"] > 0 else "pending",
        }


class MigrationManager:
    """Main migration manager for coordinating component migrations"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = None
        self.feature_flag_manager = FeatureFlagManager()
        self.performance_monitor = PerformanceMonitor()
        self.rollout_manager = GradualRolloutManager(self.feature_flag_manager)
        self.redis_url = redis_url
        self.migration_history: Dict[str, MigrationMetrics] = {}

    async def initialize(self) -> None:
        """Initialize migration manager"""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            self.feature_flag_manager.redis_client = self.redis_client
            logger.info("Migration manager initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis for migration manager: {e}")

    async def migrate_component(
        self,
        component_name: str,
        user_id: str,
        baseline_measurement: Callable,
        migration_func: Callable,
    ) -> Dict[str, Any]:
        """Migrate a component with performance monitoring and rollback"""
        mapping = get_component_mapping(component_name)
        if not mapping:
            return {"success": False, "error": "Component mapping not found"}

        # Check if migration should proceed
        should_migrate = await self.rollout_manager.should_migrate_component(
            component_name, user_id
        )
        if not should_migrate:
            return {"success": False, "error": "Migration not enabled for user"}

        # Measure baseline performance
        baseline_performance = await self.performance_monitor.measure_performance(
            component_name, baseline_measurement
        )

        # Start migration
        start_time = time.time()
        migration_metrics = MigrationMetrics(
            start_time=datetime.now(), performance_baseline=baseline_performance
        )

        try:
            # Perform migration
            result = await migration_func()

            # Measure post-migration performance
            current_performance = await self.performance_monitor.measure_performance(
                component_name, baseline_measurement
            )

            migration_metrics.current_performance = current_performance
            migration_metrics.end_time = datetime.now()
            migration_metrics.success_count = 1

            # Check if rollback is needed
            if self.performance_monitor.should_rollback(
                component_name, current_performance, baseline_performance
            ):
                logger.warning(
                    f"Performance degradation detected for {component_name}, triggering rollback"
                )
                await self._rollback_component(component_name, migration_metrics)
                migration_metrics.rollback_triggered = True

                ROLLBACK_COUNTER.labels(
                    component=component_name,
                    runtime=mapping.runtime,
                    reason="performance_degradation",
                ).inc()

                return {
                    "success": False,
                    "error": "Performance degradation triggered rollback",
                    "baseline_performance": baseline_performance,
                    "current_performance": current_performance,
                }

            # Migration successful
            duration = time.time() - start_time
            MIGRATION_DURATION.labels(
                component=component_name, runtime=mapping.runtime
            ).observe(duration)

            MIGRATION_SUCCESS_COUNTER.labels(
                component=component_name, runtime=mapping.runtime
            ).inc()

            # Update rollout percentage
            await self.rollout_manager.update_rollout_percentage(component_name, True)

            # Store migration history
            self.migration_history[component_name] = migration_metrics

            return {
                "success": True,
                "baseline_performance": baseline_performance,
                "current_performance": current_performance,
                "duration": duration,
            }

        except Exception as e:
            logger.error(f"Migration failed for {component_name}: {e}")

            migration_metrics.error_count = 1
            migration_metrics.end_time = datetime.now()

            MIGRATION_FAILURE_COUNTER.labels(
                component=component_name,
                runtime=mapping.runtime,
                error_type="exception",
            ).inc()

            # Update rollout percentage
            await self.rollout_manager.update_rollout_percentage(component_name, False)

            return {"success": False, "error": str(e)}

    async def _rollback_component(
        self, component_name: str, metrics: MigrationMetrics
    ) -> None:
        """Rollback component migration"""
        logger.info(f"Rolling back migration for {component_name}")

        # TODO: Implement actual rollback logic
        # This would involve reverting to the previous runtime
        # and restoring the previous state

        metrics.rollback_triggered = True

    async def get_migration_status(self, component_name: str) -> Dict[str, Any]:
        """Get migration status for a component"""
        mapping = get_component_mapping(component_name)
        if not mapping:
            return {"error": "Component not found"}

        rollout_status = await self.rollout_manager.get_rollout_status(component_name)
        feature_enabled = await self.feature_flag_manager.is_feature_enabled(
            mapping.migration_strategy.feature_flag
        )

        return {
            "component": component_name,
            "runtime": mapping.runtime,
            "phase": mapping.migration_strategy.phase.value,
            "feature_enabled": feature_enabled,
            "rollout_status": rollout_status,
            "performance_benchmark": {
                "target_response_time_ms": mapping.performance_benchmark.target_response_time_ms,
                "target_throughput_rps": mapping.performance_benchmark.target_throughput_rps,
                "expected_speedup": mapping.performance_benchmark.expected_speedup,
            },
        }

    async def get_all_migration_status(self) -> Dict[str, Any]:
        """Get migration status for all components"""
        from .component_mapping import COMPONENT_MAPPINGS

        status = {}
        for component_name in COMPONENT_MAPPINGS.keys():
            status[component_name] = await self.get_migration_status(component_name)

        return status
