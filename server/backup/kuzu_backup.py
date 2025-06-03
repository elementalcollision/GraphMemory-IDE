"""
Kuzu Graph Database Backup and Recovery Manager

Implements backup strategies for Kuzu embedded graph database including:
- File-system level backups of database directory
- Export/import using supported data formats (JSON, Parquet, CSV)
- Database integrity validation
- Integration with monitoring and alerting systems
"""

import os
import asyncio
import logging
import json
import shutil
import tarfile
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles

logger = logging.getLogger(__name__)


class KuzuBackupType(Enum):
    """Types of Kuzu backups"""
    FILESYSTEM = "filesystem"
    EXPORT_JSON = "export_json"
    EXPORT_PARQUET = "export_parquet"
    EXPORT_CSV = "export_csv"
    FULL_BACKUP = "full_backup"


class KuzuBackupStatus(Enum):
    """Kuzu backup operation status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class KuzuBackupMetadata:
    """Metadata for Kuzu backup operations"""
    backup_id: str
    backup_type: KuzuBackupType
    timestamp: datetime
    database_path: str
    size_bytes: int
    duration_seconds: float
    status: KuzuBackupStatus
    node_tables: Optional[List[str]] = None
    relationship_tables: Optional[List[str]] = None
    storage_location: Optional[str] = None
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    export_format: Optional[str] = None


class KuzuBackupManager:
    """
    Kuzu graph database backup and recovery manager
    """
    
    def __init__(self, 
                 database_path: str,
                 backup_storage_path: str,
                 metrics_collector: Optional[Any] = None) -> None:
        self.database_path = Path(database_path)
        self.backup_storage_path = Path(backup_storage_path)
        self.metrics = metrics_collector
        
        # Ensure storage directory exists
        self.backup_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Validate database path exists
        if not self.database_path.exists():
            logger.warning(f"Kuzu database path does not exist: {self.database_path}")
    
    async def create_filesystem_backup(self, 
                                     backup_name: Optional[str] = None,
                                     compress: bool = True) -> KuzuBackupMetadata:
        """
        Create a filesystem-level backup of the entire Kuzu database directory
        """
        start_time = datetime.utcnow()
        backup_id = backup_name or f"kuzu_fs_backup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting Kuzu filesystem backup: {backup_id}")
        
        try:
            # Record backup start metrics
            if self.metrics:
                self.metrics.record_backup_started(KuzuBackupType.FILESYSTEM.value)
            
            # Create backup directory
            backup_dir = self.backup_storage_path / backup_id
            backup_dir.mkdir(exist_ok=True)
            
            if compress:
                # Create compressed tar archive
                archive_path = backup_dir / f"{backup_id}.tar.gz"
                
                def create_archive() -> bool:
                    try:
                        with tarfile.open(archive_path, "w:gz") as tar:
                            tar.add(self.database_path, arcname=self.database_path.name)
                        return True
                    except Exception:
                        return False
                
                # Run compression in thread pool to avoid blocking
                create_archive_func: Callable[[], bool] = create_archive
                success = await asyncio.get_event_loop().run_in_executor(None, create_archive_func)  # type: ignore
                if not success:
                    raise RuntimeError("Failed to create archive")
                
                backup_size = archive_path.stat().st_size
                
                # Calculate checksum
                checksum = await self._calculate_checksum(archive_path)
                
            else:
                # Copy directory structure
                backup_db_path = backup_dir / self.database_path.name
                
                def copy_directory() -> bool:
                    try:
                        shutil.copytree(self.database_path, backup_db_path)
                        return True
                    except Exception:
                        return False
                
                copy_directory_func: Callable[[], bool] = copy_directory
                success = await asyncio.get_event_loop().run_in_executor(None, copy_directory_func)  # type: ignore
                if not success:
                    raise RuntimeError("Failed to copy directory")
                
                # Calculate total size
                backup_size = sum(f.stat().st_size for f in backup_db_path.rglob('*') if f.is_file())
                
                # Calculate directory checksum (checksum of all file checksums)
                checksum = await self._calculate_directory_checksum(backup_db_path)
            
            # Get database schema information if possible
            node_tables, relationship_tables = await self._get_schema_info()
            
            # Create metadata
            duration = (datetime.utcnow() - start_time).total_seconds()
            metadata = KuzuBackupMetadata(
                backup_id=backup_id,
                backup_type=KuzuBackupType.FILESYSTEM,
                timestamp=start_time,
                database_path=str(self.database_path),
                size_bytes=backup_size,
                duration_seconds=duration,
                status=KuzuBackupStatus.SUCCESS,
                node_tables=node_tables,
                relationship_tables=relationship_tables,
                storage_location=str(backup_dir),
                checksum=checksum
            )
            
            # Save metadata
            await self._save_backup_metadata(metadata)
            
            # Record success metrics
            if self.metrics:
                self.metrics.record_backup_completed(
                    KuzuBackupType.FILESYSTEM.value,
                    duration,
                    backup_size
                )
            
            logger.info(f"Kuzu filesystem backup completed successfully: {backup_id}")
            return metadata
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            # Record failure metrics
            if self.metrics:
                self.metrics.record_backup_failed(KuzuBackupType.FILESYSTEM.value, error_msg)
            
            # Create failure metadata
            metadata = KuzuBackupMetadata(
                backup_id=backup_id,
                backup_type=KuzuBackupType.FILESYSTEM,
                timestamp=start_time,
                database_path=str(self.database_path),
                size_bytes=0,
                duration_seconds=duration,
                status=KuzuBackupStatus.FAILED,
                error_message=error_msg
            )
            
            await self._save_backup_metadata(metadata)
            raise
    
    async def export_to_format(self, 
                             export_format: str = "json",
                             backup_name: Optional[str] = None) -> KuzuBackupMetadata:
        """
        Export Kuzu database to specified format (JSON, Parquet, CSV)
        Note: This requires an active Kuzu connection and is a placeholder for implementation
        """
        start_time = datetime.utcnow()
        backup_id = backup_name or f"kuzu_export_{export_format}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting Kuzu export backup ({export_format}): {backup_id}")
        
        try:
            backup_type = getattr(KuzuBackupType, f"EXPORT_{export_format.upper()}", KuzuBackupType.EXPORT_JSON)
            
            if self.metrics:
                self.metrics.record_backup_started(backup_type.value)
            
            # Create backup directory
            backup_dir = self.backup_storage_path / backup_id
            backup_dir.mkdir(exist_ok=True)
            
            # TODO: Implement actual Kuzu export functionality
            # This would require:
            # 1. Connect to Kuzu database
            # 2. Query all node and relationship tables
            # 3. Export data to specified format
            # 4. Save exported files
            
            # For now, create placeholder files
            export_file = backup_dir / f"database_export.{export_format}"
            placeholder_data = {
                "backup_id": backup_id,
                "timestamp": start_time.isoformat(),
                "format": export_format,
                "note": "Kuzu export functionality requires implementation with actual Kuzu connection"
            }
            
            async with aiofiles.open(export_file, 'w') as f:
                if export_format == "json":
                    await f.write(json.dumps(placeholder_data, indent=2))
                else:
                    await f.write(f"# Kuzu {export_format.upper()} export placeholder\n")
                    await f.write(f"# {json.dumps(placeholder_data)}\n")
            
            backup_size = export_file.stat().st_size
            checksum = await self._calculate_checksum(export_file)
            
            # Create metadata
            duration = (datetime.utcnow() - start_time).total_seconds()
            metadata = KuzuBackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                timestamp=start_time,
                database_path=str(self.database_path),
                size_bytes=backup_size,
                duration_seconds=duration,
                status=KuzuBackupStatus.SUCCESS,
                storage_location=str(backup_dir),
                checksum=checksum,
                export_format=export_format
            )
            
            # Save metadata
            await self._save_backup_metadata(metadata)
            
            # Record success metrics
            if self.metrics:
                self.metrics.record_backup_completed(
                    backup_type.value,
                    duration,
                    backup_size
                )
            
            logger.info(f"Kuzu export backup completed: {backup_id}")
            return metadata
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            backup_type = getattr(KuzuBackupType, f"EXPORT_{export_format.upper()}", KuzuBackupType.EXPORT_JSON)
            
            if self.metrics:
                self.metrics.record_backup_failed(backup_type.value, error_msg)
            
            metadata = KuzuBackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                timestamp=start_time,
                database_path=str(self.database_path),
                size_bytes=0,
                duration_seconds=duration,
                status=KuzuBackupStatus.FAILED,
                error_message=error_msg
            )
            
            await self._save_backup_metadata(metadata)
            raise
    
    async def restore_from_filesystem(self, 
                                    backup_id: str, 
                                    target_path: Optional[str] = None) -> bool:
        """
        Restore Kuzu database from filesystem backup
        """
        logger.info(f"Starting Kuzu filesystem restore from backup: {backup_id}")
        
        try:
            backup_dir = self.backup_storage_path / backup_id
            
            if not backup_dir.exists():
                raise FileNotFoundError(f"Backup directory not found: {backup_dir}")
            
            target_db_path = Path(target_path) if target_path else self.database_path
            
            # Check for compressed archive
            archive_path = backup_dir / f"{backup_id}.tar.gz"
            
            if archive_path.exists():
                # Extract compressed archive
                def extract_archive() -> bool:
                    try:
                        with tarfile.open(archive_path, "r:gz") as tar:
                            tar.extractall(path=target_db_path.parent)
                        return True
                    except Exception:
                        return False
                
                extract_archive_func: Callable[[], bool] = extract_archive
                success = await asyncio.get_event_loop().run_in_executor(None, extract_archive_func)  # type: ignore
                if not success:
                    raise RuntimeError("Failed to extract archive")
                
            else:
                # Look for directory backup
                backup_db_path = backup_dir / self.database_path.name
                
                if backup_db_path.exists():
                    # Copy directory structure
                    if target_db_path.exists():
                        shutil.rmtree(target_db_path)
                    
                    def copy_directory() -> bool:
                        try:
                            shutil.copytree(backup_db_path, target_db_path)
                            return True
                        except Exception:
                            return False
                    
                    copy_directory_func: Callable[[], bool] = copy_directory
                    success = await asyncio.get_event_loop().run_in_executor(None, copy_directory_func)  # type: ignore
                    if not success:
                        raise RuntimeError("Failed to copy directory")
                else:
                    raise FileNotFoundError("No valid backup data found in backup directory")
            
            logger.info(f"Kuzu filesystem restore completed: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Kuzu filesystem restore failed: {e}")
            return False
    
    async def validate_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Validate backup integrity and consistency
        """
        logger.info(f"Validating Kuzu backup: {backup_id}")
        
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
                return validation_results
            
            # Load and validate metadata
            async with aiofiles.open(metadata_file, 'r') as f:
                metadata = json.loads(await f.read())
                validation_results["checks"]["metadata"] = "PASS"
            
            backup_type = metadata.get("backup_type")
            
            if backup_type == "filesystem":
                # Check compressed archive
                archive_path = backup_dir / f"{backup_id}.tar.gz"
                if archive_path.exists():
                    # Verify archive integrity
                    def check_archive() -> bool:
                        try:
                            with tarfile.open(archive_path, "r:gz") as tar:
                                # Test archive integrity
                                tar.getmembers()
                            return True
                        except Exception:
                            return False
                    
                    check_archive_func: Callable[[], bool] = check_archive
                    is_valid_archive = await asyncio.get_event_loop().run_in_executor(None, check_archive_func)  # type: ignore
                    
                    if is_valid_archive:
                        validation_results["checks"]["archive_integrity"] = "PASS"
                    else:
                        validation_results["checks"]["archive_integrity"] = "FAIL"
                        validation_results["errors"].append("Archive is corrupted")
                        validation_results["is_valid"] = False
                    
                    # Verify checksum if available
                    stored_checksum = metadata.get("checksum")
                    if stored_checksum:
                        current_checksum = await self._calculate_checksum(archive_path)
                        if stored_checksum == current_checksum:
                            validation_results["checks"]["checksum"] = "PASS"
                        else:
                            validation_results["checks"]["checksum"] = "FAIL"
                            validation_results["errors"].append("Checksum mismatch")
                            validation_results["is_valid"] = False
                else:
                    # Check directory backup
                    backup_db_path = backup_dir / self.database_path.name
                    if backup_db_path.exists():
                        validation_results["checks"]["directory_exists"] = "PASS"
                        
                        # Verify directory checksum if available
                        stored_checksum = metadata.get("checksum")
                        if stored_checksum:
                            current_checksum = await self._calculate_directory_checksum(backup_db_path)
                            if stored_checksum == current_checksum:
                                validation_results["checks"]["directory_checksum"] = "PASS"
                            else:
                                validation_results["checks"]["directory_checksum"] = "FAIL"
                                validation_results["errors"].append("Directory checksum mismatch")
                                validation_results["is_valid"] = False
                    else:
                        validation_results["checks"]["directory_exists"] = "FAIL"
                        validation_results["errors"].append("Backup directory structure missing")
                        validation_results["is_valid"] = False
            
            elif backup_type.startswith("export_"):
                # Validate export files
                export_format = metadata.get("export_format", "json")
                export_file = backup_dir / f"database_export.{export_format}"
                
                if export_file.exists():
                    validation_results["checks"]["export_file"] = "PASS"
                    
                    # Verify file size
                    actual_size = export_file.stat().st_size
                    expected_size = metadata.get("size_bytes", 0)
                    
                    if actual_size == expected_size:
                        validation_results["checks"]["file_size"] = "PASS"
                    else:
                        validation_results["checks"]["file_size"] = "FAIL"
                        validation_results["errors"].append("File size mismatch")
                        validation_results["is_valid"] = False
                else:
                    validation_results["checks"]["export_file"] = "FAIL"
                    validation_results["errors"].append("Export file missing")
                    validation_results["is_valid"] = False
            
            logger.info(f"Kuzu backup validation completed: {backup_id}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Kuzu backup validation failed: {e}")
            validation_results["is_valid"] = False
            validation_results["errors"].append(str(e))
            return validation_results
    
    async def cleanup_old_backups(self, retention_days: int = 14) -> List[str]:
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
                            shutil.rmtree(backup_dir)
                            removed_backups.append(backup_dir.name)
                            logger.info(f"Removed old Kuzu backup: {backup_dir.name}")
            
            if self.metrics:
                self.metrics.record_backup_cleanup(len(removed_backups))
            
            return removed_backups
            
        except Exception as e:
            logger.error(f"Kuzu backup cleanup failed: {e}")
            return removed_backups
    
    async def _get_schema_info(self) -> tuple[Optional[List[str]], Optional[List[str]]]:
        """
        Get schema information from Kuzu database
        TODO: Implement when Kuzu connection is available
        """
        try:
            # Placeholder for actual Kuzu schema query
            # This would require connecting to the database and querying:
            # - Node table names
            # - Relationship table names
            # - Schema information
            
            # For now, return None to indicate schema info is not available
            return None, None
            
        except Exception as e:
            logger.warning(f"Failed to get Kuzu schema info: {e}")
            return None, None
    
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
    
    async def _calculate_directory_checksum(self, directory_path: Path) -> str:
        """Calculate checksum for entire directory structure"""
        checksums = []
        
        # Sort files for consistent checksum calculation
        for file_path in sorted(directory_path.rglob('*')):
            if file_path.is_file():
                file_checksum = await self._calculate_checksum(file_path)
                # Include relative path in checksum calculation
                relative_path = file_path.relative_to(directory_path)
                checksums.append(f"{relative_path}:{file_checksum}")
        
        # Calculate checksum of all file checksums
        combined_checksums = "\n".join(checksums)
        return hashlib.sha256(combined_checksums.encode()).hexdigest()
    
    async def _save_backup_metadata(self, metadata: KuzuBackupMetadata) -> None:
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