"""
Test helper utilities for GraphMemory-IDE integration testing.
Provides common testing utilities, validators, and performance monitoring.
"""

import asyncio
import time
import tracemalloc
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from datetime import datetime, timedelta
import json
import psutil
import inspect

class AsyncConditionWaiter:
    """Utility for waiting on async conditions with timeout."""
    
    def __init__(self, timeout: float = 30.0, check_interval: float = 0.1) -> None:
        self.timeout = timeout
        self.check_interval = check_interval
    
    async def wait_for_condition(
        self,
        condition_func: Callable[[], Any],
        error_message: str = "Condition not met within timeout",
        timeout: Optional[float] = None
    ) -> Any:
        """
        Wait for a condition function to return a truthy value.
        
        Args:
            condition_func: Function to check condition
            error_message: Error message if timeout occurs
            timeout: Override default timeout
            
        Returns:
            Result of condition_func when truthy
            
        Raises:
            asyncio.TimeoutError: If condition not met within timeout
        """
        timeout = timeout or self.timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = condition_func()
                if asyncio.iscoroutine(result):
                    result = await result
                
                if result:
                    return result
                    
            except Exception as e:
                # Log exception but continue waiting
                print(f"Exception in condition check: {e}")
            
            await asyncio.sleep(self.check_interval)
        
        raise asyncio.TimeoutError(f"{error_message} (timeout: {timeout}s)")
    
    async def wait_for_value_change(
        self,
        value_func: Callable[[], Any],
        initial_value: Any,
        error_message: str = "Value did not change within timeout",
        timeout: Optional[float] = None
    ) -> Any:
        """Wait for a value to change from its initial value."""
        async def condition() -> None:
            current_value = value_func()
            if asyncio.iscoroutine(current_value):
                current_value = await current_value
            return current_value != initial_value
        
        await self.wait_for_condition(condition, error_message, timeout)
        return value_func()
    
    async def wait_for_multiple_conditions(
        self,
        conditions: List[Tuple[Callable[[], Any], str]],
        all_must_pass: bool = True,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Wait for multiple conditions, either all or any to pass."""
        timeout = timeout or self.timeout
        start_time = time.time()
        results = {}
        
        while time.time() - start_time < timeout:
            passed_conditions = 0
            
            for i, (condition_func, description) in enumerate(conditions):
                try:
                    result = condition_func()
                    if asyncio.iscoroutine(result):
                        result = await result
                    
                    if result:
                        results[description] = result
                        passed_conditions += 1
                    
                except Exception as e:
                    results[f"{description}_error"] = str(e)
            
            # Check if we should return
            if all_must_pass and passed_conditions == len(conditions):
                return results
            elif not all_must_pass and passed_conditions > 0:
                return results
            
            await asyncio.sleep(self.check_interval)
        
        mode = "all" if all_must_pass else "any"
        raise asyncio.TimeoutError(
            f"Not {mode} conditions met within {timeout}s. Results: {results}"
        )

class ExecutionTimer:
    """Utility for measuring execution time and performance."""
    
    def __init__(self) -> None:
        self.measurements = {}
        self.active_timers = {}
    
    @contextmanager
    def measure(self, operation_name: str) -> None:
        """Context manager to measure execution time."""
        start_time = time.time()
        try:
            process = psutil.Process()
            start_memory = process.memory_info().rss
        except psutil.NoSuchProcess:
            start_memory = 0
        
        try:
            yield
        finally:
            end_time = time.time()
            try:
                process = psutil.Process()
                end_memory = process.memory_info().rss
            except psutil.NoSuchProcess:
                end_memory = start_memory
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            self.measurements[operation_name] = {
                "duration": duration,
                "memory_delta": memory_delta,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @asynccontextmanager
    async def measure_async(self, operation_name: str) -> None:
        """Async context manager to measure execution time."""
        start_time = time.time()
        try:
            process = psutil.Process()
            start_memory = process.memory_info().rss
        except psutil.NoSuchProcess:
            start_memory = 0
        
        try:
            yield
        finally:
            end_time = time.time()
            try:
                process = psutil.Process()
                end_memory = process.memory_info().rss
            except psutil.NoSuchProcess:
                end_memory = start_memory
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            self.measurements[operation_name] = {
                "duration": duration,
                "memory_delta": memory_delta,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def start_timer(self, operation_name: str) -> None:
        """Start a named timer."""
        try:
            process = psutil.Process()
            start_memory = process.memory_info().rss
        except psutil.NoSuchProcess:
            start_memory = 0
            
        self.active_timers[operation_name] = {
            "start_time": time.time(),
            "start_memory": start_memory
        }
    
    def stop_timer(self, operation_name: str) -> Dict[str, Any]:
        """Stop a named timer and return measurements."""
        if operation_name not in self.active_timers:
            raise ValueError(f"Timer '{operation_name}' not found")
        
        timer_data = self.active_timers.pop(operation_name)
        end_time = time.time()
        try:
            process = psutil.Process()
            end_memory = process.memory_info().rss
        except psutil.NoSuchProcess:
            end_memory = timer_data["start_memory"]
        
        duration = end_time - timer_data["start_time"]
        memory_delta = end_memory - timer_data["start_memory"]
        
        measurement = {
            "duration": duration,
            "memory_delta": memory_delta,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.measurements[operation_name] = measurement
        return measurement
    
    def get_measurements(self) -> Dict[str, Dict[str, Any]]:
        """Get all measurements."""
        return self.measurements.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.measurements:
            return {"total_operations": 0}
        
        durations = [float(m["duration"]) for m in self.measurements.values()]
        memory_deltas = [int(m["memory_delta"]) for m in self.measurements.values()]
        
        return {
            "total_operations": len(self.measurements),
            "total_time": sum(durations),
            "average_time": sum(durations) / len(durations),
            "max_time": max(durations),
            "min_time": min(durations),
            "total_memory_delta": sum(memory_deltas),
            "average_memory_delta": sum(memory_deltas) / len(memory_deltas),
            "slow_operations": [
                name for name, data in self.measurements.items()
                if float(data["duration"]) > 1.0
            ]
        }
    
    def reset_measurements(self) -> None:
        """Reset all measurements."""
        self.measurements.clear()
        self.active_timers.clear()

class ResponseValidator:
    """Utility for validating HTTP responses and API data structures."""
    
    @staticmethod
    def validate_response_structure(
        response: Dict[str, Any],
        required_fields: List[str],
        optional_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate response has required structure.
        
        Returns:
            Dict with validation results
        """
        optional_fields = optional_fields or []
        results = {
            "valid": True,
            "missing_fields": [],
            "unexpected_fields": [],
            "field_types": {},
            "errors": []
        }
        
        # Check required fields
        for field in required_fields:
            if field not in response:
                results["missing_fields"].append(field)
                results["valid"] = False
            else:
                results["field_types"][field] = type(response[field]).__name__
        
        # Check for unexpected fields
        all_expected = set(required_fields + optional_fields)
        for field in response.keys():
            if field not in all_expected:
                results["unexpected_fields"].append(field)
        
        return results
    
    @staticmethod
    def validate_json_response(response_text: str) -> Dict[str, Any]:
        """Validate JSON response format."""
        try:
            data = json.loads(response_text)
            return {
                "valid": True,
                "data": data,
                "size": len(response_text),
                "type": type(data).__name__
            }
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "error": str(e),
                "size": len(response_text),
                "raw_data": response_text[:100] + "..." if len(response_text) > 100 else response_text
            }
    
    @staticmethod
    def validate_timestamp_format(timestamp: str, format_str: str = "%Y-%m-%dT%H:%M:%S") -> bool:
        """Validate timestamp format."""
        try:
            datetime.strptime(timestamp.split('.')[0], format_str)  # Remove microseconds if present
            return True
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def validate_uuid_format(uuid_str: str) -> bool:
        """Validate UUID format."""
        import uuid
        try:
            uuid.UUID(uuid_str)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_pagination_response(
        response: Dict[str, Any],
        expected_items_key: str = "items",
        expected_total_key: str = "total"
    ) -> Dict[str, Any]:
        """Validate paginated response structure."""
        results = {
            "valid": True,
            "has_items": expected_items_key in response,
            "has_total": expected_total_key in response,
            "items_count": 0,
            "total_value": None,
            "errors": []
        }
        
        if not results["has_items"]:
            results["valid"] = False
            results["errors"].append(f"Missing {expected_items_key} field")
        else:
            items = response[expected_items_key]
            if not isinstance(items, list):
                results["valid"] = False
                results["errors"].append(f"{expected_items_key} is not a list")
            else:
                results["items_count"] = len(items)
        
        if not results["has_total"]:
            results["valid"] = False
            results["errors"].append(f"Missing {expected_total_key} field")
        else:
            results["total_value"] = response[expected_total_key]
            if not isinstance(results["total_value"], int):
                results["valid"] = False
                results["errors"].append(f"{expected_total_key} is not an integer")
        
        return results

class DataComparator:
    """Utility for comparing data structures and detecting differences."""
    
    @staticmethod
    def deep_compare(obj1: Any, obj2: Any, path: str = "") -> Dict[str, Any]:
        """
        Deep compare two objects and return differences.
        
        Returns:
            Dict with comparison results
        """
        results = {
            "equal": True,
            "differences": [],
            "type_mismatches": [],
            "missing_keys": [],
            "extra_keys": []
        }
        
        # Type comparison
        if type(obj1) != type(obj2):
            results["equal"] = False
            results["type_mismatches"].append({
                "path": path,
                "type1": type(obj1).__name__,
                "type2": type(obj2).__name__
            })
            return results
        
        # Handle different types
        if isinstance(obj1, dict):
            return DataComparator._compare_dicts(obj1, obj2, path, results)
        elif isinstance(obj1, list):
            return DataComparator._compare_lists(obj1, obj2, path, results)
        else:
            return DataComparator._compare_values(obj1, obj2, path, results)
    
    @staticmethod
    def _compare_dicts(dict1: dict, dict2: dict, path: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two dictionaries."""
        keys1 = set(dict1.keys())
        keys2 = set(dict2.keys())
        
        # Missing and extra keys
        missing = keys1 - keys2
        extra = keys2 - keys1
        
        if missing:
            results["equal"] = False
            for key in missing:
                results["missing_keys"].append(f"{path}.{key}" if path else key)
        
        if extra:
            results["equal"] = False
            for key in extra:
                results["extra_keys"].append(f"{path}.{key}" if path else key)
        
        # Compare common keys
        for key in keys1 & keys2:
            key_path = f"{path}.{key}" if path else key
            sub_result = DataComparator.deep_compare(dict1[key], dict2[key], key_path)
            
            if not sub_result["equal"]:
                results["equal"] = False
                results["differences"].extend(sub_result["differences"])
                results["type_mismatches"].extend(sub_result["type_mismatches"])
                results["missing_keys"].extend(sub_result["missing_keys"])
                results["extra_keys"].extend(sub_result["extra_keys"])
        
        return results
    
    @staticmethod
    def _compare_lists(list1: list, list2: list, path: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two lists."""
        if len(list1) != len(list2):
            results["equal"] = False
            results["differences"].append({
                "path": path,
                "type": "length_mismatch",
                "length1": len(list1),
                "length2": len(list2)
            })
        
        # Compare elements up to the shorter length
        for i in range(min(len(list1), len(list2))):
            item_path = f"{path}[{i}]"
            sub_result = DataComparator.deep_compare(list1[i], list2[i], item_path)
            
            if not sub_result["equal"]:
                results["equal"] = False
                results["differences"].extend(sub_result["differences"])
                results["type_mismatches"].extend(sub_result["type_mismatches"])
                results["missing_keys"].extend(sub_result["missing_keys"])
                results["extra_keys"].extend(sub_result["extra_keys"])
        
        return results
    
    @staticmethod
    def _compare_values(val1: Any, val2: Any, path: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two primitive values."""
        if val1 != val2:
            results["equal"] = False
            results["differences"].append({
                "path": path,
                "type": "value_mismatch",
                "value1": val1,
                "value2": val2
            })
        
        return results
    
    @staticmethod
    def compare_lists_ignore_order(list1: List[Any], list2: List[Any]) -> Dict[str, Any]:
        """Compare two lists ignoring order."""
        results = {
            "equal": True,
            "missing_items": [],
            "extra_items": [],
            "count_mismatches": {}
        }
        
        if len(list1) != len(list2):
            results["equal"] = False
        
        # Count occurrences
        from collections import Counter
        counter1 = Counter(str(item) for item in list1)  # Convert to string for hashability
        counter2 = Counter(str(item) for item in list2)
        
        # Find differences
        for item in counter1:
            if item not in counter2:
                results["missing_items"].append(item)
                results["equal"] = False
            elif counter1[item] != counter2[item]:
                results["count_mismatches"][item] = {
                    "count1": counter1[item],
                    "count2": counter2[item]
                }
                results["equal"] = False
        
        for item in counter2:
            if item not in counter1:
                results["extra_items"].append(item)
                results["equal"] = False
        
        return results

class MemoryProfiler:
    """Utility for memory profiling during tests."""
    
    def __init__(self) -> None:
        self.snapshots = {}
        self.is_tracing = False
    
    def start_tracing(self) -> None:
        """Start memory tracing."""
        tracemalloc.start()
        self.is_tracing = True
    
    def stop_tracing(self) -> None:
        """Stop memory tracing."""
        if self.is_tracing:
            tracemalloc.stop()
            self.is_tracing = False
    
    def take_snapshot(self, name: str) -> None:
        """Take a memory snapshot."""
        if not self.is_tracing:
            self.start_tracing()
        
        snapshot = tracemalloc.take_snapshot()
        try:
            process = psutil.Process()
            rss_memory = process.memory_info().rss
        except psutil.NoSuchProcess:
            rss_memory = 0
            
        self.snapshots[name] = {
            "snapshot": snapshot,
            "timestamp": datetime.utcnow().isoformat(),
            "rss_memory": rss_memory
        }
    
    def compare_snapshots(self, name1: str, name2: str) -> Dict[str, Any]:
        """Compare two memory snapshots."""
        if name1 not in self.snapshots or name2 not in self.snapshots:
            raise ValueError("One or both snapshots not found")
        
        snap1 = self.snapshots[name1]["snapshot"]
        snap2 = self.snapshots[name2]["snapshot"]
        
        top_stats = snap2.compare_to(snap1, 'lineno')
        
        # Get RSS memory difference
        rss_diff = self.snapshots[name2]["rss_memory"] - self.snapshots[name1]["rss_memory"]
        
        # Analyze top differences
        significant_changes = []
        for stat in top_stats[:10]:  # Top 10 changes
            significant_changes.append({
                "filename": stat.traceback.format()[0],
                "size_diff": stat.size_diff,
                "count_diff": stat.count_diff
            })
        
        return {
            "rss_memory_diff": rss_diff,
            "rss_memory_diff_mb": rss_diff / 1024 / 1024,
            "significant_changes": significant_changes,
            "total_changes": len(top_stats)
        }
    
    def get_current_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            usage = {
                "rss": memory_info.rss,
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms": memory_info.vms,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except psutil.NoSuchProcess:
            usage = {
                "rss": 0,
                "rss_mb": 0.0,
                "vms": 0,
                "vms_mb": 0.0,
                "percent": 0.0,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if self.is_tracing:
            current, peak = tracemalloc.get_traced_memory()
            usage["traced_current"] = current
            usage["traced_current_mb"] = current / 1024 / 1024
            usage["traced_peak"] = peak
            usage["traced_peak_mb"] = peak / 1024 / 1024
        
        return usage
    
    def detect_memory_leaks(self, threshold_mb: float = 10.0) -> Dict[str, Any]:
        """Detect potential memory leaks."""
        if len(self.snapshots) < 2:
            return {"status": "insufficient_data", "snapshots": len(self.snapshots)}
        
        # Compare first and last snapshots
        snapshot_names = list(self.snapshots.keys())
        first_snapshot = snapshot_names[0]
        last_snapshot = snapshot_names[-1]
        
        comparison = self.compare_snapshots(first_snapshot, last_snapshot)
        leak_detected = comparison["rss_memory_diff_mb"] > threshold_mb
        
        return {
            "leak_detected": leak_detected,
            "memory_growth_mb": comparison["rss_memory_diff_mb"],
            "threshold_mb": threshold_mb,
            "first_snapshot": first_snapshot,
            "last_snapshot": last_snapshot,
            "significant_changes": comparison["significant_changes"][:5]  # Top 5
        }

# Convenience functions for common testing patterns
async def wait_for_condition(condition_func: Callable, timeout: float = 30.0, error_message: str = "Condition not met") -> Any:
    """Convenience function for waiting on conditions."""
    waiter = AsyncConditionWaiter(timeout)
    return await waiter.wait_for_condition(condition_func, error_message, timeout)

def measure_execution_time(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    def wrapper(*args, **kwargs) -> Any:
        timer = ExecutionTimer()
        func_name = func.__name__
        
        if inspect.iscoroutinefunction(func):
            async def async_wrapper() -> Any:
                async with timer.measure_async(func_name):
                    result = await func(*args, **kwargs)
                return result, timer.get_measurements()[func_name]
            return async_wrapper()
        else:
            with timer.measure(func_name):
                result = func(*args, **kwargs)
            return result, timer.get_measurements()[func_name]
    
    return wrapper

def validate_api_response(response: Dict[str, Any], required_fields: List[str]) -> bool:
    """Convenience function for API response validation."""
    validator = ResponseValidator()
    result = validator.validate_response_structure(response, required_fields)
    return result["valid"]

def compare_data_structures(obj1: Any, obj2: Any) -> bool:
    """Convenience function for data comparison."""
    comparator = DataComparator()
    result = comparator.deep_compare(obj1, obj2)
    return result["equal"] 