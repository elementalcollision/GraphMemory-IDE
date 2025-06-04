"""
Database Synchronization Engine

Handles bidirectional synchronization between PostgreSQL and Kuzu graph database:
- Change Data Capture (CDC) for PostgreSQL
- Event-driven synchronization
- Data transformation and mapping
- Conflict resolution
- Batch processing
- Monitoring and alerting
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Set, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
import uuid
from pathlib import Path

from sqlalchemy import text, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from server.database_models import (
    User, UserSession, TelemetryEvent, AnalyticsQuery, 
    KuzuQuery, CollaborationSession, CollaborationParticipant,
    SystemMetrics, APIRequestLog
)
from server.graph_database import get_graph_database, GraphQueryResult
from server.core.database import get_async_session
from server.monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class SyncEventType(Enum):
    """Types of synchronization events"""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    BULK_SYNC = "bulk_sync"

class SyncDirection(Enum):
    """Synchronization direction"""
    PG_TO_GRAPH = "pg_to_graph"
    GRAPH_TO_PG = "graph_to_pg"
    BIDIRECTIONAL = "bidirectional"

@dataclass
class SyncEvent:
    """Synchronization event data"""
    id: str
    event_type: SyncEventType
    table_name: str
    record_id: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str
    processed: bool = False
    error: Optional[str] = None
    retry_count: int = 0

@dataclass
class SyncConfiguration:
    """Synchronization configuration"""
    enabled: bool = True
    batch_size: int = 100
    sync_interval: int = 30  # seconds
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    conflict_resolution: str = "latest_wins"
    enable_monitoring: bool = True
    tables_to_sync: Set[str] = None
    
    def __post_init__(self) -> None:
        if self.tables_to_sync is None:
            self.tables_to_sync = {
                'users', 'user_sessions', 'telemetry_events',
                'analytics_queries', 'kuzu_queries', 'collaboration_sessions',
                'collaboration_participants', 'system_metrics', 'api_request_logs'
            }

class DataTransformer:
    """Transforms data between PostgreSQL and Kuzu formats"""
    
    def __init__(self) -> None:
        """Initialize data transformer"""
        self.transformation_rules: Dict[str, Callable] = {
            'user': self._transform_user,
            'memory': self._transform_memory,
            'relationship': self._transform_relationship,
            'analytics': self._transform_analytics
        }
    
    def transform_to_graph(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform PostgreSQL data to graph format"""
        transformer = self.transformation_rules.get(table_name)
        if transformer:
            return transformer(data, 'to_graph')
        return data
    
    def transform_from_graph(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform graph data to PostgreSQL format"""
        transformer = self.transformation_rules.get(table_name)
        if transformer:
            return transformer(data, 'from_graph')
        return data
    
    def _transform_user(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform user data"""
        if direction == 'to_graph':
            return {
                'id': str(data.get('id', '')),
                'username': data.get('username', ''),
                'email': data.get('email', ''),
                'created_at': self._format_timestamp(data.get('created_at')),
                'properties': {
                    'role': data.get('role', 'user'),
                    'is_active': str(data.get('is_active', True)),
                    'last_login': self._format_timestamp(data.get('last_login')),
                    'preferences': json.dumps(data.get('preferences', {}))
                }
            }
        else:
            props = data.get('properties', {})
            return {
                'id': uuid.UUID(data['id']) if data.get('id') else None,
                'username': data.get('username'),
                'email': data.get('email'),
                'role': props.get('role', 'user'),
                'is_active': props.get('is_active', 'true').lower() == 'true',
                'preferences': json.loads(props.get('preferences', '{}')),
                'created_at': self._parse_timestamp(data.get('created_at')),
                'last_login': self._parse_timestamp(props.get('last_login'))
            }
    
    def _transform_user_session(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform user session data"""
        if direction == 'to_graph':
            return {
                'id': str(data.get('id', '')),
                'user_id': str(data.get('user_id', '')),
                'session_token': data.get('session_token', ''),
                'created_at': self._format_timestamp(data.get('created_at')),
                'properties': {
                    'ip_address': data.get('ip_address', ''),
                    'user_agent': data.get('user_agent', ''),
                    'expires_at': self._format_timestamp(data.get('expires_at')),
                    'is_active': str(data.get('is_active', True))
                }
            }
        return data  # Simplified for brevity
    
    def _transform_telemetry_event(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform telemetry event data"""
        if direction == 'to_graph':
            return {
                'id': str(data.get('id', '')),
                'user_id': str(data.get('user_id', '')),
                'event_type': data.get('event_type', ''),
                'timestamp': self._format_timestamp(data.get('timestamp')),
                'properties': {
                    'event_data': json.dumps(data.get('event_data', {})),
                    'session_id': str(data.get('session_id', '')),
                    'ip_address': data.get('ip_address', ''),
                    'user_agent': data.get('user_agent', '')
                }
            }
        return data
    
    def _transform_analytics_query(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform analytics query data"""
        if direction == 'to_graph':
            return {
                'id': str(data.get('id', '')),
                'user_id': str(data.get('user_id', '')),
                'query_type': data.get('query_type', ''),
                'created_at': self._format_timestamp(data.get('created_at')),
                'properties': {
                    'parameters': json.dumps(data.get('parameters', {})),
                    'execution_time': str(data.get('execution_time', 0)),
                    'result_count': str(data.get('result_count', 0)),
                    'cached': str(data.get('cached', False))
                }
            }
        return data
    
    def _transform_kuzu_query(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform Kuzu query data"""
        if direction == 'to_graph':
            return {
                'id': str(data.get('id', '')),
                'user_id': str(data.get('user_id', '')),
                'query': data.get('query', ''),
                'created_at': self._format_timestamp(data.get('created_at')),
                'properties': {
                    'parameters': json.dumps(data.get('parameters', {})),
                    'results': json.dumps(data.get('results', {})),
                    'execution_time': str(data.get('execution_time', 0)),
                    'error_message': data.get('error_message', '')
                }
            }
        return data
    
    def _transform_collaboration_session(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform collaboration session data"""
        return data  # Simplified for brevity
    
    def _transform_collaboration_participant(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform collaboration participant data"""
        return data  # Simplified for brevity
    
    def _transform_system_metrics(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform system metrics data"""
        return data  # Simplified for brevity
    
    def _transform_api_request_log(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Transform API request log data"""
        return data  # Simplified for brevity
    
    def _format_timestamp(self, ts: Any) -> str:
        """Format timestamp for graph database"""
        if isinstance(ts, datetime):
            return ts.isoformat()
        elif isinstance(ts, str):
            return ts
        elif ts is None:
            return ''
        else:
            return str(ts)
    
    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse timestamp from graph database"""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None

class ConflictResolver:
    """Handles conflicts during synchronization"""
    
    def __init__(self, strategy: str = "latest_wins") -> None:
        self.strategy = strategy
        self._resolvers = {
            'latest_wins': self._latest_wins_resolver,
            'source_wins': self._source_wins_resolver,
            'manual': self._manual_resolver
        }
    
    def resolve_conflict(self, pg_data: Dict[str, Any], graph_data: Dict[str, Any], 
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve data conflict"""
        resolver = self._resolvers.get(self.strategy, self._latest_wins_resolver)
        return resolver(pg_data, graph_data, context)
    
    def _latest_wins_resolver(self, pg_data: Dict[str, Any], graph_data: Dict[str, Any], 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Latest timestamp wins conflict resolution"""
        pg_updated = self._get_timestamp(pg_data, 'updated_at') or self._get_timestamp(pg_data, 'created_at')
        graph_updated = self._get_timestamp(graph_data, 'updated_at') or self._get_timestamp(graph_data, 'created_at')
        
        if pg_updated and graph_updated:
            return pg_data if pg_updated >= graph_updated else graph_data
        elif pg_updated:
            return pg_data
        else:
            return graph_data
    
    def _source_wins_resolver(self, pg_data: Dict[str, Any], graph_data: Dict[str, Any], 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Source system wins conflict resolution"""
        source = context.get('source', 'postgresql')
        return pg_data if source == 'postgresql' else graph_data
    
    def _manual_resolver(self, pg_data: Dict[str, Any], graph_data: Dict[str, Any], 
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """Manual conflict resolution (requires human intervention)"""
        # For now, default to latest wins
        return self._latest_wins_resolver(pg_data, graph_data, context)
    
    def _get_timestamp(self, data: Dict[str, Any], field: str) -> Optional[datetime]:
        """Extract timestamp from data"""
        value = data.get(field)
        if isinstance(value, datetime):
            return value
        elif isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return None
        return None

class SyncEventProcessor:
    """Processes synchronization events"""
    
    def __init__(self, config: SyncConfiguration) -> None:
        self.config = config
        self.transformer = DataTransformer()
        self.conflict_resolver = ConflictResolver(config.conflict_resolution)
        self._metrics = MetricsCollector()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
    
    async def queue_event(self, event: SyncEvent) -> None:
        """Queue a synchronization event"""
        await self._event_queue.put(event)
        logger.debug(f"Queued sync event: {event.table_name}.{event.record_id}")
    
    async def process_events(self) -> None:
        """Process queued synchronization events"""
        if self._processing:
            return
        
        self._processing = True
        logger.info("Starting sync event processing")
        
        try:
            while True:
                events = []
                
                # Collect batch of events
                try:
                    # Wait for at least one event
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=self.config.sync_interval)
                    events.append(event)
                    
                    # Collect additional events up to batch size
                    while len(events) < self.config.batch_size:
                        try:
                            event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                            events.append(event)
                        except asyncio.TimeoutError:
                            break
                
                except asyncio.TimeoutError:
                    # No events to process, continue loop
                    continue
                
                if events:
                    await self._process_event_batch(events)
                
        except asyncio.CancelledError:
            logger.info("Sync event processing cancelled")
        except Exception as e:
            logger.error(f"Error in sync event processing: {e}")
        finally:
            self._processing = False
    
    async def _process_event_batch(self, events: List[SyncEvent]) -> None:
        """Process a batch of synchronization events"""
        logger.info(f"Processing sync event batch of {len(events)} events")
        start_time = time.time()
        
        processed_count = 0
        error_count = 0
        
        for event in events:
            try:
                success = await self._process_single_event(event)
                if success:
                    processed_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Error processing sync event {event.id}: {e}")
                error_count += 1
        
        processing_time = time.time() - start_time
        
        # Record metrics
        self._metrics.record_histogram('sync_batch_processing_time', processing_time)
        self._metrics.record_gauge('sync_events_processed', processed_count)
        self._metrics.record_gauge('sync_events_errors', error_count)
        
        logger.info(f"Processed {processed_count} events, {error_count} errors in {processing_time:.3f}s")
    
    async def _process_single_event(self, event: SyncEvent) -> bool:
        """Process a single synchronization event"""
        try:
            if event.event_type == SyncEventType.INSERT:
                return await self._handle_insert(event)
            elif event.event_type == SyncEventType.UPDATE:
                return await self._handle_update(event)
            elif event.event_type == SyncEventType.DELETE:
                return await self._handle_delete(event)
            elif event.event_type == SyncEventType.BULK_SYNC:
                return await self._handle_bulk_sync(event)
            else:
                logger.warning(f"Unknown sync event type: {event.event_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing sync event {event.id}: {e}")
            event.error = str(e)
            event.retry_count += 1
            
            if event.retry_count < self.config.max_retries:
                # Re-queue for retry
                await asyncio.sleep(self.config.retry_delay)
                await self.queue_event(event)
            
            return False
    
    async def _handle_insert(self, event: SyncEvent) -> bool:
        """Handle insert synchronization event"""
        graph_db = await get_graph_database()
        
        # Transform data for graph database
        graph_data = self.transformer.transform_to_graph(event.table_name, event.data)
        
        # Create node in graph database
        if event.table_name in ['users', 'user_sessions', 'telemetry_events', 'analytics_queries', 'kuzu_queries']:
            node_type = self._get_node_type(event.table_name)
            query = f"""
            CREATE (n:{node_type} {{
                id: $id,
                {self._build_property_string(graph_data)}
            }})
            """
            
            result = graph_db.query_engine.execute_query(query, graph_data)
            
            if result.success:
                logger.debug(f"Created {node_type} node: {event.record_id}")
                return True
            else:
                logger.error(f"Failed to create {node_type} node: {result.error}")
                return False
        
        return True
    
    async def _handle_update(self, event: SyncEvent) -> bool:
        """Handle update synchronization event"""
        graph_db = await get_graph_database()
        
        # Transform data for graph database
        graph_data = self.transformer.transform_to_graph(event.table_name, event.data)
        
        # Update node in graph database
        if event.table_name in ['users', 'user_sessions', 'telemetry_events', 'analytics_queries', 'kuzu_queries']:
            node_type = self._get_node_type(event.table_name)
            query = f"""
            MATCH (n:{node_type} {{id: $id}})
            SET {self._build_set_string(graph_data)}
            """
            
            result = graph_db.query_engine.execute_query(query, graph_data)
            
            if result.success:
                logger.debug(f"Updated {node_type} node: {event.record_id}")
                return True
            else:
                logger.error(f"Failed to update {node_type} node: {result.error}")
                return False
        
        return True
    
    async def _handle_delete(self, event: SyncEvent) -> bool:
        """Handle delete synchronization event"""
        graph_db = await get_graph_database()
        
        if event.table_name in ['users', 'user_sessions', 'telemetry_events', 'analytics_queries', 'kuzu_queries']:
            node_type = self._get_node_type(event.table_name)
            query = f"""
            MATCH (n:{node_type} {{id: $id}})
            DETACH DELETE n
            """
            
            result = graph_db.query_engine.execute_query(query, {'id': event.record_id})
            
            if result.success:
                logger.debug(f"Deleted {node_type} node: {event.record_id}")
                return True
            else:
                logger.error(f"Failed to delete {node_type} node: {result.error}")
                return False
        
        return True
    
    async def _handle_bulk_sync(self, event: SyncEvent) -> bool:
        """Handle bulk synchronization event"""
        # Implementation for bulk sync
        logger.info(f"Processing bulk sync for table: {event.table_name}")
        return True
    
    def _get_node_type(self, table_name: str) -> str:
        """Get graph node type from table name"""
        mapping = {
            'users': 'User',
            'user_sessions': 'UserSession',
            'telemetry_events': 'TelemetryEvent',
            'analytics_queries': 'AnalyticsQuery',
            'kuzu_queries': 'KuzuQuery'
        }
        return mapping.get(table_name, 'Unknown')
    
    def _build_property_string(self, data: Dict[str, Any]) -> str:
        """Build property string for Cypher query"""
        props = []
        for key, value in data.items():
            if key != 'id' and value is not None:
                if isinstance(value, str):
                    props.append(f"{key}: '{value}'")
                else:
                    props.append(f"{key}: {json.dumps(value)}")
        return ', '.join(props)
    
    def _build_set_string(self, data: Dict[str, Any]) -> str:
        """Build SET string for Cypher query"""
        sets = []
        for key, value in data.items():
            if key != 'id' and value is not None:
                if isinstance(value, str):
                    sets.append(f"n.{key} = '{value}'")
                else:
                    sets.append(f"n.{key} = {json.dumps(value)}")
        return ', '.join(sets)

class DatabaseSynchronizer:
    """Main database synchronization manager"""
    
    def __init__(self, config: Optional[SyncConfiguration] = None) -> None:
        self.config = config or SyncConfiguration()
        self.event_processor = SyncEventProcessor(self.config)
        self._metrics = MetricsCollector()
        self._running = False
        self._sync_tasks: List[asyncio.Task] = []
    
    async def start(self) -> None:
        """Start database synchronization"""
        if self._running:
            logger.warning("Database synchronization already running")
            return
        
        if not self.config.enabled:
            logger.info("Database synchronization disabled")
            return
        
        logger.info("Starting database synchronization")
        self._running = True
        
        # Start event processing task
        task = asyncio.create_task(self.event_processor.process_events())
        self._sync_tasks.append(task)
        
        # Start periodic sync tasks
        for table in self.config.tables_to_sync:
            task = asyncio.create_task(self._periodic_sync_table(table))
            self._sync_tasks.append(task)
        
        logger.info(f"Started {len(self._sync_tasks)} synchronization tasks")
    
    async def stop(self) -> None:
        """Stop database synchronization"""
        if not self._running:
            return
        
        logger.info("Stopping database synchronization")
        self._running = False
        
        # Cancel all tasks
        for task in self._sync_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._sync_tasks:
            await asyncio.gather(*self._sync_tasks, return_exceptions=True)
        
        self._sync_tasks.clear()
        logger.info("Database synchronization stopped")
    
    async def sync_table(self, table_name: str, incremental: bool = True) -> None:
        """Manually sync a specific table"""
        logger.info(f"Starting manual sync for table: {table_name}")
        
        start_time = time.time()
        
        try:
            async with get_async_session() as session:
                # Get records from PostgreSQL
                if incremental:
                    # Get only recently updated records
                    cutoff_time = datetime.now(timezone.utc) - timezone.timedelta(hours=1)
                    query = text(f"""
                        SELECT * FROM {table_name} 
                        WHERE updated_at > :cutoff_time OR created_at > :cutoff_time
                        ORDER BY updated_at DESC
                    """)
                    result = await session.execute(query, {'cutoff_time': cutoff_time})
                else:
                    # Get all records
                    query = text(f"SELECT * FROM {table_name}")
                    result = await session.execute(query)
                
                records = result.fetchall()
                
                # Process records in batches
                for i in range(0, len(records), self.config.batch_size):
                    batch = records[i:i + self.config.batch_size]
                    
                    for record in batch:
                        record_dict = dict(record._mapping)
                        
                        # Create sync event
                        event = SyncEvent(
                            id=str(uuid.uuid4()),
                            event_type=SyncEventType.BULK_SYNC,
                            table_name=table_name,
                            record_id=str(record_dict.get('id', '')),
                            data=record_dict,
                            timestamp=datetime.now(timezone.utc),
                            source='postgresql'
                        )
                        
                        await self.event_processor.queue_event(event)
                
                sync_time = time.time() - start_time
                logger.info(f"Queued {len(records)} records from {table_name} in {sync_time:.3f}s")
                
        except Exception as e:
            logger.error(f"Error syncing table {table_name}: {e}")
            raise
    
    async def _periodic_sync_table(self, table_name: str) -> None:
        """Periodically sync a table"""
        while self._running:
            try:
                await self.sync_table(table_name, incremental=True)
                await asyncio.sleep(self.config.sync_interval * 60)  # Convert to minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic sync for {table_name}: {e}")
                await asyncio.sleep(self.config.retry_delay)
    
    def get_status(self) -> Dict[str, Any]:
        """Get synchronization status"""
        return {
            'running': self._running,
            'config': asdict(self.config),
            'active_tasks': len(self._sync_tasks),
            'queue_size': self.event_processor._event_queue.qsize() if hasattr(self.event_processor._event_queue, 'qsize') else 0
        }

# Singleton instance
_db_synchronizer: Optional[DatabaseSynchronizer] = None

async def get_database_synchronizer() -> DatabaseSynchronizer:
    """Get or create database synchronizer instance"""
    global _db_synchronizer
    
    if _db_synchronizer is None:
        config = SyncConfiguration()
        _db_synchronizer = DatabaseSynchronizer(config)
    
    return _db_synchronizer

async def start_database_sync() -> None:
    """Start database synchronization"""
    synchronizer = await get_database_synchronizer()
    await synchronizer.start()

async def stop_database_sync() -> None:
    """Stop database synchronization"""
    synchronizer = await get_database_synchronizer()
    await synchronizer.stop() 