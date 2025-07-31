"""Component Mapping & Runtime Assignment Configuration.

This module defines the comprehensive mapping of all GraphMemory-IDE components
to their target runtimes (CPython vs Condon) with migration strategies,
performance characteristics, and thread safety requirements.

Based on Task 3-B requirements and analysis of current architecture.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

# Runtime Types
RuntimeType = Literal["cpython", "condon", "hybrid"]


class MigrationPhase(Enum):
    """Migration phases for gradual rollout"""

    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    ROLLBACK = "rollback"


class ThreadSafetyLevel(Enum):
    """Thread safety requirements"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PerformanceBenchmark:
    """Performance benchmarks for each component"""

    target_response_time_ms: float
    target_throughput_rps: float
    memory_limit_mb: float
    cpu_limit_percent: float
    expected_speedup: float  # Expected improvement with Condon


@dataclass
class MigrationStrategy:
    """Migration strategy for each component"""

    phase: MigrationPhase
    feature_flag: str
    rollback_threshold: float  # Performance degradation threshold
    gradual_rollout_percent: float
    dependencies: list[str] = field(default_factory=list)
    compatibility_requirements: list[str] = field(default_factory=list)


@dataclass
class ComponentMapping:
    """Component mapping configuration"""

    component_name: str
    runtime: RuntimeType
    reason: str
    performance_requirements: ThreadSafetyLevel
    migration_strategy: MigrationStrategy
    performance_benchmark: PerformanceBenchmark
    condon_parts: list[str] = field(default_factory=list)  # For hybrid
    cpython_parts: list[str] = field(default_factory=list)  # For hybrid


# Component Mapping Configuration
COMPONENT_MAPPINGS: dict[str, ComponentMapping] = {
    # ===== CONDON RUNTIME COMPONENTS (Performance Critical) =====
    "analytics_engine": ComponentMapping(
        component_name="analytics_engine",
        runtime="condon",
        reason=(
            "Graph algorithms and ML analytics performance critical - "
            "10-100x speedup expected"
        ),
        performance_requirements=ThreadSafetyLevel.CRITICAL,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.ACTIVE,
            feature_flag="ENABLE_CONDON_ANALYTICS",
            rollback_threshold=0.8,  # 20% performance degradation threshold
            gradual_rollout_percent=25.0,
            dependencies=["kuzu_graphdb", "redis_cache"],
            compatibility_requirements=["python_interop", "numpy_compatibility"],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=100.0,
            target_throughput_rps=1000.0,
            memory_limit_mb=2048.0,
            cpu_limit_percent=80.0,
            expected_speedup=50.0,  # 50x improvement expected
        ),
    ),
    "ai_detection": ComponentMapping(
        component_name="ai_detection",
        runtime="condon",
        reason=(
            "ML model inference and TensorFlow operations - " "5-10x speedup expected"
        ),
        performance_requirements=ThreadSafetyLevel.CRITICAL,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.ACTIVE,
            feature_flag="ENABLE_CONDON_AI_DETECTION",
            rollback_threshold=0.85,
            gradual_rollout_percent=15.0,
            dependencies=["tensorflow", "scikit_learn"],
            compatibility_requirements=["tensorflow_interop", "ml_libraries"],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=200.0,
            target_throughput_rps=500.0,
            memory_limit_mb=4096.0,
            cpu_limit_percent=90.0,
            expected_speedup=8.0,
        ),
    ),
    "performance_monitor": ComponentMapping(
        component_name="performance_monitor",
        runtime="condon",
        reason=(
            "Real-time metrics processing and Prometheus integration - "
            "3-5x speedup expected"
        ),
        performance_requirements=ThreadSafetyLevel.HIGH,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.ACTIVE,
            feature_flag="ENABLE_CONDON_MONITORING",
            rollback_threshold=0.9,
            gradual_rollout_percent=20.0,
            dependencies=["prometheus", "redis_cache"],
            compatibility_requirements=["prometheus_client", "metrics_export"],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=50.0,
            target_throughput_rps=2000.0,
            memory_limit_mb=1024.0,
            cpu_limit_percent=70.0,
            expected_speedup=4.0,
        ),
    ),
    "ai_performance_optimizer": ComponentMapping(
        component_name="ai_performance_optimizer",
        runtime="condon",
        reason="ML-driven optimization algorithms - 10-20x speedup expected",
        performance_requirements=ThreadSafetyLevel.CRITICAL,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.PLANNED,
            feature_flag="ENABLE_CONDON_AI_OPTIMIZER",
            rollback_threshold=0.8,
            gradual_rollout_percent=10.0,
            dependencies=["ml_models", "redis_cache"],
            compatibility_requirements=["scikit_learn", "pandas", "numpy"],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=300.0,
            target_throughput_rps=200.0,
            memory_limit_mb=3072.0,
            cpu_limit_percent=85.0,
            expected_speedup=15.0,
        ),
    ),
    # ===== CPYTHON RUNTIME COMPONENTS (Web Framework Compatibility) =====
    "auth_routes": ComponentMapping(
        component_name="auth_routes",
        runtime="cpython",
        reason="FastAPI compatibility and web framework integration",
        performance_requirements=ThreadSafetyLevel.HIGH,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.COMPLETED,
            feature_flag="KEEP_CPYTHON_AUTH",
            rollback_threshold=1.0,  # No rollback needed
            gradual_rollout_percent=100.0,
            dependencies=["fastapi", "jwt"],
            compatibility_requirements=["fastapi_compatibility", "web_framework"],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=50.0,
            target_throughput_rps=500.0,
            memory_limit_mb=512.0,
            cpu_limit_percent=60.0,
            expected_speedup=1.0,  # No speedup expected
        ),
    ),
    "dashboard": ComponentMapping(
        component_name="dashboard",
        runtime="cpython",
        reason="Streamlit compatibility and web dashboard integration",
        performance_requirements=ThreadSafetyLevel.MEDIUM,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.COMPLETED,
            feature_flag="KEEP_CPYTHON_DASHBOARD",
            rollback_threshold=1.0,
            gradual_rollout_percent=100.0,
            dependencies=["streamlit", "plotly"],
            compatibility_requirements=["streamlit_compatibility", "web_ui"],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=100.0,
            target_throughput_rps=100.0,
            memory_limit_mb=1024.0,
            cpu_limit_percent=50.0,
            expected_speedup=1.0,
        ),
    ),
    "streaming": ComponentMapping(
        component_name="streaming",
        runtime="cpython",
        reason="WebSocket real-time communication and FastAPI integration",
        performance_requirements=ThreadSafetyLevel.CRITICAL,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.COMPLETED,
            feature_flag="KEEP_CPYTHON_STREAMING",
            rollback_threshold=1.0,
            gradual_rollout_percent=100.0,
            dependencies=["websockets", "fastapi"],
            compatibility_requirements=[
                "websocket_compatibility",
                "realtime_communication",
            ],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=10.0,
            target_throughput_rps=1000.0,
            memory_limit_mb=512.0,
            cpu_limit_percent=80.0,
            expected_speedup=1.0,
        ),
    ),
    # ===== HYBRID COMPONENTS (Mixed Runtime) =====
    "collaboration": ComponentMapping(
        component_name="collaboration",
        runtime="hybrid",
        reason="Mixed web API (CPython) and real-time processing (Condon)",
        performance_requirements=ThreadSafetyLevel.CRITICAL,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.ACTIVE,
            feature_flag="ENABLE_HYBRID_COLLABORATION",
            rollback_threshold=0.85,
            gradual_rollout_percent=30.0,
            dependencies=["websockets", "redis_cache", "crdt_engine"],
            compatibility_requirements=["service_boundary", "python_interop"],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=200.0,
            target_throughput_rps=300.0,
            memory_limit_mb=2048.0,
            cpu_limit_percent=75.0,
            expected_speedup=3.0,
        ),
        condon_parts=["real_time_processing", "ml_features", "crdt_engine"],
        cpython_parts=["web_api", "websocket", "auth_integration"],
    ),
    "memory_conflict_resolution": ComponentMapping(
        component_name="memory_conflict_resolution",
        runtime="hybrid",
        reason=(
            "Complex conflict resolution with ML algorithms (Condon) "
            "and web API (CPython)"
        ),
        performance_requirements=ThreadSafetyLevel.CRITICAL,
        migration_strategy=MigrationStrategy(
            phase=MigrationPhase.PLANNED,
            feature_flag="ENABLE_HYBRID_CONFLICT_RESOLUTION",
            rollback_threshold=0.8,
            gradual_rollout_percent=20.0,
            dependencies=["ml_algorithms", "redis_cache", "web_api"],
            compatibility_requirements=["ml_interop", "service_boundary"],
        ),
        performance_benchmark=PerformanceBenchmark(
            target_response_time_ms=150.0,
            target_throughput_rps=400.0,
            memory_limit_mb=1536.0,
            cpu_limit_percent=70.0,
            expected_speedup=5.0,
        ),
        condon_parts=["ml_algorithms", "conflict_detection", "resolution_engine"],
        cpython_parts=["web_api", "user_interface", "audit_logging"],
    ),
}

# Runtime Performance Characteristics
RUNTIME_PERFORMANCE_CHARACTERISTICS = {
    "cpython": {
        "description": "Standard Python runtime with GIL limitations",
        "strengths": [
            "Full Python ecosystem compatibility",
            "Dynamic features support",
            "Easy debugging and development",
            "Web framework integration",
        ],
        "limitations": [
            "Global Interpreter Lock (GIL)",
            "Limited multithreading performance",
            "Runtime overhead",
            "Memory management overhead",
        ],
        "best_for": [
            "Web frameworks (FastAPI, Streamlit)",
            "I/O bound operations",
            "Prototyping and development",
            "Dynamic code execution",
        ],
    },
    "condon": {
        "description": ("High-performance Python compiler with native code generation"),
        "strengths": [
            "10-100x performance improvement",
            "Native multithreading (no GIL)",
            "Ahead-of-time compilation",
            "Memory safety and efficiency",
        ],
        "limitations": [
            "Not drop-in Python replacement",
            "Limited dynamic features",
            "Compilation complexity",
            "Some Python modules not supported",
        ],
        "best_for": [
            "CPU-intensive computations",
            "ML and AI algorithms",
            "Graph algorithms",
            "Performance-critical components",
        ],
    },
    "hybrid": {
        "description": "Mixed runtime approach with service boundaries",
        "strengths": [
            "Best of both worlds",
            "Gradual migration capability",
            "Service isolation",
            "Flexible deployment",
        ],
        "limitations": [
            "Increased complexity",
            "Service communication overhead",
            "Coordination challenges",
            "Debugging complexity",
        ],
        "best_for": [
            "Complex systems with mixed requirements",
            "Gradual migration strategies",
            "Performance-critical with web integration",
            "Experimental features",
        ],
    },
}

# Migration Strategy Configuration
MIGRATION_STRATEGY_CONFIG = {
    "feature_flags": {
        "ENABLE_CONDON_ANALYTICS": {
            "default": False,
            "environment_var": "ENABLE_CONDON_ANALYTICS",
            "description": "Enable Condon runtime for analytics engine",
        },
        "ENABLE_CONDON_AI_DETECTION": {
            "default": False,
            "environment_var": "ENABLE_CONDON_AI_DETECTION",
            "description": "Enable Condon runtime for AI detection",
        },
        "ENABLE_CONDON_MONITORING": {
            "default": False,
            "environment_var": "ENABLE_CONDON_MONITORING",
            "description": "Enable Condon runtime for performance monitoring",
        },
        "ENABLE_CONDON_AI_OPTIMIZER": {
            "default": False,
            "environment_var": "ENABLE_CONDON_AI_OPTIMIZER",
            "description": ("Enable Condon runtime for AI performance optimizer"),
        },
        "ENABLE_HYBRID_COLLABORATION": {
            "default": False,
            "environment_var": "ENABLE_HYBRID_COLLABORATION",
            "description": "Enable hybrid runtime for collaboration system",
        },
        "ENABLE_HYBRID_CONFLICT_RESOLUTION": {
            "default": False,
            "environment_var": "ENABLE_HYBRID_CONFLICT_RESOLUTION",
            "description": "Enable hybrid runtime for conflict resolution",
        },
    },
    "rollback_triggers": {
        "performance_degradation": 0.8,  # 20% performance degradation
        "error_rate_threshold": 0.05,  # 5% error rate
        "memory_usage_threshold": 0.9,  # 90% memory usage
        "cpu_usage_threshold": 0.95,  # 95% CPU usage
    },
    "gradual_rollout": {
        "initial_percentage": 5.0,
        "increment_percentage": 10.0,
        "evaluation_period_hours": 24,
        "success_criteria": {
            "performance_threshold": 0.9,
            "error_rate_threshold": 0.01,
            "user_satisfaction_threshold": 0.8,
        },
    },
}


def get_component_mapping(component_name: str) -> Optional[ComponentMapping]:
    """Get component mapping configuration"""
    return COMPONENT_MAPPINGS.get(component_name)


def get_condon_components() -> list[str]:
    """Get list of components mapped to Condon runtime"""
    return [
        name
        for name, mapping in COMPONENT_MAPPINGS.items()
        if mapping.runtime == "condon"
    ]


def get_cpython_components() -> list[str]:
    """Get list of components mapped to CPython runtime"""
    return [
        name
        for name, mapping in COMPONENT_MAPPINGS.items()
        if mapping.runtime == "cpython"
    ]


def get_hybrid_components() -> list[str]:
    """Get list of hybrid components"""
    return [
        name
        for name, mapping in COMPONENT_MAPPINGS.items()
        if mapping.runtime == "hybrid"
    ]


def get_migration_phase_components(phase: MigrationPhase) -> list[str]:
    """Get components in specific migration phase"""
    return [
        name
        for name, mapping in COMPONENT_MAPPINGS.items()
        if mapping.migration_strategy.phase == phase
    ]


def get_dependency_graph() -> dict[str, list[str]]:
    """Get the dependency graph for all components"""
    dependency_graph: dict[str, list[str]] = {}
    for name, mapping in COMPONENT_MAPPINGS.items():
        dependency_graph[name] = mapping.migration_strategy.dependencies.copy()
    return dependency_graph


def detect_circular_dependencies() -> list[str]:
    """Detect circular dependencies in component mappings"""
    issues = []

    # Build dependency graph
    dependency_graph = get_dependency_graph()

    # Track visited nodes and recursion stack for DFS
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle_dfs(node: str, path: list[str]) -> bool:
        """Depth-first search to detect cycles"""
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycle_path = path[cycle_start:] + [node]
            issues.append(f"Circular dependency detected: {' -> '.join(cycle_path)}")
            return True

        if node in visited:
            return False

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        # Check all dependencies
        for dep in dependency_graph.get(node, []):
            if has_cycle_dfs(dep, path):
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    # Check for cycles starting from each component
    for component in dependency_graph:
        if component not in visited:
            has_cycle_dfs(component, [])

    return issues


def get_topological_order() -> list[str]:
    """Get topological order of components for dependency resolution"""
    dependency_graph = get_dependency_graph()

    # Calculate in-degrees
    in_degree: dict[str, int] = {node: 0 for node in dependency_graph}
    for node, deps in dependency_graph.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[dep] += 1

    # Kahn's algorithm for topological sort
    queue: list[str] = [node for node, degree in in_degree.items() if not degree]
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)

        for dep in dependency_graph.get(node, []):
            in_degree[dep] -= 1
            if not in_degree[dep]:
                queue.append(dep)

    # Check if we have a valid topological order
    if len(result) != len(dependency_graph):
        # There are cycles, return empty list
        return []

    return result


def validate_component_mappings() -> list[str]:
    """Validate component mappings and return any issues"""
    issues = []

    for name, mapping in COMPONENT_MAPPINGS.items():
        # Check for missing dependencies
        for dep in mapping.migration_strategy.dependencies:
            if dep not in COMPONENT_MAPPINGS:
                issues.append(
                    f"Component '{name}' depends on missing component '{dep}'"
                )

        # Check for circular dependencies
        circular_deps = detect_circular_dependencies()
        issues.extend(circular_deps)

        # Validate performance benchmarks
        if mapping.performance_benchmark.target_response_time_ms <= 0:
            issues.append(f"Invalid response time for component '{name}'")

        if mapping.performance_benchmark.expected_speedup < 1.0:
            issues.append(f"Expected speedup should be >= 1.0 for component '{name}'")

    return issues
