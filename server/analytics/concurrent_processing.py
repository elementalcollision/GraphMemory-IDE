import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional, Union, AsyncGenerator
import multiprocessing as mp
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ConcurrentProcessingManager:
    """Manages concurrent processing for analytics operations"""
    
    def __init__(self, 
                 max_thread_workers: Optional[int] = None,
                 max_process_workers: Optional[int] = None) -> None:
        
        # Default to optimal worker counts
        self.max_thread_workers = max_thread_workers or min(32, (mp.cpu_count() or 1) + 4)
        self.max_process_workers = max_process_workers or (mp.cpu_count() or 1)
        
        self.thread_executor: Optional[ThreadPoolExecutor] = None
        self.process_executor: Optional[ProcessPoolExecutor] = None
        self._initialized = False
        self._shutdown = False
    
    async def initialize(self) -> None:
        """Initialize executor pools"""
        if self._initialized or self._shutdown:
            return
        
        self.thread_executor = ThreadPoolExecutor(
            max_workers=self.max_thread_workers,
            thread_name_prefix="analytics-thread"
        )
        
        self.process_executor = ProcessPoolExecutor(
            max_workers=self.max_process_workers,
            mp_context=mp.get_context('spawn')  # More stable than fork
        )
        
        self._initialized = True
        logger.info(
            f"Initialized concurrent processing: "
            f"{self.max_thread_workers} threads, {self.max_process_workers} processes"
        )
    
    async def shutdown(self) -> None:
        """Shutdown executor pools"""
        if not self._initialized or self._shutdown:
            return
            
        if self.thread_executor:
            self.thread_executor.shutdown(wait=True)
            self.thread_executor = None
            
        if self.process_executor:
            self.process_executor.shutdown(wait=True)
            self.process_executor = None
        
        self._initialized = False
        self._shutdown = True
        logger.info("Concurrent processing shutdown complete")
    
    @asynccontextmanager
    async def thread_pool_context(self) -> AsyncGenerator[ThreadPoolExecutor, None]:
        """Context manager for thread pool operations"""
        if not self._initialized:
            await self.initialize()
        
        if not self.thread_executor:
            raise RuntimeError("Thread executor not available")
        
        try:
            yield self.thread_executor
        except Exception as e:
            logger.error(f"Thread pool operation failed: {e}")
            raise
    
    @asynccontextmanager
    async def process_pool_context(self) -> AsyncGenerator[ProcessPoolExecutor, None]:
        """Context manager for process pool operations"""
        if not self._initialized:
            await self.initialize()
        
        if not self.process_executor:
            raise RuntimeError("Process executor not available")
        
        try:
            yield self.process_executor
        except Exception as e:
            logger.error(f"Process pool operation failed: {e}")
            raise
    
    async def run_cpu_intensive_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run CPU-intensive task in process pool"""
        async with self.process_pool_context() as executor:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(executor, func, *args, **kwargs)
    
    async def run_io_intensive_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run I/O-intensive task in thread pool"""
        async with self.thread_pool_context() as executor:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(executor, func, *args, **kwargs)
    
    async def run_parallel_tasks(self, tasks: List[Dict[str, Any]], 
                                task_type: str = "thread") -> List[Any]:
        """Run multiple tasks in parallel"""
        if task_type == "thread":
            executor_context = self.thread_pool_context()
        else:
            executor_context = self.process_pool_context()
        
        async with executor_context as executor:
            loop = asyncio.get_event_loop()
            futures = []
            
            for task in tasks:
                func = task['func']
                args = task.get('args', ())
                kwargs = task.get('kwargs', {})
                
                future = loop.run_in_executor(executor, func, *args, **kwargs)
                futures.append(future)
            
            results = await asyncio.gather(*futures, return_exceptions=True)
            # Convert tuple result to list to match return type
            return list(results)
    
    async def run_parallel_algorithms(self, 
                                    algorithms: List[Dict[str, Any]], 
                                    graph_data: Any) -> Dict[str, Any]:
        """Run multiple analytics algorithms in parallel"""
        tasks = []
        
        for algo_config in algorithms:
            algorithm_name = algo_config['name']
            algorithm_func = algo_config['func']
            algorithm_params = algo_config.get('params', {})
            
            # Determine if algorithm is CPU or I/O intensive
            cpu_intensive_algorithms = [
                'betweenness_centrality', 'closeness_centrality', 
                'spectral_clustering', 'community_detection'
            ]
            
            task_type = "process" if algorithm_name in cpu_intensive_algorithms else "thread"
            
            task = {
                'func': algorithm_func,
                'args': (graph_data,),
                'kwargs': algorithm_params,
                'name': algorithm_name,
                'type': task_type
            }
            tasks.append(task)
        
        # Group tasks by type for optimal execution
        thread_tasks = [t for t in tasks if t['type'] == 'thread']
        process_tasks = [t for t in tasks if t['type'] == 'process']
        
        results = {}
        
        # Run thread tasks
        if thread_tasks:
            thread_results = await self.run_parallel_tasks(thread_tasks, "thread")
            for i, task in enumerate(thread_tasks):
                results[task['name']] = {
                    'result': thread_results[i],
                    'execution_type': 'thread'
                }
        
        # Run process tasks
        if process_tasks:
            process_results = await self.run_parallel_tasks(process_tasks, "process")
            for i, task in enumerate(process_tasks):
                results[task['name']] = {
                    'result': process_results[i],
                    'execution_type': 'process'
                }
        
        return results
    
    def get_executor_status(self) -> Dict[str, Any]:
        """Get current executor status"""
        return {
            "initialized": self._initialized,
            "shutdown": self._shutdown,
            "thread_executor_available": self.thread_executor is not None,
            "process_executor_available": self.process_executor is not None,
            "max_thread_workers": self.max_thread_workers,
            "max_process_workers": self.max_process_workers,
            "cpu_count": mp.cpu_count()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on executors"""
        if not self._initialized:
            return {"status": "not_initialized", "healthy": False}
        
        health_status = {
            "status": "healthy",
            "healthy": True,
            "thread_executor": False,
            "process_executor": False
        }
        
        # Test function for executors
        def test_function() -> str:
            return "test"
        
        # Test thread executor
        try:
            if self.thread_executor:
                async with self.thread_pool_context() as executor:
                    loop = asyncio.get_event_loop()
                    test_result = await loop.run_in_executor(executor, lambda: test_function())
                    health_status["thread_executor"] = test_result == "test"
        except Exception as e:
            logger.error(f"Thread executor health check failed: {e}")
            health_status["thread_executor_error"] = str(e)
        
        # Test process executor
        try:
            if self.process_executor:
                async with self.process_pool_context() as executor:
                    loop = asyncio.get_event_loop()
                    test_result = await loop.run_in_executor(executor, lambda: test_function())
                    health_status["process_executor"] = test_result == "test"
        except Exception as e:
            logger.error(f"Process executor health check failed: {e}")
            health_status["process_executor_error"] = str(e)
        
        # Overall health
        if not (health_status["thread_executor"] and health_status["process_executor"]):
            health_status["status"] = "degraded"
            health_status["healthy"] = False
        
        return health_status


# Global instance for easy access
concurrent_manager = ConcurrentProcessingManager() 