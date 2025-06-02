"""
Graph Database Integration Module

Provides production-ready integration with Kuzu graph database including:
- Connection management with pooling
- Schema initialization and validation
- Graph data operations
- Health checks and monitoring
- PostgreSQL synchronization support
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
import threading
from datetime import datetime, timezone

try:
    import kuzu
except ImportError:
    kuzu = None
    logging.warning("Kuzu not installed. Graph database features disabled.")

from server.core.config import get_settings
from server.monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

@dataclass
class GraphDatabaseConfig:
    """Configuration for Kuzu graph database"""
    database_path: str = "./data/kuzu_graph"
    buffer_pool_size: int = 1024 * 1024 * 1024  # 1GB
    max_num_threads: int = 8
    compression: bool = True
    auto_checkpoint: bool = True
    checkpoint_threshold: int = 64 * 1024 * 1024  # 64MB
    connection_pool_size: int = 10
    connection_timeout: int = 30
    query_timeout: int = 60
    enable_monitoring: bool = True

@dataclass
class GraphQueryResult:
    """Wrapper for graph query results"""
    success: bool
    data: List[Dict[str, Any]]
    execution_time: float
    error: Optional[str] = None
    row_count: int = 0
    
class GraphConnectionPool:
    """Thread-safe connection pool for Kuzu database"""
    
    def __init__(self, database: 'kuzu.Database', config: GraphDatabaseConfig) -> None:
        self.database = database
        self.config = config
        self._connections: List['kuzu.Connection'] = []
        self._available_connections: List['kuzu.Connection'] = []
        self._lock = threading.Lock()
        self._metrics = MetricsCollector()
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize connection pool"""
        logger.info(f"Initializing graph connection pool with {self.config.connection_pool_size} connections")
        
        for i in range(self.config.connection_pool_size):
            try:
                conn = kuzu.Connection(self.database, num_threads=2)
                self._connections.append(conn)
                self._available_connections.append(conn)
                logger.debug(f"Created graph connection {i+1}/{self.config.connection_pool_size}")
            except Exception as e:
                logger.error(f"Failed to create graph connection {i+1}: {e}")
                raise
    
    @contextmanager
    def get_connection(self) -> None:
        """Get connection from pool with automatic return"""
        connection = None
        start_time = time.time()
        
        try:
            # Wait for available connection
            timeout = self.config.connection_timeout
            while not self._available_connections and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            with self._lock:
                if not self._available_connections:
                    raise ConnectionError("No available graph connections in pool")
                
                connection = self._available_connections.pop()
                self._metrics.increment('graph_connections_acquired')
            
            yield connection
            
        finally:
            if connection:
                with self._lock:
                    self._available_connections.append(connection)
                    self._metrics.increment('graph_connections_returned')
    
    def close_all(self) -> None:
        """Close all connections in pool"""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing graph connection: {e}")
            
            self._connections.clear()
            self._available_connections.clear()
            logger.info("Graph connection pool closed")

class GraphSchemaManager:
    """Manages graph database schema and structure"""
    
    def __init__(self, connection_pool: GraphConnectionPool) -> None:
        self.connection_pool = connection_pool
        self._metrics = MetricsCollector()
    
    def initialize_schema(self) -> bool:
        """Initialize graph database schema"""
        logger.info("Initializing graph database schema")
        
        schema_queries = [
            # Node tables
            """
            CREATE NODE TABLE IF NOT EXISTS User(
                id STRING,
                username STRING,
                email STRING,
                created_at TIMESTAMP,
                properties MAP(STRING, STRING),
                PRIMARY KEY(id)
            )
            """,
            
            """
            CREATE NODE TABLE IF NOT EXISTS Project(
                id STRING,
                name STRING,
                description STRING,
                owner_id STRING,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                status STRING,
                properties MAP(STRING, STRING),
                PRIMARY KEY(id)
            )
            """,
            
            """
            CREATE NODE TABLE IF NOT EXISTS Memory(
                id STRING,
                content STRING,
                memory_type STRING,
                source_table STRING,
                source_id STRING,
                created_at TIMESTAMP,
                embeddings DOUBLE[],
                metadata MAP(STRING, STRING),
                PRIMARY KEY(id)
            )
            """,
            
            # Relationship tables
            """
            CREATE REL TABLE IF NOT EXISTS OWNS(
                FROM User TO Project,
                relationship_type STRING DEFAULT 'OWNS',
                created_at TIMESTAMP DEFAULT current_timestamp()
            )
            """,
            
            """
            CREATE REL TABLE IF NOT EXISTS COLLABORATES(
                FROM User TO Project,
                role STRING,
                permissions STRING[],
                created_at TIMESTAMP DEFAULT current_timestamp()
            )
            """,
            
            """
            CREATE REL TABLE IF NOT EXISTS CONTAINS(
                FROM Project TO Memory,
                relevance_score DOUBLE DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT current_timestamp()
            )
            """,
            
            """
            CREATE REL TABLE IF NOT EXISTS RELATES_TO(
                FROM Memory TO Memory,
                similarity_score DOUBLE,
                relationship_type STRING,
                created_at TIMESTAMP DEFAULT current_timestamp()
            )
            """,
            
            """
            CREATE REL TABLE IF NOT EXISTS ACCESSED_BY(
                FROM Memory TO User,
                access_type STRING,
                access_count INT64 DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT current_timestamp()
            )
            """
        ]
        
        try:
            with self.connection_pool.get_connection() as conn:
                for i, query in enumerate(schema_queries):
                    try:
                        result = conn.execute(query)
                        logger.debug(f"Schema query {i+1}/{len(schema_queries)} executed successfully")
                    except Exception as e:
                        logger.error(f"Failed to execute schema query {i+1}: {e}")
                        return False
            
            # Create indexes for better performance
            self._create_indexes()
            
            logger.info("Graph database schema initialized successfully")
            self._metrics.increment('graph_schema_initializations')
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize graph schema: {e}")
            self._metrics.increment('graph_schema_errors')
            return False
    
    def _create_indexes(self) -> None:
        """Create indexes for better query performance"""
        index_queries = [
            "CREATE INDEX IF NOT EXISTS user_email_idx ON User(email)",
            "CREATE INDEX IF NOT EXISTS project_owner_idx ON Project(owner_id)",
            "CREATE INDEX IF NOT EXISTS memory_type_idx ON Memory(memory_type)",
            "CREATE INDEX IF NOT EXISTS memory_source_idx ON Memory(source_table, source_id)",
        ]
        
        try:
            with self.connection_pool.get_connection() as conn:
                for query in index_queries:
                    try:
                        conn.execute(query)
                        logger.debug(f"Index created: {query}")
                    except Exception as e:
                        logger.warning(f"Failed to create index: {e}")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

class GraphQueryEngine:
    """Handles graph database queries and operations"""
    
    def __init__(self, connection_pool: GraphConnectionPool, config: GraphDatabaseConfig) -> None:
        self.connection_pool = connection_pool
        self.config = config
        self._metrics = MetricsCollector()
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> GraphQueryResult:
        """Execute a graph query with monitoring"""
        start_time = time.time()
        
        try:
            with self.connection_pool.get_connection() as conn:
                # Set query timeout if supported
                if hasattr(conn, 'set_query_timeout'):
                    conn.set_query_timeout(self.config.query_timeout * 1000)  # Convert to ms
                
                # Execute query
                if parameters:
                    result = conn.execute(query, parameters)
                else:
                    result = conn.execute(query)
                
                # Process results
                data = []
                row_count = 0
                
                if hasattr(result, 'has_next') and callable(result.has_next):
                    while result.has_next():
                        row = result.get_next()
                        data.append(self._process_row(row))
                        row_count += 1
                
                execution_time = time.time() - start_time
                
                # Record metrics
                self._metrics.record_histogram('graph_query_duration', execution_time)
                self._metrics.increment('graph_queries_executed')
                
                logger.debug(f"Graph query executed in {execution_time:.3f}s, returned {row_count} rows")
                
                return GraphQueryResult(
                    success=True,
                    data=data,
                    execution_time=execution_time,
                    row_count=row_count
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"Graph query failed after {execution_time:.3f}s: {error_msg}")
            self._metrics.increment('graph_query_errors')
            
            return GraphQueryResult(
                success=False,
                data=[],
                execution_time=execution_time,
                error=error_msg
            )
    
    def _process_row(self, row: Any) -> Dict[str, Any]:
        """Process a single row from query results"""
        if isinstance(row, (list, tuple)):
            return {f"col_{i}": self._serialize_value(val) for i, val in enumerate(row)}
        elif isinstance(row, dict):
            return {k: self._serialize_value(v) for k, v in row.items()}
        else:
            return {"value": self._serialize_value(row)}
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize values for JSON compatibility"""
        if isinstance(value, datetime):
            return value.isoformat()
        elif hasattr(value, '_asdict'):  # Named tuple
            return value._asdict()
        elif hasattr(value, '__dict__'):
            return value.__dict__
        else:
            return value

class GraphHealthChecker:
    """Health check functionality for graph database"""
    
    def __init__(self, connection_pool: GraphConnectionPool) -> None:
        self.connection_pool = connection_pool
        self._metrics = MetricsCollector()
    
    async def check_health(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {}
        }
        
        # Check connection pool
        health_status["checks"]["connection_pool"] = self._check_connection_pool()
        
        # Check database accessibility
        health_status["checks"]["database_access"] = await self._check_database_access()
        
        # Check schema integrity
        health_status["checks"]["schema_integrity"] = await self._check_schema_integrity()
        
        # Determine overall status
        failed_checks = [k for k, v in health_status["checks"].items() if not v.get("healthy", False)]
        if failed_checks:
            health_status["status"] = "unhealthy"
            health_status["failed_checks"] = failed_checks
        
        return health_status
    
    def _check_connection_pool(self) -> Dict[str, Any]:
        """Check connection pool status"""
        try:
            available = len(self.connection_pool._available_connections)
            total = len(self.connection_pool._connections)
            
            return {
                "healthy": True,
                "available_connections": available,
                "total_connections": total,
                "utilization": (total - available) / total if total > 0 else 0
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _check_database_access(self) -> Dict[str, Any]:
        """Check database accessibility"""
        try:
            with self.connection_pool.get_connection() as conn:
                start_time = time.time()
                result = conn.execute("MATCH (n) RETURN count(n) AS node_count LIMIT 1")
                response_time = time.time() - start_time
                
                return {
                    "healthy": True,
                    "response_time": response_time
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _check_schema_integrity(self) -> Dict[str, Any]:
        """Check schema integrity"""
        try:
            with self.connection_pool.get_connection() as conn:
                # Check if expected tables exist
                result = conn.execute("CALL show_tables() RETURN *")
                
                expected_tables = {"User", "Project", "Memory", "OWNS", "COLLABORATES", "CONTAINS", "RELATES_TO", "ACCESSED_BY"}
                found_tables = set()
                
                if hasattr(result, 'has_next'):
                    while result.has_next():
                        row = result.get_next()
                        if len(row) > 1:
                            found_tables.add(row[1])
                
                missing_tables = expected_tables - found_tables
                
                return {
                    "healthy": len(missing_tables) == 0,
                    "expected_tables": list(expected_tables),
                    "found_tables": list(found_tables),
                    "missing_tables": list(missing_tables)
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }

class GraphDatabaseManager:
    """Main graph database manager"""
    
    def __init__(self, config: Optional[GraphDatabaseConfig] = None) -> None:
        self.config = config or GraphDatabaseConfig()
        self.database: Optional['kuzu.Database'] = None
        self.connection_pool: Optional[GraphConnectionPool] = None
        self.schema_manager: Optional[GraphSchemaManager] = None
        self.query_engine: Optional[GraphQueryEngine] = None
        self.health_checker: Optional[GraphHealthChecker] = None
        self._metrics = MetricsCollector()
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize graph database manager"""
        if kuzu is None:
            logger.error("Kuzu not available. Cannot initialize graph database.")
            return False
        
        try:
            logger.info("Initializing graph database manager")
            
            # Ensure database directory exists
            db_path = Path(self.config.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            self.database = kuzu.Database(
                database_path=str(db_path),
                buffer_pool_size=self.config.buffer_pool_size,
                max_num_threads=self.config.max_num_threads,
                compression=self.config.compression,
                auto_checkpoint=self.config.auto_checkpoint,
                checkpoint_threshold=self.config.checkpoint_threshold
            )
            
            # Initialize connection pool
            self.connection_pool = GraphConnectionPool(self.database, self.config)
            
            # Initialize managers
            self.schema_manager = GraphSchemaManager(self.connection_pool)
            self.query_engine = GraphQueryEngine(self.connection_pool, self.config)
            self.health_checker = GraphHealthChecker(self.connection_pool)
            
            # Initialize schema
            if not self.schema_manager.initialize_schema():
                logger.error("Failed to initialize graph database schema")
                return False
            
            self._initialized = True
            self._metrics.increment('graph_database_initializations')
            logger.info("Graph database manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize graph database manager: {e}")
            self._metrics.increment('graph_database_initialization_errors')
            return False
    
    async def close(self) -> None:
        """Close graph database manager"""
        if self.connection_pool:
            self.connection_pool.close_all()
        
        if self.database:
            try:
                self.database.close()
            except Exception as e:
                logger.warning(f"Error closing graph database: {e}")
        
        self._initialized = False
        logger.info("Graph database manager closed")
    
    def is_healthy(self) -> bool:
        """Check if graph database is healthy"""
        return self._initialized and self.database is not None and self.connection_pool is not None

# Singleton instance
_graph_db_manager: Optional[GraphDatabaseManager] = None

async def get_graph_database() -> GraphDatabaseManager:
    """Get or create graph database manager instance"""
    global _graph_db_manager
    
    if _graph_db_manager is None:
        settings = get_settings()
        config = GraphDatabaseConfig(
            database_path=getattr(settings, 'GRAPH_DATABASE_PATH', './data/kuzu_graph'),
            buffer_pool_size=getattr(settings, 'GRAPH_BUFFER_POOL_SIZE', 1024*1024*1024),
            max_num_threads=getattr(settings, 'GRAPH_MAX_THREADS', 8),
            connection_pool_size=getattr(settings, 'GRAPH_CONNECTION_POOL_SIZE', 10),
            enable_monitoring=getattr(settings, 'GRAPH_ENABLE_MONITORING', True)
        )
        
        _graph_db_manager = GraphDatabaseManager(config)
        await _graph_db_manager.initialize()
    
    return _graph_db_manager

async def close_graph_database() -> None:
    """Close graph database manager"""
    global _graph_db_manager
    
    if _graph_db_manager:
        await _graph_db_manager.close()
        _graph_db_manager = None 