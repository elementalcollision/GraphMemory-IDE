"""
Backup Orchestrator

Unified backup and recovery orchestrator for GraphMemory-IDE that coordinates:
- PostgreSQL backup and recovery operations
- Redis backup and recovery operations  
- Kuzu graph database backup and recovery operations
- Automated scheduling and monitoring
- Cross-database consistency and validation
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class BackupStrategy(Enum):
    """Backup strategy types"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupPriority(Enum):
    """Backup priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BackupJob:
    """Backup job configuration"""
    job_id: str
    name: str
    description: str
    strategy: BackupStrategy
    priority: BackupPriority
    databases: List[str]  # postgres, redis, kuzu
    schedule_cron: str
    retention_days: int
    enabled: bool = True
    created_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@dataclass
class BackupExecution:
    """Backup execution results"""
    execution_id: str
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    status: str
    databases_backed_up: List[str]
    backup_ids: Dict[str, str]  # database -> backup_id
    total_size_bytes: int
    error_message: Optional[str] = None
    validation_results: Optional[Dict[str, Any]] = None


class BackupOrchestrator:
    """
    Unified backup orchestrator for all database systems
    """
    
    def __init__(self,
                 postgresql_manager=None,
                 redis_manager=None,
                 kuzu_manager=None,
                 backup_jobs_config_path: str = "backups/config/jobs.json",
                 execution_logs_path: str = "backups/logs",
                 metrics_collector=None):
        
        self.postgresql_manager = postgresql_manager
        self.redis_manager = redis_manager
        self.kuzu_manager = kuzu_manager
        self.metrics = metrics_collector
        
        # Configuration paths
        self.jobs_config_path = Path(backup_jobs_config_path)
        self.execution_logs_path = Path(execution_logs_path)
        
        # Ensure directories exist
        self.jobs_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.execution_logs_path.mkdir(parents=True, exist_ok=True)
        
        # Scheduler for automated backups
        self.scheduler = AsyncIOScheduler()
        self.backup_jobs: Dict[str, BackupJob] = {}
        
        # Execution tracking
        self.active_executions: Dict[str, BackupExecution] = {}
    
    async def initialize(self):
        """Initialize the backup orchestrator"""
        try:
            await self._load_backup_jobs()
            await self._schedule_backup_jobs()
            self.scheduler.start()
            logger.info("Backup orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize backup orchestrator: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the backup orchestrator"""
        try:
            self.scheduler.shutdown()
            logger.info("Backup orchestrator shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during backup orchestrator shutdown: {e}")
    
    async def create_backup_job(self, job: BackupJob) -> bool:
        """Create a new backup job"""
        try:
            # Set creation timestamp
            job.created_at = datetime.utcnow()
            
            # Add to jobs dictionary
            self.backup_jobs[job.job_id] = job
            
            # Save to configuration file
            await self._save_backup_jobs()
            
            # Schedule the job if enabled
            if job.enabled:
                await self._schedule_job(job)
            
            logger.info(f"Backup job created: {job.job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup job {job.job_id}: {e}")
            return False
    
    async def execute_backup_job(self, job_id: str) -> BackupExecution:
        """Execute a backup job manually or via scheduler"""
        if job_id not in self.backup_jobs:
            raise ValueError(f"Backup job not found: {job_id}")
        
        job = self.backup_jobs[job_id]
        execution_id = f"{job_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Create execution record
        execution = BackupExecution(
            execution_id=execution_id,
            job_id=job_id,
            started_at=datetime.utcnow(),
            completed_at=None,
            duration_seconds=None,
            status="running",
            databases_backed_up=[],
            backup_ids={},
            total_size_bytes=0
        )
        
        self.active_executions[execution_id] = execution
        
        logger.info(f"Starting backup job execution: {execution_id}")
        
        try:
            # Record execution start metrics
            if self.metrics:
                self.metrics.record_backup_job_started(job_id, job.strategy.value)
            
            backup_results = {}
            total_size = 0
            
            # Execute PostgreSQL backup
            if "postgres" in job.databases and self.postgresql_manager:
                logger.info(f"Executing PostgreSQL backup for job {job_id}")
                try:
                    pg_backup = await self.postgresql_manager.create_base_backup(
                        backup_name=f"{job_id}_postgres_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    )
                    backup_results["postgres"] = pg_backup.backup_id
                    total_size += pg_backup.size_bytes
                    execution.databases_backed_up.append("postgres")
                    
                except Exception as e:
                    logger.error(f"PostgreSQL backup failed for job {job_id}: {e}")
                    execution.error_message = f"PostgreSQL backup failed: {e}"
            
            # Execute Redis backup
            if "redis" in job.databases and self.redis_manager:
                logger.info(f"Executing Redis backup for job {job_id}")
                try:
                    if job.strategy == BackupStrategy.FULL:
                        redis_backup = await self.redis_manager.create_full_backup(
                            backup_name=f"{job_id}_redis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                        )
                    else:
                        redis_backup = await self.redis_manager.create_rdb_backup(
                            backup_name=f"{job_id}_redis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                        )
                    
                    backup_results["redis"] = redis_backup.backup_id
                    total_size += redis_backup.size_bytes
                    execution.databases_backed_up.append("redis")
                    
                except Exception as e:
                    logger.error(f"Redis backup failed for job {job_id}: {e}")
                    if execution.error_message:
                        execution.error_message += f"; Redis backup failed: {e}"
                    else:
                        execution.error_message = f"Redis backup failed: {e}"
            
            # Execute Kuzu backup
            if "kuzu" in job.databases and self.kuzu_manager:
                logger.info(f"Executing Kuzu backup for job {job_id}")
                try:
                    kuzu_backup = await self.kuzu_manager.create_filesystem_backup(
                        backup_name=f"{job_id}_kuzu_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    )
                    backup_results["kuzu"] = kuzu_backup.backup_id
                    total_size += kuzu_backup.size_bytes
                    execution.databases_backed_up.append("kuzu")
                    
                except Exception as e:
                    logger.error(f"Kuzu backup failed for job {job_id}: {e}")
                    if execution.error_message:
                        execution.error_message += f"; Kuzu backup failed: {e}"
                    else:
                        execution.error_message = f"Kuzu backup failed: {e}"
            
            # Update execution results
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            execution.backup_ids = backup_results
            execution.total_size_bytes = total_size
            
            # Determine final status
            if execution.error_message:
                if execution.databases_backed_up:
                    execution.status = "partial_success"
                else:
                    execution.status = "failed"
            else:
                execution.status = "success"
            
            # Validate backups if successful
            if execution.status in ["success", "partial_success"]:
                validation_results = await self._validate_execution_backups(execution)
                execution.validation_results = validation_results
            
            # Update job last run timestamp
            job.last_run = execution.started_at
            await self._save_backup_jobs()
            
            # Save execution log
            await self._save_execution_log(execution)
            
            # Record metrics
            if self.metrics:
                if execution.status == "success":
                    self.metrics.record_backup_job_completed(
                        job_id, 
                        execution.duration_seconds, 
                        total_size
                    )
                else:
                    self.metrics.record_backup_job_failed(job_id, execution.error_message or "Unknown error")
            
            # Remove from active executions
            del self.active_executions[execution_id]
            
            logger.info(f"Backup job execution completed: {execution_id} (status: {execution.status})")
            return execution
            
        except Exception as e:
            # Handle unexpected errors
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            execution.status = "failed"
            execution.error_message = str(e)
            
            # Save error execution log
            await self._save_execution_log(execution)
            
            # Record failure metrics
            if self.metrics:
                self.metrics.record_backup_job_failed(job_id, str(e))
            
            # Remove from active executions
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            logger.error(f"Backup job execution failed: {execution_id}: {e}")
            raise
    
    async def cleanup_old_backups(self) -> Dict[str, List[str]]:
        """Clean up old backups across all database systems"""
        cleanup_results = {}
        
        try:
            # Clean up PostgreSQL backups
            if self.postgresql_manager:
                pg_removed = await self.postgresql_manager.cleanup_old_backups()
                cleanup_results["postgres"] = pg_removed
            
            # Clean up Redis backups
            if self.redis_manager:
                redis_removed = await self.redis_manager.cleanup_old_backups()
                cleanup_results["redis"] = redis_removed
            
            # Clean up Kuzu backups
            if self.kuzu_manager:
                kuzu_removed = await self.kuzu_manager.cleanup_old_backups()
                cleanup_results["kuzu"] = kuzu_removed
            
            logger.info(f"Backup cleanup completed: {cleanup_results}")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return cleanup_results
    
    async def get_backup_status(self) -> Dict[str, Any]:
        """Get comprehensive backup status"""
        status = {
            "jobs": {},
            "active_executions": {},
            "recent_executions": [],
            "system_status": {}
        }
        
        try:
            # Job status
            for job_id, job in self.backup_jobs.items():
                status["jobs"][job_id] = {
                    "name": job.name,
                    "enabled": job.enabled,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "next_run": job.next_run.isoformat() if job.next_run else None,
                    "schedule": job.schedule_cron
                }
            
            # Active executions
            for exec_id, execution in self.active_executions.items():
                status["active_executions"][exec_id] = {
                    "job_id": execution.job_id,
                    "started_at": execution.started_at.isoformat(),
                    "status": execution.status,
                    "databases": execution.databases_backed_up
                }
            
            # Recent executions (last 10)
            recent_logs = await self._get_recent_execution_logs(limit=10)
            status["recent_executions"] = recent_logs
            
            # System status
            status["system_status"] = {
                "postgresql_manager": self.postgresql_manager is not None,
                "redis_manager": self.redis_manager is not None,
                "kuzu_manager": self.kuzu_manager is not None,
                "scheduler_running": self.scheduler.running
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get backup status: {e}")
            return status
    
    async def _load_backup_jobs(self):
        """Load backup job configurations from file"""
        try:
            if self.jobs_config_path.exists():
                async with aiofiles.open(self.jobs_config_path, 'r') as f:
                    jobs_data = json.loads(await f.read())
                    
                    for job_data in jobs_data:
                        job = BackupJob(**job_data)
                        # Convert string dates back to datetime objects
                        if job.created_at:
                            job.created_at = datetime.fromisoformat(job.created_at)
                        if job.last_run:
                            job.last_run = datetime.fromisoformat(job.last_run)
                        
                        self.backup_jobs[job.job_id] = job
                
                logger.info(f"Loaded {len(self.backup_jobs)} backup jobs")
            else:
                logger.info("No existing backup jobs configuration found")
                
        except Exception as e:
            logger.error(f"Failed to load backup jobs: {e}")
    
    async def _save_backup_jobs(self):
        """Save backup job configurations to file"""
        try:
            jobs_data = []
            for job in self.backup_jobs.values():
                job_dict = asdict(job)
                # Convert datetime objects to ISO strings
                if job_dict['created_at']:
                    job_dict['created_at'] = job.created_at.isoformat()
                if job_dict['last_run']:
                    job_dict['last_run'] = job.last_run.isoformat()
                if job_dict['next_run']:
                    job_dict['next_run'] = job.next_run.isoformat()
                
                # Convert enums to values
                job_dict['strategy'] = job.strategy.value
                job_dict['priority'] = job.priority.value
                
                jobs_data.append(job_dict)
            
            async with aiofiles.open(self.jobs_config_path, 'w') as f:
                await f.write(json.dumps(jobs_data, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save backup jobs: {e}")
    
    async def _schedule_backup_jobs(self):
        """Schedule all enabled backup jobs"""
        for job in self.backup_jobs.values():
            if job.enabled:
                await self._schedule_job(job)
    
    async def _schedule_job(self, job: BackupJob):
        """Schedule a single backup job"""
        try:
            trigger = CronTrigger.from_crontab(job.schedule_cron)
            
            self.scheduler.add_job(
                func=self.execute_backup_job,
                trigger=trigger,
                args=[job.job_id],
                id=job.job_id,
                name=job.name,
                replace_existing=True
            )
            
            # Update next run time
            next_run = self.scheduler.get_job(job.job_id).next_run_time
            job.next_run = next_run.replace(tzinfo=None) if next_run else None
            
            logger.info(f"Scheduled backup job: {job.job_id} ({job.schedule_cron})")
            
        except Exception as e:
            logger.error(f"Failed to schedule backup job {job.job_id}: {e}")
    
    async def _validate_execution_backups(self, execution: BackupExecution) -> Dict[str, Any]:
        """Validate all backups from an execution"""
        validation_results = {}
        
        try:
            # Validate PostgreSQL backup
            if "postgres" in execution.backup_ids and self.postgresql_manager:
                pg_backup_id = execution.backup_ids["postgres"]
                pg_validation = await self.postgresql_manager.validate_backup(pg_backup_id)
                validation_results["postgres"] = pg_validation
            
            # Validate Redis backup
            if "redis" in execution.backup_ids and self.redis_manager:
                redis_backup_id = execution.backup_ids["redis"]
                redis_validation = await self.redis_manager.validate_backup(redis_backup_id)
                validation_results["redis"] = redis_validation
            
            # Validate Kuzu backup
            if "kuzu" in execution.backup_ids and self.kuzu_manager:
                kuzu_backup_id = execution.backup_ids["kuzu"]
                kuzu_validation = await self.kuzu_manager.validate_backup(kuzu_backup_id)
                validation_results["kuzu"] = kuzu_validation
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            return {"error": str(e)}
    
    async def _save_execution_log(self, execution: BackupExecution):
        """Save execution log to file"""
        try:
            log_file = self.execution_logs_path / f"{execution.execution_id}.json"
            
            # Convert execution to dictionary
            execution_dict = asdict(execution)
            execution_dict['started_at'] = execution.started_at.isoformat()
            if execution.completed_at:
                execution_dict['completed_at'] = execution.completed_at.isoformat()
            
            async with aiofiles.open(log_file, 'w') as f:
                await f.write(json.dumps(execution_dict, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save execution log: {e}")
    
    async def _get_recent_execution_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution logs"""
        try:
            logs = []
            log_files = sorted(self.execution_logs_path.glob("*.json"), reverse=True)
            
            for log_file in log_files[:limit]:
                async with aiofiles.open(log_file, 'r') as f:
                    log_data = json.loads(await f.read())
                    logs.append(log_data)
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get recent execution logs: {e}")
            return [] 