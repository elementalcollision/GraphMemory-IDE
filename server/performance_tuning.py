"""
Database Performance Tuning and Optimization for GraphMemory-IDE.

This module provides automated performance analysis and optimization
for PostgreSQL databases in production environments.
"""

import asyncio
import logging
import psutil
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, inspect
from dataclasses import dataclass, asdict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    slow_queries: int
    cache_hit_ratio: float
    index_usage: float
    table_bloat: float
    recommendations: List[str]


@dataclass
class OptimizationSettings:
    """Database optimization settings"""
    shared_buffers: str
    effective_cache_size: str
    work_mem: str
    maintenance_work_mem: str
    max_connections: int
    checkpoint_completion_target: float
    wal_buffers: str
    random_page_cost: float
    effective_io_concurrency: int


class DatabaseOptimizer:
    """Database performance optimizer and analyzer"""
    
    def __init__(self, database_url: str) -> None:
        """Initialize optimizer with database connection"""
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def close(self) -> None:
        """Close database connections"""
        await self.engine.dispose()

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics"""
        metrics = {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.0
        }
        
        logger.info(f"System metrics: CPU: {metrics['cpu_usage']:.1f}%, "
                   f"Memory: {metrics['memory_usage']:.1f}%, "
                   f"Disk: {metrics['disk_usage']:.1f}%")
        
        return metrics

    async def get_database_metrics(self) -> Dict[str, Any]:
        """Get PostgreSQL database performance metrics"""
        async with self.async_session() as session:
            metrics = {}
            
            # Active connections
            result = await session.execute(text("""
                SELECT COUNT(*) as active_connections
                FROM pg_stat_activity 
                WHERE state = 'active'
            """))
            metrics['active_connections'] = result.scalar()
            
            # Cache hit ratio
            result = await session.execute(text("""
                SELECT 
                    ROUND(
                        100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2
                    ) as cache_hit_ratio
                FROM pg_stat_database 
                WHERE datname = current_database()
            """))
            metrics['cache_hit_ratio'] = result.scalar() or 0.0
            
            # Index usage ratio
            result = await session.execute(text("""
                SELECT 
                    ROUND(
                        100.0 * sum(idx_scan) / (sum(seq_scan) + sum(idx_scan)), 2
                    ) as index_usage_ratio
                FROM pg_stat_user_tables
                WHERE seq_scan + idx_scan > 0
            """))
            metrics['index_usage_ratio'] = result.scalar() or 0.0
            
            # Slow queries (queries taking more than 1 second)
            result = await session.execute(text("""
                SELECT COUNT(*) as slow_queries
                FROM pg_stat_statements 
                WHERE mean_exec_time > 1000
            """))
            metrics['slow_queries'] = result.scalar() or 0
            
            # Database size
            result = await session.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
            """))
            metrics['database_size'] = result.scalar()
            
            # Table bloat estimate
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    ROUND(
                        CASE WHEN otta=0 THEN 0.0 
                        ELSE sml.relpages/otta::numeric 
                        END, 1
                    ) AS bloat_ratio
                FROM (
                    SELECT 
                        schemaname, tablename, cc.reltuples, cc.relpages, 
                        CEIL((cc.reltuples*((datahdr+ma-
                        (CASE WHEN datahdr%ma=0 THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)) AS otta
                    FROM (
                        SELECT 
                            ma,bs,schemaname,tablename,
                            (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
                            (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
                        FROM (
                            SELECT 
                                schemaname, tablename, hdr, ma, bs,
                                SUM((1-null_frac)*avg_width) AS datawidth,
                                MAX(null_frac) AS maxfracsum,
                                hdr+(
                                    SELECT 1+count(*)/8
                                    FROM pg_stats s2
                                    WHERE null_frac<>0 AND s2.schemaname = s.schemaname AND s2.tablename = s.tablename
                                ) AS nullhdr
                            FROM pg_stats s, (
                                SELECT 
                                    (SELECT current_setting('block_size')::numeric) AS bs,
                                    CASE WHEN substring(v,12,3) IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr,
                                    CASE WHEN v ~ 'mingw32' THEN 8 ELSE 4 END AS ma
                                FROM (SELECT version() AS v) AS foo
                            ) AS constants
                            WHERE schemaname NOT IN ('information_schema','pg_catalog')
                            GROUP BY 1,2,3,4,5
                        ) AS foo
                    ) AS rs
                    JOIN pg_class cc ON cc.relname = rs.tablename
                    JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname = rs.schemaname AND nn.nspname <> 'information_schema'
                ) AS sml
                WHERE sml.relpages > 0
                ORDER BY bloat_ratio DESC
                LIMIT 10
            """))
            bloat_data = result.fetchall()
            metrics['table_bloat'] = [
                {'schema': row[0], 'table': row[1], 'bloat_ratio': float(row[2])}
                for row in bloat_data
            ]
            
            # Connection statistics
            result = await session.execute(text("""
                SELECT 
                    state,
                    COUNT(*) as count
                FROM pg_stat_activity 
                GROUP BY state
            """))
            connection_stats = {row[0]: row[1] for row in result.fetchall()}
            metrics['connection_stats'] = connection_stats
            
            # Top slow queries
            result = await session.execute(text("""
                SELECT 
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    rows
                FROM pg_stat_statements 
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """))
            slow_queries = [
                {
                    'query': row[0][:100] + '...' if len(row[0]) > 100 else row[0],
                    'calls': row[1],
                    'total_time': float(row[2]),
                    'mean_time': float(row[3]),
                    'rows': row[4]
                }
                for row in result.fetchall()
            ]
            metrics['slow_queries_detail'] = slow_queries
            
        return metrics

    async def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze query performance and identify optimization opportunities"""
        async with self.async_session() as session:
            analysis = {}
            
            # Missing indexes analysis
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    seq_scan,
                    seq_tup_read,
                    seq_tup_read / seq_scan as avg_seq_read
                FROM pg_stat_user_tables 
                WHERE seq_scan > 100 
                AND seq_tup_read / seq_scan > 1000
                ORDER BY seq_tup_read DESC
                LIMIT 10
            """))
            missing_indexes = [
                {
                    'schema': row[0],
                    'table': row[1],
                    'seq_scans': row[2],
                    'seq_reads': row[3],
                    'avg_read_per_scan': float(row[4])
                }
                for row in result.fetchall()
            ]
            analysis['missing_indexes'] = missing_indexes
            
            # Unused indexes
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size
                FROM pg_stat_user_indexes 
                WHERE idx_scan = 0 
                AND schemaname NOT IN ('information_schema', 'pg_catalog')
                ORDER BY pg_relation_size(indexrelid) DESC
                LIMIT 10
            """))
            unused_indexes = [
                {
                    'schema': row[0],
                    'table': row[1],
                    'index': row[2],
                    'scans': row[3],
                    'size': row[4]
                }
                for row in result.fetchall()
            ]
            analysis['unused_indexes'] = unused_indexes
            
            # Lock analysis
            result = await session.execute(text("""
                SELECT 
                    mode,
                    COUNT(*) as count
                FROM pg_locks 
                WHERE granted = true
                GROUP BY mode
                ORDER BY count DESC
            """))
            lock_stats = [{"mode": row[0], "count": row[1]} for row in result.fetchall()]
            analysis['lock_statistics'] = lock_stats
            
        return analysis

    def generate_recommendations(self, system_metrics: Dict[str, float], 
                               db_metrics: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Memory recommendations
        if system_metrics['memory_usage'] > 80:
            recommendations.append(
                "High memory usage detected. Consider reducing shared_buffers or work_mem"
            )
        elif system_metrics['memory_usage'] < 50:
            recommendations.append(
                "Low memory usage. Consider increasing shared_buffers for better caching"
            )
        
        # Cache hit ratio recommendations
        cache_hit_ratio = db_metrics.get('cache_hit_ratio', 0)
        if cache_hit_ratio < 95:
            recommendations.append(
                f"Cache hit ratio is {cache_hit_ratio}%. Consider increasing shared_buffers"
            )
        
        # Index usage recommendations
        index_usage = db_metrics.get('index_usage_ratio', 0)
        if index_usage < 80:
            recommendations.append(
                f"Index usage is {index_usage}%. Review query patterns and add missing indexes"
            )
        
        # Connection recommendations
        active_connections = db_metrics.get('active_connections', 0)
        if active_connections > 100:
            recommendations.append(
                "High number of active connections. Consider connection pooling"
            )
        
        # Slow queries recommendations
        slow_queries = db_metrics.get('slow_queries', 0)
        if slow_queries > 10:
            recommendations.append(
                f"Found {slow_queries} slow queries. Review and optimize query performance"
            )
        
        # Table bloat recommendations
        table_bloat = db_metrics.get('table_bloat', [])
        high_bloat_tables = [t for t in table_bloat if t['bloat_ratio'] > 2.0]
        if high_bloat_tables:
            recommendations.append(
                f"High table bloat detected in {len(high_bloat_tables)} tables. Consider VACUUM FULL"
            )
        
        # CPU recommendations
        if system_metrics['cpu_usage'] > 80:
            recommendations.append(
                "High CPU usage. Review query performance and consider query optimization"
            )
        
        return recommendations

    def calculate_optimal_settings(self, system_metrics: Dict[str, float]) -> OptimizationSettings:
        """Calculate optimal PostgreSQL settings based on system resources"""
        # Get total system memory in GB
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Calculate optimal settings based on system resources
        # These are conservative estimates - adjust based on your workload
        
        shared_buffers_gb = min(total_memory_gb * 0.25, 8)  # 25% of RAM, max 8GB
        effective_cache_size_gb = total_memory_gb * 0.75    # 75% of RAM
        work_mem_mb = max(4, int(total_memory_gb * 1024 / 200))  # Total RAM / max_connections / 4
        maintenance_work_mem_mb = min(2048, int(total_memory_gb * 1024 * 0.1))  # 10% of RAM, max 2GB
        
        # Connection limits based on memory
        max_connections = min(200, max(100, int(total_memory_gb * 50)))
        
        # I/O settings
        cpu_count = psutil.cpu_count()
        effective_io_concurrency = (cpu_count or 4) * 2
        
        return OptimizationSettings(
            shared_buffers=f"{shared_buffers_gb:.1f}GB",
            effective_cache_size=f"{effective_cache_size_gb:.1f}GB",
            work_mem=f"{work_mem_mb}MB",
            maintenance_work_mem=f"{maintenance_work_mem_mb}MB",
            max_connections=max_connections,
            checkpoint_completion_target=0.9,
            wal_buffers="16MB",
            random_page_cost=1.1,  # Assume SSD storage
            effective_io_concurrency=effective_io_concurrency
        )

    async def generate_postgresql_config(self, settings: OptimizationSettings) -> str:
        """Generate optimized PostgreSQL configuration"""
        config = f"""
# GraphMemory-IDE Optimized PostgreSQL Configuration
# Generated on {datetime.now().isoformat()}

# Memory Configuration
shared_buffers = {settings.shared_buffers}
effective_cache_size = {settings.effective_cache_size}
work_mem = {settings.work_mem}
maintenance_work_mem = {settings.maintenance_work_mem}

# Connection Configuration
max_connections = {settings.max_connections}
shared_preload_libraries = 'pg_stat_statements'

# Checkpoint Configuration
checkpoint_completion_target = {settings.checkpoint_completion_target}
wal_buffers = {settings.wal_buffers}

# Planner Configuration
random_page_cost = {settings.random_page_cost}
effective_io_concurrency = {settings.effective_io_concurrency}
default_statistics_target = 100

# Logging Configuration
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# Performance Monitoring
track_activities = on
track_counts = on
track_io_timing = on
track_functions = all
"""
        return config

    async def run_vacuum_analyze(self) -> Dict[str, Any]:
        """Run VACUUM ANALYZE on all tables"""
        async with self.async_session() as session:
            logger.info("Running VACUUM ANALYZE...")
            
            # Get list of user tables
            result = await session.execute(text("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
            """))
            tables = result.fetchall()
            
            results: Dict[str, Any] = {
                'tables_analyzed': len(tables),
                'start_time': datetime.now().isoformat(),
                'errors': []
            }
            
            for schema, table in tables:
                try:
                    await session.execute(text(f'VACUUM ANALYZE "{schema}"."{table}"'))
                    logger.info(f"Analyzed {schema}.{table}")
                except Exception as e:
                    error_msg = f"Error analyzing {schema}.{table}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            await session.commit()
            results['end_time'] = datetime.now().isoformat()
            
        return results

    async def create_missing_indexes(self, analysis: Dict[str, Any], dry_run: bool = True) -> List[str]:
        """Create indexes for tables with high sequential scan ratios"""
        missing_indexes = analysis.get('missing_indexes', [])
        index_statements = []
        
        for table_info in missing_indexes:
            if table_info['avg_read_per_scan'] > 1000:  # Only for high-impact tables
                schema = table_info['schema']
                table = table_info['table']
                
                # This is a simplified example - in practice, you'd need to analyze
                # query patterns to determine the best columns to index
                index_name = f"idx_{table}_performance_auto"
                index_statement = f'CREATE INDEX CONCURRENTLY "{index_name}" ON "{schema}"."{table}" (id);'
                index_statements.append(index_statement)
                
                if not dry_run:
                    try:
                        async with self.async_session() as session:
                            await session.execute(text(index_statement))
                            await session.commit()
                            logger.info(f"Created index: {index_name}")
                    except Exception as e:
                        logger.error(f"Failed to create index {index_name}: {e}")
        
        return index_statements

    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        logger.info("Generating performance report...")
        
        # Collect all metrics
        system_metrics = await self.get_system_metrics()
        db_metrics = await self.get_database_metrics()
        query_analysis = await self.analyze_query_performance()
        recommendations = self.generate_recommendations(system_metrics, db_metrics)
        optimal_settings = self.calculate_optimal_settings(system_metrics)
        
        # Create performance metrics object
        performance_metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_usage=system_metrics['cpu_usage'],
            memory_usage=system_metrics['memory_usage'],
            disk_usage=system_metrics['disk_usage'],
            active_connections=db_metrics['active_connections'],
            slow_queries=db_metrics['slow_queries'],
            cache_hit_ratio=db_metrics['cache_hit_ratio'],
            index_usage=db_metrics.get('index_usage_ratio', 0),
            table_bloat=max([t['bloat_ratio'] for t in db_metrics.get('table_bloat', [{'bloat_ratio': 0}])]),
            recommendations=recommendations
        )
        
        # Compile full report
        report = {
            'performance_metrics': asdict(performance_metrics),
            'system_metrics': system_metrics,
            'database_metrics': db_metrics,
            'query_analysis': query_analysis,
            'optimal_settings': asdict(optimal_settings),
            'postgresql_config': await self.generate_postgresql_config(optimal_settings),
            'generated_at': datetime.now().isoformat()
        }
        
        return report

    async def save_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Save performance report to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Performance report saved to: {filename}")
        return filename


async def main() -> None:
    """Main optimization function"""
    # Default database URL - should be from environment
    database_url = os.getenv(
        'DATABASE_URL', 
        'postgresql+asyncpg://graphmemory:graphmemory@localhost:5432/graphmemory_dev'
    )
    
    optimizer = DatabaseOptimizer(database_url)
    
    try:
        # Generate performance report
        report = await optimizer.generate_performance_report()
        
        # Save report
        report_file = await optimizer.save_report(report)
        
        # Print summary
        metrics = report['performance_metrics']
        print(f"\n🚀 GraphMemory-IDE Database Performance Report")
        print(f"===============================================")
        print(f"Generated: {metrics['timestamp']}")
        print(f"CPU Usage: {metrics['cpu_usage']:.1f}%")
        print(f"Memory Usage: {metrics['memory_usage']:.1f}%")
        print(f"Cache Hit Ratio: {metrics['cache_hit_ratio']:.1f}%")
        print(f"Index Usage: {metrics['index_usage']:.1f}%")
        print(f"Active Connections: {metrics['active_connections']}")
        print(f"Slow Queries: {metrics['slow_queries']}")
        print(f"\n📋 Recommendations:")
        for i, rec in enumerate(metrics['recommendations'], 1):
            print(f"{i}. {rec}")
        
        print(f"\n📄 Full report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        raise
    finally:
        await optimizer.close()


if __name__ == "__main__":
    asyncio.run(main()) 