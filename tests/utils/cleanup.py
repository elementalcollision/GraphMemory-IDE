"""
Cleanup utilities for GraphMemory-IDE integration testing.
Provides automatic resource cleanup, database cleanup, and file management.
"""

import asyncio
import os
import shutil
import tempfile
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Callable
import logging

logger = logging.getLogger(__name__)

class ResourceCleanupManager:
    """Manages cleanup of test resources."""
    
    def __init__(self):
        self.cleanup_tasks: List[Callable] = []
        self.temp_files: Set[Path] = set()
        self.temp_dirs: Set[Path] = set()
        self.active_processes: List[Any] = []
        self.database_connections: List[Any] = []
    
    def register_cleanup_task(self, task: Callable):
        """Register a cleanup task to be executed later."""
        self.cleanup_tasks.append(task)
    
    def register_temp_file(self, file_path: Path):
        """Register a temporary file for cleanup."""
        self.temp_files.add(file_path)
    
    def register_temp_dir(self, dir_path: Path):
        """Register a temporary directory for cleanup."""
        self.temp_dirs.add(dir_path)
    
    def register_process(self, process: Any):
        """Register a process for cleanup."""
        self.active_processes.append(process)
    
    def register_database_connection(self, connection: Any):
        """Register a database connection for cleanup."""
        self.database_connections.append(connection)
    
    async def cleanup_all(self):
        """Execute all cleanup tasks."""
        logger.info("Starting comprehensive cleanup")
        
        # Execute custom cleanup tasks
        for task in reversed(self.cleanup_tasks):  # LIFO order
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
                logger.debug(f"Executed cleanup task: {task.__name__}")
            except Exception as e:
                logger.warning(f"Cleanup task failed: {task.__name__}: {e}")
        
        # Cleanup database connections
        await self._cleanup_database_connections()
        
        # Cleanup processes
        await self._cleanup_processes()
        
        # Cleanup temporary files and directories
        self._cleanup_temp_files()
        
        # Clear all registrations
        self.cleanup_tasks.clear()
        self.temp_files.clear()
        self.temp_dirs.clear()
        self.active_processes.clear()
        self.database_connections.clear()
        
        logger.info("Cleanup completed")
    
    async def _cleanup_database_connections(self):
        """Cleanup database connections."""
        for connection in self.database_connections:
            try:
                if hasattr(connection, 'close'):
                    if asyncio.iscoroutinefunction(connection.close):
                        await connection.close()
                    else:
                        connection.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.warning(f"Failed to close database connection: {e}")
    
    async def _cleanup_processes(self):
        """Cleanup active processes."""
        for process in self.active_processes:
            try:
                if hasattr(process, 'terminate'):
                    process.terminate()
                    # Wait for termination with timeout
                    try:
                        if hasattr(process, 'wait'):
                            if asyncio.iscoroutinefunction(process.wait):
                                await asyncio.wait_for(process.wait(), timeout=5.0)
                            else:
                                process.wait()
                    except asyncio.TimeoutError:
                        if hasattr(process, 'kill'):
                            process.kill()
                logger.debug("Process terminated")
            except Exception as e:
                logger.warning(f"Failed to terminate process: {e}")
    
    def _cleanup_temp_files(self):
        """Cleanup temporary files and directories."""
        # Cleanup temporary files
        for file_path in self.temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Removed temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {file_path}: {e}")
        
        # Cleanup temporary directories
        for dir_path in self.temp_dirs:
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    logger.debug(f"Removed temp directory: {dir_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp directory {dir_path}: {e}")

class DatabaseCleanupManager:
    """Specialized cleanup for database resources."""
    
    def __init__(self):
        self.kuzu_databases: List[Path] = []
        self.redis_databases: List[int] = []
        self.sqlite_databases: List[Path] = []
    
    def register_kuzu_database(self, db_path: Path):
        """Register Kuzu database for cleanup."""
        self.kuzu_databases.append(db_path)
    
    def register_redis_database(self, db_number: int):
        """Register Redis database for cleanup."""
        self.redis_databases.append(db_number)
    
    def register_sqlite_database(self, db_path: Path):
        """Register SQLite database for cleanup."""
        self.sqlite_databases.append(db_path)
    
    async def cleanup_databases(self):
        """Cleanup all registered databases."""
        logger.info("Starting database cleanup")
        
        # Cleanup Kuzu databases
        for db_path in self.kuzu_databases:
            try:
                if db_path.exists():
                    shutil.rmtree(db_path)
                    logger.debug(f"Removed Kuzu database: {db_path}")
            except Exception as e:
                logger.warning(f"Failed to remove Kuzu database {db_path}: {e}")
        
        # Cleanup Redis databases
        await self._cleanup_redis_databases()
        
        # Cleanup SQLite databases
        for db_path in self.sqlite_databases:
            try:
                if db_path.exists():
                    db_path.unlink()
                    logger.debug(f"Removed SQLite database: {db_path}")
            except Exception as e:
                logger.warning(f"Failed to remove SQLite database {db_path}: {e}")
        
        # Clear registrations
        self.kuzu_databases.clear()
        self.redis_databases.clear()
        self.sqlite_databases.clear()
        
        logger.info("Database cleanup completed")
    
    async def _cleanup_redis_databases(self):
        """Cleanup Redis test databases."""
        try:
            import redis.asyncio as redis
            
            for db_number in self.redis_databases:
                try:
                    client = redis.Redis(
                        host=os.getenv("REDIS_HOST", "localhost"),
                        port=int(os.getenv("REDIS_PORT", "6379")),
                        db=db_number
                    )
                    await client.flushdb()
                    await client.close()
                    logger.debug(f"Flushed Redis database {db_number}")
                except Exception as e:
                    logger.warning(f"Failed to flush Redis database {db_number}: {e}")
        except ImportError:
            logger.debug("Redis not available, skipping Redis cleanup")

class FileCleanupManager:
    """Manages cleanup of test files and directories."""
    
    def __init__(self, base_test_dir: Optional[Path] = None):
        self.base_test_dir = base_test_dir or Path(tempfile.gettempdir()) / "graphmemory_tests"
        self.tracked_files: Set[Path] = set()
        self.tracked_dirs: Set[Path] = set()
        self.created_files: Set[Path] = set()
        self.created_dirs: Set[Path] = set()
    
    def create_temp_file(self, suffix: str = "", prefix: str = "test_", content: Optional[str] = None) -> Path:
        """Create a temporary file and track it for cleanup."""
        temp_file = Path(tempfile.mktemp(suffix=suffix, prefix=prefix, dir=self.base_test_dir))
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        
        if content:
            temp_file.write_text(content)
        else:
            temp_file.touch()
        
        self.created_files.add(temp_file)
        return temp_file
    
    def create_temp_dir(self, suffix: str = "", prefix: str = "test_") -> Path:
        """Create a temporary directory and track it for cleanup."""
        temp_dir = Path(tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=self.base_test_dir))
        self.created_dirs.add(temp_dir)
        return temp_dir
    
    @contextmanager
    def temp_file_context(self, suffix: str = "", prefix: str = "test_", content: Optional[str] = None):
        """Context manager for temporary file that's automatically cleaned up."""
        temp_file = self.create_temp_file(suffix, prefix, content)
        try:
            yield temp_file
        finally:
            self.cleanup_file(temp_file)
    
    @contextmanager
    def temp_dir_context(self, suffix: str = "", prefix: str = "test_"):
        """Context manager for temporary directory that's automatically cleaned up."""
        temp_dir = self.create_temp_dir(suffix, prefix)
        try:
            yield temp_dir
        finally:
            self.cleanup_dir(temp_dir)
    
    def track_file(self, file_path: Path):
        """Track an existing file for cleanup."""
        self.tracked_files.add(file_path)
    
    def track_dir(self, dir_path: Path):
        """Track an existing directory for cleanup."""
        self.tracked_dirs.add(dir_path)
    
    def cleanup_file(self, file_path: Path):
        """Cleanup a specific file."""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Removed file: {file_path}")
            
            # Remove from tracking
            self.created_files.discard(file_path)
            self.tracked_files.discard(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove file {file_path}: {e}")
    
    def cleanup_dir(self, dir_path: Path):
        """Cleanup a specific directory."""
        try:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                logger.debug(f"Removed directory: {dir_path}")
            
            # Remove from tracking
            self.created_dirs.discard(dir_path)
            self.tracked_dirs.discard(dir_path)
        except Exception as e:
            logger.warning(f"Failed to remove directory {dir_path}: {e}")
    
    def cleanup_all_files(self):
        """Cleanup all tracked files and directories."""
        logger.info("Starting file cleanup")
        
        # Cleanup created files
        for file_path in list(self.created_files):
            self.cleanup_file(file_path)
        
        # Cleanup tracked files
        for file_path in list(self.tracked_files):
            self.cleanup_file(file_path)
        
        # Cleanup created directories
        for dir_path in list(self.created_dirs):
            self.cleanup_dir(dir_path)
        
        # Cleanup tracked directories
        for dir_path in list(self.tracked_dirs):
            self.cleanup_dir(dir_path)
        
        # Cleanup base test directory if empty
        try:
            if self.base_test_dir.exists() and not any(self.base_test_dir.iterdir()):
                self.base_test_dir.rmdir()
                logger.debug(f"Removed empty base test directory: {self.base_test_dir}")
        except Exception as e:
            logger.debug(f"Could not remove base test directory: {e}")
        
        logger.info("File cleanup completed")

class TestSessionCleanup:
    """Comprehensive cleanup manager for test sessions."""
    
    def __init__(self):
        self.resource_manager = ResourceCleanupManager()
        self.database_manager = DatabaseCleanupManager()
        self.file_manager = FileCleanupManager()
        self.is_cleanup_registered = False
    
    def register_all_cleanup(self):
        """Register cleanup for all managers."""
        if not self.is_cleanup_registered:
            import atexit
            atexit.register(self._sync_cleanup)
            self.is_cleanup_registered = True
    
    def _sync_cleanup(self):
        """Synchronous cleanup for atexit."""
        asyncio.run(self.cleanup_all())
    
    async def cleanup_all(self):
        """Cleanup all test resources."""
        logger.info("Starting comprehensive test session cleanup")
        
        try:
            # Cleanup in reverse order of creation
            await self.resource_manager.cleanup_all()
            await self.database_manager.cleanup_databases()
            self.file_manager.cleanup_all_files()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("Test session cleanup completed")
    
    @asynccontextmanager
    async def session_context(self):
        """Context manager for test session with automatic cleanup."""
        try:
            yield self
        finally:
            await self.cleanup_all()

# Utility functions for common cleanup patterns
@contextmanager
def auto_cleanup_files(*file_paths: Path):
    """Context manager to automatically cleanup files."""
    try:
        yield
    finally:
        for file_path in file_paths:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")

@contextmanager
def auto_cleanup_dirs(*dir_paths: Path):
    """Context manager to automatically cleanup directories."""
    try:
        yield
    finally:
        for dir_path in dir_paths:
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup directory {dir_path}: {e}")

@asynccontextmanager
async def auto_cleanup_async_resources(*resources):
    """Context manager to automatically cleanup async resources."""
    try:
        yield
    finally:
        for resource in resources:
            try:
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
            except Exception as e:
                logger.warning(f"Failed to cleanup resource {resource}: {e}")

def force_remove_readonly(func, path, exc_info):
    """Error handler for removing read-only files on Windows."""
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)

def safe_remove_tree(path: Path):
    """Safely remove a directory tree, handling read-only files."""
    if path.exists():
        try:
            shutil.rmtree(path, onerror=force_remove_readonly)
        except Exception as e:
            logger.warning(f"Failed to remove tree {path}: {e}")

def cleanup_old_test_files(max_age_hours: int = 24):
    """Cleanup old test files from temporary directory."""
    temp_dir = Path(tempfile.gettempdir())
    current_time = time.time()
    cutoff_time = current_time - (max_age_hours * 3600)
    
    cleaned_count = 0
    for item in temp_dir.glob("graphmemory_test*"):
        try:
            item_time = item.stat().st_mtime
            if item_time < cutoff_time:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    safe_remove_tree(item)
                cleaned_count += 1
        except Exception as e:
            logger.debug(f"Could not cleanup old test item {item}: {e}")
    
    if cleaned_count > 0:
        logger.info(f"Cleaned up {cleaned_count} old test files/directories")

# Global cleanup instance for use in fixtures
global_cleanup = TestSessionCleanup() 