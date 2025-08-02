#!/usr/bin/env python3
"""
Performance Profiler for Codon Optimization Analysis

This script profiles computational components to establish performance baselines
and identify components that would benefit most from Codon's performance improvements.

Components Profiled:
- server/analytics/algorithms.py
- server/monitoring/ai_performance_optimizer.py
- monitoring/ai_detection/anomaly_detector.py

Performance Metrics:
- Execution time analysis
- Function call frequency
- Bottleneck identification
- Optimization potential assessment
"""

import cProfile
import pstats
import time
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    component_name: str
    function_name: str
    execution_time: float
    call_count: int
    total_time: float
    bottleneck_type: str
    optimization_potential: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ProfilingResult:
    """Results of performance profiling."""
    component_name: str
    total_execution_time: float
    total_function_calls: int
    bottlenecks: List[str]
    optimization_opportunities: List[str]
    thread_safety_issues: List[str]
    codon_optimization_potential: str
    scan_timestamp: datetime = field(default_factory=datetime.now)

class PerformanceProfiler:
    """Performance profiler for computational components."""
    
    def __init__(self):
        self.results: List[ProfilingResult] = []
        self.components = {
            'analytics_algorithms': {
                'module': 'server.analytics.algorithms',
                'description': 'Graph algorithms and ML analytics',
                'optimization_potential': 'HIGH',
                'thread_safety': 'MEDIUM'
            },
            'ai_performance_optimizer': {
                'module': 'server.monitoring.ai_performance_optimizer',
                'description': 'AI-powered performance optimization',
                'optimization_potential': 'HIGH',
                'thread_safety': 'HIGH'
            },
            'anomaly_detector': {
                'module': 'monitoring.ai_detection.anomaly_detector',
                'description': 'AI anomaly detection engine',
                'optimization_potential': 'CRITICAL',
                'thread_safety': 'HIGH'
            }
        }
    
    def profile_component(self, component_name: str, test_function: callable, 
                         iterations: int = 5) -> ProfilingResult:
        """Profile a computational component."""
        logger.info(f"Profiling component: {component_name}")
        
        # Initialize profiling data
        execution_times = []
        total_calls = []
        bottlenecks = []
        
        # Profile each iteration
        for i in range(iterations):
            logger.info(f"  Iteration {i+1}/{iterations}")
            
            # Start profiling
            profiler = cProfile.Profile()
            profiler.enable()
            
            # Execute test function
            start_time = time.time()
            try:
                test_function()
            except Exception as e:
                logger.warning(f"Error in test function: {e}")
                continue
            execution_time = time.time() - start_time
            
            # Stop profiling
            profiler.disable()
            
            # Analyze profiler stats
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            
            # Count total calls
            total_call_count = 0
            for func_name, (cc, nc, tt, ct, callers) in stats.stats.items():
                total_call_count += nc
            
            # Store metrics
            execution_times.append(execution_time)
            total_calls.append(total_call_count)
            
            # Identify bottlenecks
            bottleneck = self._identify_bottleneck(stats, execution_time)
            if bottleneck:
                bottlenecks.append(bottleneck)
        
        # Calculate averages
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        avg_total_calls = sum(total_calls) / len(total_calls) if total_calls else 0
        
        # Identify optimization opportunities
        optimization_opportunities = self._identify_optimization_opportunities(
            avg_execution_time, int(avg_total_calls), bottlenecks
        )
        
        # Assess thread safety issues
        thread_safety_issues = self._assess_thread_safety_issues(
            avg_execution_time, bottlenecks
        )
        
        # Determine Codon optimization potential
        codon_potential = self._assess_codon_optimization_potential(
            avg_execution_time, int(avg_total_calls), bottlenecks
        )
        
        return ProfilingResult(
            component_name=component_name,
            total_execution_time=avg_execution_time,
            total_function_calls=int(avg_total_calls),
            bottlenecks=list(set(bottlenecks)),
            optimization_opportunities=optimization_opportunities,
            thread_safety_issues=thread_safety_issues,
            codon_optimization_potential=codon_potential
        )
    
    def _identify_bottleneck(self, stats: pstats.Stats, execution_time: float) -> Optional[str]:
        """Identify performance bottlenecks."""
        bottlenecks = []
        
        # Check for specific bottlenecks
        for func_name, (cc, nc, tt, ct, callers) in stats.stats.items():
            func_str = stats.func_std_string(func_name)
            
            # NetworkX bottleneck
            if 'networkx' in func_str.lower() and ct > execution_time * 0.3:
                bottlenecks.append("NETWORKX_INTENSIVE")
                break
            
            # NumPy bottleneck
            if 'numpy' in func_str.lower() and ct > execution_time * 0.3:
                bottlenecks.append("NUMPY_INTENSIVE")
                break
            
            # scikit-learn bottleneck
            if 'sklearn' in func_str.lower() and ct > execution_time * 0.3:
                bottlenecks.append("SKLEARN_INTENSIVE")
                break
            
            # TensorFlow bottleneck
            if 'tensorflow' in func_str.lower() and ct > execution_time * 0.3:
                bottlenecks.append("TENSORFLOW_INTENSIVE")
                break
        
        # Execution time bottleneck
        if execution_time > 1.0:
            bottlenecks.append("EXECUTION_TIME_INTENSIVE")
        
        return bottlenecks[0] if bottlenecks else None
    
    def _identify_optimization_opportunities(self, execution_time: float, 
                                           total_calls: int, bottlenecks: List[str]) -> List[str]:
        """Identify optimization opportunities."""
        opportunities = []
        
        if execution_time > 1.0:  # More than 1 second
            opportunities.append("EXECUTION_TIME_OPTIMIZATION")
        
        if total_calls > 10000:  # High function call count
            opportunities.append("FUNCTION_CALL_OPTIMIZATION")
        
        if "NETWORKX_INTENSIVE" in bottlenecks:
            opportunities.append("GRAPH_ALGORITHM_OPTIMIZATION")
        
        if "NUMPY_INTENSIVE" in bottlenecks:
            opportunities.append("NUMERICAL_COMPUTATION_OPTIMIZATION")
        
        if "SKLEARN_INTENSIVE" in bottlenecks:
            opportunities.append("MACHINE_LEARNING_OPTIMIZATION")
        
        if "TENSORFLOW_INTENSIVE" in bottlenecks:
            opportunities.append("DEEP_LEARNING_OPTIMIZATION")
        
        return opportunities
    
    def _assess_thread_safety_issues(self, execution_time: float,
                                    bottlenecks: List[str]) -> List[str]:
        """Assess thread safety issues."""
        issues = []
        
        # Long execution time with potential concurrency
        if execution_time > 0.5:
            issues.append("LONG_EXECUTION_TIME")
        
        # Memory-intensive operations
        if "MEMORY_INTENSIVE" in bottlenecks:
            issues.append("MEMORY_THREAD_SAFETY")
        
        return issues
    
    def _assess_codon_optimization_potential(self, execution_time: float,
                                             total_calls: int, bottlenecks: List[str]) -> str:
        """Assess Codon optimization potential."""
        score = 0
        
        # Execution time factor
        if execution_time > 1.0:
            score += 3
        elif execution_time > 0.5:
            score += 2
        elif execution_time > 0.1:
            score += 1
        
        # Function call factor
        if total_calls > 10000:
            score += 2
        elif total_calls > 5000:
            score += 1
        
        # Bottleneck factors
        if "NETWORKX_INTENSIVE" in bottlenecks:
            score += 2
        if "NUMPY_INTENSIVE" in bottlenecks:
            score += 3
        if "SKLEARN_INTENSIVE" in bottlenecks:
            score += 3
        if "TENSORFLOW_INTENSIVE" in bottlenecks:
            score += 3
        
        if score >= 8:
            return "CRITICAL"
        elif score >= 5:
            return "HIGH"
        elif score >= 3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def create_test_functions(self) -> Dict[str, callable]:
        """Create test functions for each component."""
        test_functions = {}
        
        # Test function for analytics algorithms
        def test_analytics_algorithms():
            """Test analytics algorithms performance."""
            try:
                # Import and test graph algorithms
                from server.analytics.algorithms import GraphAlgorithms, MLAnalytics
                from server.analytics.models import CentralityType, ClusteringType
                
                # Create test data
                nodes = [{'id': f'node_{i}', 'label': f'Node {i}'} for i in range(50)]
                edges = [{'source': f'node_{i}', 'target': f'node_{i+1}', 'weight': 1.0} 
                        for i in range(49)]
                
                # Test graph algorithms
                ga = GraphAlgorithms()
                graph = ga.build_networkx_graph(nodes, edges)
                
                # Test centrality calculation
                centrality = asyncio.run(ga.calculate_centrality(graph, CentralityType.BETWEENNESS))
                
                # Test ML analytics
                ml = MLAnalytics()
                features = [[i, i*2, i*3] for i in range(50)]  # Simple features
                clusters, score, _ = asyncio.run(ml.cluster_nodes(features, ClusteringType.KMEANS, 3))
                
            except Exception as e:
                logger.warning(f"Analytics algorithms test failed: {e}")
        
        test_functions['analytics_algorithms'] = test_analytics_algorithms
        
        # Test function for AI performance optimizer
        def test_ai_performance_optimizer():
            """Test AI performance optimizer."""
            try:
                # Import and test AI performance optimizer
                from server.monitoring.ai_performance_optimizer import AIPerformanceOptimizer
                
                # Create test optimizer
                optimizer = AIPerformanceOptimizer()
                
                # Test initialization
                asyncio.run(optimizer.initialize())
                
                # Test performance analysis
                summary = asyncio.run(optimizer.get_performance_summary())
                
                # Cleanup
                asyncio.run(optimizer.cleanup())
                
            except Exception as e:
                logger.warning(f"AI performance optimizer test failed: {e}")
        
        test_functions['ai_performance_optimizer'] = test_ai_performance_optimizer
        
        # Test function for anomaly detector
        def test_anomaly_detector():
            """Test anomaly detector performance."""
            try:
                # Import and test anomaly detector
                from monitoring.ai_detection.anomaly_detector import EnsembleAnomalyDetector
                
                # Create test data
                import pandas as pd
                import numpy as np
                
                data = pd.DataFrame({
                    'timestamp': pd.date_range('2025-01-01', periods=50, freq='H'),
                    'metric_value': np.random.randn(50) + np.sin(np.arange(50) * 0.1)
                })
                
                # Create and test detector
                detector = EnsembleAnomalyDetector()
                detector.train(data)
                anomalies = detector.detect_anomalies(data)
                
            except Exception as e:
                logger.warning(f"Anomaly detector test failed: {e}")
        
        test_functions['anomaly_detector'] = test_anomaly_detector
        
        return test_functions
    
    def run_profiling(self) -> List[ProfilingResult]:
        """Run performance profiling for all components."""
        logger.info("Starting performance profiling...")
        
        test_functions = self.create_test_functions()
        
        for component_name, test_function in test_functions.items():
            try:
                result = self.profile_component(component_name, test_function)
                self.results.append(result)
                logger.info(f"Completed profiling for {component_name}")
            except Exception as e:
                logger.error(f"Error profiling {component_name}: {e}")
        
        return self.results

def generate_report(results: List[ProfilingResult], output_file: Optional[str] = None) -> None:
    """Generate a comprehensive performance profiling report."""
    
    report = {
        'scan_timestamp': datetime.now().isoformat(),
        'summary': {
            'total_components_profiled': len(results),
            'components_with_high_optimization_potential': len([r for r in results if r.codon_optimization_potential in ['HIGH', 'CRITICAL']]),
            'components_with_thread_safety_issues': len([r for r in results if r.thread_safety_issues]),
            'average_execution_time': sum([r.total_execution_time for r in results]) / len(results) if results else 0,
            'average_function_calls': sum([r.total_function_calls for r in results]) / len(results) if results else 0
        },
        'detailed_results': [
            {
                'component_name': r.component_name,
                'total_execution_time': r.total_execution_time,
                'total_function_calls': r.total_function_calls,
                'bottlenecks': r.bottlenecks,
                'optimization_opportunities': r.optimization_opportunities,
                'thread_safety_issues': r.thread_safety_issues,
                'codon_optimization_potential': r.codon_optimization_potential
            }
            for r in results
        ]
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_file}")
    else:
        print(json.dumps(report, indent=2))

def main():
    """Main function for the performance profiler."""
    parser = argparse.ArgumentParser(description='Profile computational components for Codon optimization')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--iterations', '-i', type=int, default=5, help='Number of profiling iterations')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        profiler = PerformanceProfiler()
        results = profiler.run_profiling()
        
        # Print summary
        print(f"\n=== Performance Profiling Summary ===")
        print(f"Components profiled: {len(results)}")
        print(f"High optimization potential: {len([r for r in results if r.codon_optimization_potential in ['HIGH', 'CRITICAL']])}")
        print(f"Thread safety issues: {len([r for r in results if r.thread_safety_issues])}")
        
        if results:
            avg_execution = sum([r.total_execution_time for r in results]) / len(results)
            avg_calls = sum([r.total_function_calls for r in results]) / len(results)
            
            print(f"Average execution time: {avg_execution:.3f}s")
            print(f"Average function calls: {avg_calls:.0f}")
        
        # Show high-potential components
        high_potential = [r for r in results if r.codon_optimization_potential in ['HIGH', 'CRITICAL']]
        if high_potential:
            print(f"\n=== High Codon Optimization Potential ===")
            for result in high_potential:
                print(f"\nComponent: {result.component_name}")
                print(f"Optimization Potential: {result.codon_optimization_potential}")
                print(f"Execution Time: {result.total_execution_time:.3f}s")
                print(f"Function Calls: {result.total_function_calls:.0f}")
                print(f"Bottlenecks: {', '.join(result.bottlenecks)}")
                print(f"Thread Safety Issues: {', '.join(result.thread_safety_issues)}")
        
        # Generate detailed report
        if args.output:
            generate_report(results, args.output)
        
        if any(r.codon_optimization_potential == 'CRITICAL' for r in results):
            sys.exit(1)  # Exit with error if critical optimization needed
            
    except Exception as e:
        logger.error(f"Error during profiling: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 