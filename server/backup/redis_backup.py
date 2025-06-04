"""
Redis Backup and Recovery Manager

Implements automated backup strategies for Redis including:
- RDB snapshots (SAVE/BGSAVE operations)
- AOF (Append-Only File) management
- Backup validation and integrity checking
- Integration with monitoring and alerting systems
"""

import os
import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis
import aiofiles

logger = logging.getLogger(__name__)


class RedisBackupType(Enum):
    """Types of Redis backups"""
    RDB_SNAPSHOT = "rdb_snapshot"
    AOF_REWRITE = "aof_rewrite"
    FULL_BACKUP = "full_backup"


class RedisBackupStatus(Enum):
    """Redis backup operation status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RedisBackupMetadata:
    """Metadata for Redis backup operations"""
    backup_id: str
    backup_type: RedisBackupType
    timestamp: datetime
    redis_instance: str
    size_bytes: int
    duration_seconds: float
    status: RedisBackupStatus
    memory_usage_mb: Optional[float] = None
    keys_count: Optional[int] = None
    storage_location: Optional[str] = None
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    aof_size_bytes: Optional[int] = None
    rdb_size_bytes: Optional[int] = None


class RedisBackupManager:
    """
    Comprehensive Redis backup and recovery manager
    """
    
    def __init__(self, 
                 redis_url: str,
                 backup_storage_path: str,
                 metrics_collector=None) -> None:
        self.redis_url = redis_url
        self.backup_storage_path = Path(backup_storage_path)
        self.metrics = metrics_collector
        
        # Ensure storage directory exists
        self.backup_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Parse Redis connection details
        self.redis_host = self._extract_host()
        self.redis_port = self._extract_port()
        self.redis_db = self._extract_db()
    
    async def create_rdb_backup(self, 
                              backup_name: Optional[str] = None,
                              use_bgsave: bool = True) -> RedisBackupMetadata:
        """
        Create RDB snapshot backup
        """
        start_time = datetime.utcnow()
        backup_id = backup_name or f"rdb_backup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting RDB backup: {backup_id}")
        
        redis_client = None
        try:
            # Record backup start metrics
            if self.metrics:
                self.metrics.record_backup_started(RedisBackupType.RDB_SNAPSHOT.value)
            
            # Connect to Redis
            redis_client = redis.from_url(self.redis_url)
            await redis_client.ping()
            
            # Get Redis info before backup
            info = await redis_client.info()
            memory_usage = info.get('used_memory', 0) / (1024 * 1024)  # Convert to MB
            
            # Count keys across all databases
            keys_count = 0
            for db_num in range(16):  # Redis default has 16 databases
                await redis_client.select(db_num)
                db_size = await redis_client.dbsize()
                keys_count += db_size
            
            # Switch back to default database
            await redis_client.select(self.redis_db)
            
            # Trigger RDB save
            if use_bgsave:
                # Use background save (non-blocking)
                result = await redis_client.bgsave()
                if not result:
                    raise RuntimeError("BGSAVE command failed")
                
                # Wait for background save to complete
                while True:
                    info = await redis_client.info('persistence')
                    if info.get('rdb_bgsave_in_progress', 0) == 0:
                        break
                    await asyncio.sleep(1)
                    
                # Check if save was successful
                if info.get('rdb_last_bgsave_status') != 'ok':
                    raise RuntimeError("Background save failed")
            else:
                # Use synchronous save (blocking)
                await redis_client.save()
            
            # Get RDB file path from Redis config
            config = await redis_client.config_get('dir')
            rdb_dir = config.get('dir', '/var/lib/redis')
            
            config = await redis_client.config_get('dbfilename')
            rdb_filename = config.get('dbfilename', 'dump.rdb')
            
            rdb_source_path = Path(rdb_dir) / rdb_filename
            
            # Copy RDB file to backup location
            backup_dir = self.backup_storage_path / backup_id
            backup_dir.mkdir(exist_ok=True)
            
            backup_rdb_path = backup_dir / f"{backup_id}.rdb"
            
            # Copy RDB file
            if rdb_source_path.exists():
                await self._copy_file(rdb_source_path, backup_rdb_path)
            else:
                raise FileNotFoundError(f"RDB file not found: {rdb_source_path}")
            
            # Calculate backup size and checksum
            backup_size = backup_rdb_path.stat().st_size
            checksum = await self._calculate_checksum(backup_rdb_path)
            
            # Create metadata
            duration = (datetime.utcnow() - start_time).total_seconds()
            metadata = RedisBackupMetadata(
                backup_id=backup_id,
                backup_type=RedisBackupType.RDB_SNAPSHOT,
                timestamp=start_time,
                redis_instance=f"{self.redis_host}:{self.redis_port}",
                size_bytes=backup_size,
                duration_seconds=duration,
                status=RedisBackupStatus.SUCCESS,
                memory_usage_mb=memory_usage,
                keys_count=keys_count,
                storage_location=str(backup_dir),
                checksum=checksum,
                rdb_size_bytes=backup_size
            )
            
            # Save metadata
            await self._save_backup_metadata(metadata)
            
            # Record success metrics
            if self.metrics:
                self.metrics.record_backup_completed(
                    RedisBackupType.RDB_SNAPSHOT.value,
                    duration,
                    backup_size
                )
            
            logger.info(f"RDB backup completed successfully: {backup_id}")
            return metadata
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            # Record failure metrics
            if self.metrics:
                self.metrics.record_backup_failed(RedisBackupType.RDB_SNAPSHOT.value, error_msg)
            
            # Create failure metadata
            metadata = RedisBackupMetadata(
                backup_id=backup_id,
                backup_type=RedisBackupType.RDB_SNAPSHOT,
                timestamp=start_time,
                redis_instance=f"{self.redis_host}:{self.redis_port}",
                size_bytes=0,
                duration_seconds=duration,
                status=RedisBackupStatus.FAILED,
                error_message=error_msg
            )
            
            await self._save_backup_metadata(metadata)
            raise
            
        finally:
            if redis_client:
                await redis_client.close()
    
    async def backup_aof(self, backup_name: Optional[str] = None) -> RedisBackupMetadata:
        """
        Backup AOF (Append-Only File)
        """
        start_time = datetime.utcnow()
        backup_id = backup_name or f"aof_backup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting AOF backup: {backup_id}")
        
        redis_client = None
        try:
            # Record backup start metrics
            if self.metrics:
                self.metrics.record_backup_started(RedisBackupType.AOF_REWRITE.value)
            
            # Connect to Redis
            redis_client = redis.from_url(self.redis_url)
            await redis_client.ping()
            
            # Trigger AOF rewrite
            result = await redis_client.bgrewriteaof()
            if not result:
                raise RuntimeError("BGREWRITEAOF command failed")
            
            # Wait for AOF rewrite to complete
            while True:
                info = await redis_client.info('persistence')
                if info.get('aof_rewrite_in_progress', 0) == 0:
                    break
                await asyncio.sleep(1)
            
            # Check if rewrite was successful
            if info.get('aof_last_rewrite_status') != 'ok':
                raise RuntimeError("AOF rewrite failed")
            
            # Get AOF file path from Redis config
            config = await redis_client.config_get('dir')
            aof_dir = config.get('dir', '/var/lib/redis')
            
            config = await redis_client.config_get('appendfilename')
            aof_filename = config.get('appendfilename', 'appendonly.aof')
            
            aof_source_path = Path(aof_dir) / aof_filename
            
            # Copy AOF file to backup location
            backup_dir = self.backup_storage_path / backup_id
            backup_dir.mkdir(exist_ok=True)
            
            backup_aof_path = backup_dir / f"{backup_id}.aof"
            
            # Copy AOF file
            if aof_source_path.exists():
                await self._copy_file(aof_source_path, backup_aof_path)
            else:
                raise FileNotFoundError(f"AOF file not found: {aof_source_path}")
            
            # Calculate backup size and checksum
            backup_size = backup_aof_path.stat().st_size
            checksum = await self._calculate_checksum(backup_aof_path)
            
            # Get Redis stats
            info = await redis_client.info()
            memory_usage = info.get('used_memory', 0) / (1024 * 1024)
            
            # Create metadata
            duration = (datetime.utcnow() - start_time).total_seconds()
            metadata = RedisBackupMetadata(
                backup_id=backup_id,
                backup_type=RedisBackupType.AOF_REWRITE,
                timestamp=start_time,
                redis_instance=f"{self.redis_host}:{self.redis_port}",
                size_bytes=backup_size,
                duration_seconds=duration,
                status=RedisBackupStatus.SUCCESS,
                memory_usage_mb=memory_usage,
                storage_location=str(backup_dir),
                checksum=checksum,
                aof_size_bytes=backup_size
            )
            
            # Save metadata
            await self._save_backup_metadata(metadata)
            
            # Record success metrics
            if self.metrics:
                self.metrics.record_backup_completed(
                    RedisBackupType.AOF_REWRITE.value,
                    duration,
                    backup_size
                )
            
            logger.info(f"AOF backup completed successfully: {backup_id}")
            return metadata
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            # Record failure metrics
            if self.metrics:
                self.metrics.record_backup_failed(RedisBackupType.AOF_REWRITE.value, error_msg)
            
            # Create failure metadata
            metadata = RedisBackupMetadata(
                backup_id=backup_id,
                backup_type=RedisBackupType.AOF_REWRITE,
                timestamp=start_time,
                redis_instance=f"{self.redis_host}:{self.redis_port}",
                size_bytes=0,
                duration_seconds=duration,
                status=RedisBackupStatus.FAILED,
                error_message=error_msg
            )
            
            await self._save_backup_metadata(metadata)
            raise
            
        finally:
            if redis_client:
                await redis_client.close()
    
    async def create_full_backup(self, backup_name: Optional[str] = None) -> RedisBackupMetadata:
        """
        Create a full backup including both RDB and AOF
        """
        start_time = datetime.utcnow()
        backup_id = backup_name or f"full_backup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting full backup: {backup_id}")
        
        try:
            # Create RDB backup
            rdb_backup = await self.create_rdb_backup(f"{backup_id}_rdb")
            
            # Create AOF backup
            aof_backup = await self.create_aof_backup(f"{backup_id}_aof")
            
            # Combine backups into single full backup
            full_backup_dir = self.backup_storage_path / backup_id
            full_backup_dir.mkdir(exist_ok=True)
            
            # Copy RDB and AOF files to full backup directory
            rdb_source = Path(rdb_backup.storage_location) / f"{rdb_backup.backup_id}.rdb"
            aof_source = Path(aof_backup.storage_location) / f"{aof_backup.backup_id}.aof"
            
            await self._copy_file(rdb_source, full_backup_dir / f"{backup_id}.rdb")
            await self._copy_file(aof_source, full_backup_dir / f"{backup_id}.aof")
            
            # Calculate total size
            total_size = (rdb_backup.size_bytes + aof_backup.size_bytes)
            
            # Create combined metadata
            duration = (datetime.utcnow() - start_time).total_seconds()
            metadata = RedisBackupMetadata(
                backup_id=backup_id,
                backup_type=RedisBackupType.FULL_BACKUP,
                timestamp=start_time,
                redis_instance=f"{self.redis_host}:{self.redis_port}",
                size_bytes=total_size,
                duration_seconds=duration,
                status=RedisBackupStatus.SUCCESS,
                memory_usage_mb=rdb_backup.memory_usage_mb,
                keys_count=rdb_backup.keys_count,
                storage_location=str(full_backup_dir),
                rdb_size_bytes=rdb_backup.size_bytes,
                aof_size_bytes=aof_backup.size_bytes
            )
            
            # Save metadata
            await self._save_backup_metadata(metadata)
            
            logger.info(f"Full backup completed successfully: {backup_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Full backup failed: {e}")
            raise
    
    async def restore_from_rdb(self, backup_id: str, target_redis_url: Optional[str] = None) -> bool:
        """
        Restore Redis from RDB backup
        """
        logger.info(f"Starting RDB restore from backup: {backup_id}")
        
        try:
            backup_dir = self.backup_storage_path / backup_id
            rdb_file = backup_dir / f"{backup_id}.rdb"
            
            if not rdb_file.exists():
                raise FileNotFoundError(f"RDB backup file not found: {rdb_file}")
            
            # Connect to target Redis instance
            redis_url = target_redis_url or self.redis_url
            redis_client = redis.from_url(redis_url)
            
            # Flush current data (WARNING: This will delete all data)
            await redis_client.flushall()
            
            # Stop Redis to replace RDB file
            # This requires Redis to be configured for file-based restoration
            logger.warning("Manual RDB restoration requires Redis restart with backup file")
            logger.info(f"Copy {rdb_file} to Redis data directory and restart Redis")
            
            await redis_client.close()
            return True
            
        except Exception as e:
            logger.error(f"RDB restore failed: {e}")
            return False
    
    async def validate_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Validate backup integrity and consistency
        """
        logger.info(f"Validating backup: {backup_id}")
        
        validation_results: Dict[str, Any] = {
            "backup_id": backup_id,
            "is_valid": True,
            "checks": {},
            "errors": []
        }
        
        try:
            backup_dir = self.backup_storage_path / backup_id
            
            # Check if backup exists
            if not backup_dir.exists():
                validation_results["is_valid"] = False
                validation_results["errors"].append("Backup directory not found")
                return validation_results
            
            # Load metadata
            metadata_file = backup_dir / "metadata.json"
            if not metadata_file.exists():
                validation_results["checks"]["metadata"] = "FAIL"
                validation_results["errors"].append("Metadata file missing")
                validation_results["is_valid"] = False
            else:
                validation_results["checks"]["metadata"] = "PASS"
            
            # Check RDB file if it exists
            rdb_file = backup_dir / f"{backup_id}.rdb"
            if rdb_file.exists():
                # Verify file size
                actual_size = rdb_file.stat().st_size
                if actual_size > 0:
                    validation_results["checks"]["rdb_file_size"] = "PASS"
                else:
                    validation_results["checks"]["rdb_file_size"] = "FAIL"
                    validation_results["errors"].append("RDB file is empty")
                    validation_results["is_valid"] = False
                
                # Verify checksum if available
                if metadata_file.exists():
                    async with aiofiles.open(metadata_file, 'r') as f:
                        metadata = json.loads(await f.read())
                        stored_checksum = metadata.get('checksum')
                        
                        if stored_checksum:
                            current_checksum = await self._calculate_checksum(rdb_file)
                            if stored_checksum == current_checksum:
                                validation_results["checks"]["rdb_checksum"] = "PASS"
                            else:
                                validation_results["checks"]["rdb_checksum"] = "FAIL"
                                validation_results["errors"].append("RDB checksum mismatch")
                                validation_results["is_valid"] = False
            
            # Check AOF file if it exists
            aof_file = backup_dir / f"{backup_id}.aof"
            if aof_file.exists():
                actual_size = aof_file.stat().st_size
                if actual_size > 0:
                    validation_results["checks"]["aof_file_size"] = "PASS"
                else:
                    validation_results["checks"]["aof_file_size"] = "FAIL"
                    validation_results["errors"].append("AOF file is empty")
                    validation_results["is_valid"] = False
            
            logger.info(f"Backup validation completed: {backup_id}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            validation_results["is_valid"] = False
            validation_results["errors"].append(str(e))
            return validation_results
    
    async def cleanup_old_backups(self, retention_days: int = 7) -> List[str]:
        """
        Clean up backups older than retention period
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        removed_backups = []
        
        try:
            for backup_dir in self.backup_storage_path.iterdir():
                if not backup_dir.is_dir():
                    continue
                
                metadata_file = backup_dir / "metadata.json"
                if metadata_file.exists():
                    async with aiofiles.open(metadata_file, 'r') as f:
                        metadata = json.loads(await f.read())
                        backup_time = datetime.fromisoformat(metadata['timestamp'])
                        
                        if backup_time < cutoff_date:
                            # Remove backup directory
                            import shutil
                            shutil.rmtree(backup_dir)
                            removed_backups.append(backup_dir.name)
                            logger.info(f"Removed old backup: {backup_dir.name}")
            
            if self.metrics:
                self.metrics.record_backup_cleanup(len(removed_backups))
            
            return removed_backups
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return removed_backups
    
    def _extract_host(self) -> str:
        """Extract Redis host from URL"""
        try:
            if '://' in self.redis_url:
                # redis://host:port/db format
                parts = self.redis_url.split('://')[1].split('/')
                host_port = parts[0].split('@')[-1]  # Remove auth if present
                return host_port.split(':')[0]
            return 'localhost'
        except:
            return 'localhost'
    
    def _extract_port(self) -> int:
        """Extract Redis port from URL"""
        try:
            if '://' in self.redis_url:
                parts = self.redis_url.split('://')[1].split('/')
                host_port = parts[0].split('@')[-1]  # Remove auth if present
                if ':' in host_port:
                    return int(host_port.split(':')[1])
            return 6379
        except:
            return 6379
    
    def _extract_db(self) -> int:
        """Extract Redis database number from URL"""
        try:
            if '://' in self.redis_url:
                parts = self.redis_url.split('/')
                if len(parts) > 3:
                    return int(parts[-1])
            return 0
        except:
            return 0
    
    async def _copy_file(self, source: Path, destination: Path) -> None:
        """Copy file asynchronously"""
        async with aiofiles.open(source, 'rb') as src:
            async with aiofiles.open(destination, 'wb') as dst:
                while True:
                    chunk = await src.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    await dst.write(chunk)
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(8192)
                if not chunk:
                    break
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _save_backup_metadata(self, metadata: RedisBackupMetadata) -> None:
        """Save backup metadata to file"""
        backup_dir = self.backup_storage_path / metadata.backup_id
        metadata_file = backup_dir / "metadata.json"
        
        # Convert datetime and enum to JSON serializable format
        metadata_dict = asdict(metadata)
        metadata_dict['timestamp'] = metadata.timestamp.isoformat()
        metadata_dict['backup_type'] = metadata.backup_type.value
        metadata_dict['status'] = metadata.status.value
        
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(json.dumps(metadata_dict, indent=2))
    
    async def create_aof_backup(self, backup_name: Optional[str] = None) -> RedisBackupMetadata:
        """Alias for backup_aof method for consistency"""
        return await self.backup_aof(backup_name) 