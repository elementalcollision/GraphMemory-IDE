"""
PostgreSQL Backup and Recovery Manager

Implements automated backup strategies for PostgreSQL including:
- WAL archiving with point-in-time recovery (PITR)
- Base backups using pg_basebackup
- Backup validation and integrity checking
- Integration with monitoring and alerting systems
"""

import os
import asyncio
import subprocess
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import boto3
from botocore.exceptions import ClientError
import aiofiles
import asyncpg

from ..monitoring.metrics_collector import MetricsCollector
from ..core.config import settings

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Types of PostgreSQL backups"""
    FULL = "full"
    INCREMENTAL = "incremental" 
    WAL_ARCHIVE = "wal_archive"
    LOGICAL = "logical"


class BackupStatus(Enum):
    """Backup operation status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupMetadata:
    """Metadata for backup operations"""
    backup_id: str
    backup_type: BackupType
    timestamp: datetime
    database_name: str
    size_bytes: int
    duration_seconds: float
    status: BackupStatus
    wal_start_lsn: Optional[str] = None
    wal_end_lsn: Optional[str] = None
    storage_location: Optional[str] = None
    checksum: Optional[str] = None
    error_message: Optional[str] = None


class PostgreSQLBackupManager:
    """
    Comprehensive PostgreSQL backup and recovery manager
    """
    
    def __init__(self, 
                 database_url: str,
                 backup_storage_path: str,
                 wal_archive_path: str,
                 metrics_collector: Optional[MetricsCollector] = None) -> None:
        self.database_url = database_url
        self.backup_storage_path = Path(backup_storage_path)
        self.wal_archive_path = Path(wal_archive_path)
        self.metrics = metrics_collector or MetricsCollector()
        
        # Ensure storage directories exist
        self.backup_storage_path.mkdir(parents=True, exist_ok=True)
        self.wal_archive_path.mkdir(parents=True, exist_ok=True)
        
        # S3 client for cloud storage (optional)
        self.s3_client = None
        if settings.AWS_ACCESS_KEY_ID:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
    
    async def create_base_backup(self, 
                               backup_name: Optional[str] = None,
                               compress: bool = True,
                               verify_checksums: bool = True) -> BackupMetadata:
        """
        Create a base backup using pg_basebackup
        """
        start_time = datetime.utcnow()
        backup_id = backup_name or f"base_backup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting base backup: {backup_id}")
        
        try:
            # Record backup start metrics
            self.metrics.record_backup_started(BackupType.FULL.value)
            
            # Prepare backup directory
            backup_dir = self.backup_storage_path / backup_id
            backup_dir.mkdir(exist_ok=True)
            
            # Build pg_basebackup command
            cmd = [
                "pg_basebackup",
                "-D", str(backup_dir),
                "-Ft",  # Tar format
                "-z" if compress else "",  # Compression
                "-P",   # Progress reporting
                "-v",   # Verbose
                "-d", self.database_url
            ]
            cmd = [arg for arg in cmd if arg]  # Remove empty strings
            
            if verify_checksums:
                cmd.extend(["-c", "fast"])  # Fast checkpoint
            
            # Execute backup
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = f"pg_basebackup failed: {stderr.decode()}"
                logger.error(error_msg)
                self.metrics.record_backup_failed(BackupType.FULL.value, error_msg)
                raise RuntimeError(error_msg)
            
            # Calculate backup size
            backup_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
            
            # Get WAL information
            wal_info = await self._get_wal_info()
            
            # Create metadata
            duration = (datetime.utcnow() - start_time).total_seconds()
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=BackupType.FULL,
                timestamp=start_time,
                database_name=self._extract_db_name(),
                size_bytes=backup_size,
                duration_seconds=duration,
                status=BackupStatus.SUCCESS,
                wal_start_lsn=wal_info.get('start_lsn'),
                wal_end_lsn=wal_info.get('end_lsn'),
                storage_location=str(backup_dir)
            )
            
            # Save metadata
            await self._save_backup_metadata(metadata)
            
            # Record success metrics
            self.metrics.record_backup_completed(
                BackupType.FULL.value, 
                duration, 
                backup_size
            )
            
            logger.info(f"Base backup completed successfully: {backup_id}")
            return metadata
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            # Record failure metrics
            self.metrics.record_backup_failed(BackupType.FULL.value, error_msg)
            
            # Create failure metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=BackupType.FULL,
                timestamp=start_time,
                database_name=self._extract_db_name(),
                size_bytes=0,
                duration_seconds=duration,
                status=BackupStatus.FAILED,
                error_message=error_msg
            )
            
            await self._save_backup_metadata(metadata)
            raise
    
    async def archive_wal_segment(self, wal_file: str) -> bool:
        """
        Archive a WAL segment file
        """
        try:
            source_path = Path(f"/var/lib/postgresql/data/pg_wal/{wal_file}")
            archive_path = self.wal_archive_path / wal_file
            
            if not source_path.exists():
                logger.warning(f"WAL file not found: {source_path}")
                return False
            
            # Copy WAL file to archive location
            cmd = ["cp", str(source_path), str(archive_path)]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                logger.debug(f"WAL file archived: {wal_file}")
                
                # Upload to S3 if configured
                if self.s3_client and settings.BACKUP_S3_BUCKET:
                    await self._upload_to_s3(archive_path, f"wal/{wal_file}")
                
                self.metrics.record_wal_archived(wal_file)
                return True
            else:
                logger.error(f"Failed to archive WAL file: {wal_file}")
                self.metrics.record_wal_archive_failed(wal_file)
                return False
                
        except Exception as e:
            logger.error(f"Error archiving WAL file {wal_file}: {e}")
            self.metrics.record_wal_archive_failed(wal_file)
            return False
    
    async def perform_point_in_time_recovery(self,
                                           target_time: datetime,
                                           backup_id: str,
                                           recovery_location: str) -> bool:
        """
        Perform point-in-time recovery to specified timestamp
        """
        logger.info(f"Starting PITR to {target_time} using backup {backup_id}")
        
        try:
            self.metrics.record_recovery_started("pitr")
            
            recovery_path = Path(recovery_location)
            recovery_path.mkdir(parents=True, exist_ok=True)
            
            # Restore base backup
            backup_dir = self.backup_storage_path / backup_id
            if not backup_dir.exists():
                raise FileNotFoundError(f"Backup not found: {backup_id}")
            
            # Extract backup
            cmd = [
                "tar", "-xzf", 
                str(backup_dir / "base.tar.gz"),
                "-C", str(recovery_path)
            ]
            
            process = await asyncio.create_subprocess_exec(*cmd)
            await process.wait()
            
            if process.returncode != 0:
                raise RuntimeError("Failed to extract base backup")
            
            # Create recovery configuration
            recovery_conf = self._generate_recovery_conf(target_time)
            
            async with aiofiles.open(recovery_path / "recovery.signal", 'w') as f:
                await f.write("")
            
            async with aiofiles.open(recovery_path / "postgresql.conf", 'a') as f:
                await f.write(f"\n{recovery_conf}\n")
            
            logger.info(f"PITR setup completed for {target_time}")
            self.metrics.record_recovery_completed("pitr")
            return True
            
        except Exception as e:
            logger.error(f"PITR failed: {e}")
            self.metrics.record_recovery_failed("pitr", str(e))
            return False
    
    async def validate_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Validate backup integrity and consistency
        """
        logger.info(f"Validating backup: {backup_id}")
        
        validation_results = {
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
            
            # Check file integrity
            base_tar = backup_dir / "base.tar.gz"
            if base_tar.exists():
                # Verify tar file integrity
                cmd = ["tar", "-tzf", str(base_tar)]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    validation_results["checks"]["tar_integrity"] = "PASS"
                else:
                    validation_results["checks"]["tar_integrity"] = "FAIL"
                    validation_results["is_valid"] = False
                    validation_results["errors"].append("Backup tar file is corrupted")
            
            # Validate metadata
            metadata_file = backup_dir / "metadata.json"
            if metadata_file.exists():
                async with aiofiles.open(metadata_file, 'r') as f:
                    metadata = json.loads(await f.read())
                    validation_results["checks"]["metadata"] = "PASS"
            else:
                validation_results["checks"]["metadata"] = "FAIL"
                validation_results["errors"].append("Metadata file missing")
            
            logger.info(f"Backup validation completed: {backup_id}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            validation_results["is_valid"] = False
            validation_results["errors"].append(str(e))
            return validation_results
    
    async def cleanup_old_backups(self, retention_days: int = 30) -> List[str]:
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
            
            self.metrics.record_backup_cleanup(len(removed_backups))
            return removed_backups
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return removed_backups
    
    async def _get_wal_info(self) -> Dict[str, str]:
        """Get current WAL information from PostgreSQL"""
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Get current WAL position
            row = await conn.fetchrow("SELECT pg_current_wal_lsn() as current_lsn")
            
            await conn.close()
            
            return {
                "current_lsn": row["current_lsn"],
                "start_lsn": row["current_lsn"],  # For base backup
                "end_lsn": row["current_lsn"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get WAL info: {e}")
            return {}
    
    def _extract_db_name(self) -> str:
        """Extract database name from connection URL"""
        try:
            # Parse database name from URL
            parts = self.database_url.split('/')
            return parts[-1] if parts else "unknown"
        except:
            return "unknown"
    
    def _generate_recovery_conf(self, target_time: datetime) -> str:
        """Generate recovery configuration for PITR"""
        return f"""
# Point-in-time recovery configuration
restore_command = 'cp {self.wal_archive_path}/%f %p'
recovery_target_time = '{target_time.strftime("%Y-%m-%d %H:%M:%S")}'
recovery_target_action = 'promote'
"""
    
    async def _save_backup_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to file"""
        backup_dir = self.backup_storage_path / metadata.backup_id
        metadata_file = backup_dir / "metadata.json"
        
        # Convert datetime to ISO format for JSON serialization
        metadata_dict = asdict(metadata)
        metadata_dict['timestamp'] = metadata.timestamp.isoformat()
        metadata_dict['backup_type'] = metadata.backup_type.value
        metadata_dict['status'] = metadata.status.value
        
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(json.dumps(metadata_dict, indent=2))
    
    async def _upload_to_s3(self, local_path: Path, s3_key: str) -> None:
        """Upload file to S3 bucket"""
        if not self.s3_client:
            return
        
        try:
            self.s3_client.upload_file(
                str(local_path),
                settings.BACKUP_S3_BUCKET,
                s3_key
            )
            logger.debug(f"Uploaded to S3: {s3_key}")
            
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}") 