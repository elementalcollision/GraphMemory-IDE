#!/usr/bin/env python3
"""
Performance Analyzer for Codon Optimization Analysis

This script analyzes computational components theoretically to establish performance baselines
and identify components that would benefit most from Codon's performance improvements.

Components Analyzed:
- server/analytics/algorithms.py
- server/monitoring/ai_performance_optimizer.py
- monitoring/ai_detection/anomaly_detector.py

Analysis Methods:
- Code structure analysis
- Library usage patterns
- Theoretical performance assessment
- Codon optimization potential evaluation
"""

import ast
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceAnalysis:
    """Performance analysis results."""
    component_name: str
    file_path: str
    execution_complexity: str  # LOW, MEDIUM, HIGH, CRITICAL
    memory_usage: str  # LOW, MEDIUM, HIGH, CRITICAL
    cpu_intensity: str  # LOW, MEDIUM, HIGH, CRITICAL
    libraries_used: List[str]
    bottlenecks: List[str]
    optimization_opportunities: List[str]
    thread_safety_issues: List[str]
    codon_optimization_potential: str
    estimated_speedup: str  # 10x, 50x, 100x, 1000x
    scan_timestamp: datetime = field(default_factory=datetime.now)

class PerformanceAnalyzer:
    """Performance analyzer for computational components."""
    
    def __init__(self):
        self.results: List[PerformanceAnalysis] = []
        self.components = {
            'analytics_algorithms': {
                'file': 'server/analytics/algorithms.py',
                'description': 'Graph algorithms and ML analytics',
                'expected_complexity': 'HIGH',
                'expected_memory': 'MEDIUM',
                'expected_cpu': 'HIGH'
            },
            'ai_performance_optimizer': {
                'file': 'server/monitoring/ai_performance_optimizer.py',
                'description': 'AI-powered performance optimization',
                'expected_complexity': 'HIGH',
                'expected_memory': 'HIGH',
                'expected_cpu': 'HIGH'
            },
            'anomaly_detector': {
                'file': 'monitoring/ai_detection/anomaly_detector.py',
                'description': 'AI anomaly detection engine',
                'expected_complexity': 'CRITICAL',
                'expected_memory': 'HIGH',
                'expected_cpu': 'CRITICAL'
            }
        }
        
        # Library performance characteristics
        self.library_performance = {
            'networkx': {
                'complexity': 'HIGH',
                'memory': 'MEDIUM',
                'cpu': 'HIGH',
                'codon_speedup': '50x'
            },
            'numpy': {
                'complexity': 'MEDIUM',
                'memory': 'MEDIUM',
                'cpu': 'HIGH',
                'codon_speedup': '100x'
            },
            'pandas': {
                'complexity': 'MEDIUM',
                'memory': 'HIGH',
                'cpu': 'MEDIUM',
                'codon_speedup': '50x'
            },
            'sklearn': {
                'complexity': 'HIGH',
                'memory': 'HIGH',
                'cpu': 'CRITICAL',
                'codon_speedup': '100x'
            },
            'tensorflow': {
                'complexity': 'CRITICAL',
                'memory': 'CRITICAL',
                'cpu': 'CRITICAL',
                'codon_speedup': '1000x'
            },
            'torch': {
                'complexity': 'CRITICAL',
                'memory': 'CRITICAL',
                'cpu': 'CRITICAL',
                'codon_speedup': '1000x'
            },
            'asyncio': {
                'complexity': 'MEDIUM',
                'memory': 'LOW',
                'cpu': 'LOW',
                'codon_speedup': '10x'
            },
            'threading': {
                'complexity': 'MEDIUM',
                'memory': 'LOW',
                'cpu': 'LOW',
                'codon_speedup': '10x'
            }
        }
    
    def analyze_component(self, component_name: str, file_path: str) -> PerformanceAnalysis:
        """Analyze a computational component."""
        logger.info(f"Analyzing component: {component_name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            libraries = self._extract_libraries(tree)
            bottlenecks = self._identify_bottlenecks(libraries)
            optimization_opportunities = self._identify_optimization_opportunities(libraries, bottlenecks)
            thread_safety_issues = self._assess_thread_safety_issues(libraries, bottlenecks)
            
            # Calculate complexity scores
            execution_complexity = self._calculate_complexity(libraries)
            memory_usage = self._calculate_memory_usage(libraries)
            cpu_intensity = self._calculate_cpu_intensity(libraries)
            
            # Determine Codon optimization potential
            codon_potential = self._assess_codon_optimization_potential(
                execution_complexity, memory_usage, cpu_intensity, bottlenecks
            )
            
            # Estimate speedup
            estimated_speedup = self._estimate_speedup(libraries, bottlenecks)
            
            return PerformanceAnalysis(
                component_name=component_name,
                file_path=file_path,
                execution_complexity=execution_complexity,
                memory_usage=memory_usage,
                cpu_intensity=cpu_intensity,
                libraries_used=libraries,
                bottlenecks=bottlenecks,
                optimization_opportunities=optimization_opportunities,
                thread_safety_issues=thread_safety_issues,
                codon_optimization_potential=codon_potential,
                estimated_speedup=estimated_speedup
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {component_name}: {e}")
            return None
    
    def _extract_libraries(self, tree: ast.AST) -> List[str]:
        """Extract library imports from AST."""
        libraries = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    lib_name = alias.name.split('.')[0]
                    if lib_name in self.library_performance:
                        libraries.append(lib_name)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    lib_name = node.module.split('.')[0]
                    if lib_name in self.library_performance:
                        libraries.append(lib_name)
        
        return list(set(libraries))
    
    def _identify_bottlenecks(self, libraries: List[str]) -> List[str]:
        """Identify performance bottlenecks based on libraries used."""
        bottlenecks = []
        
        if 'networkx' in libraries:
            bottlenecks.append("NETWORKX_INTENSIVE")
        
        if 'numpy' in libraries:
            bottlenecks.append("NUMPY_INTENSIVE")
        
        if 'pandas' in libraries:
            bottlenecks.append("PANDAS_INTENSIVE")
        
        if 'sklearn' in libraries:
            bottlenecks.append("SKLEARN_INTENSIVE")
        
        if 'tensorflow' in libraries:
            bottlenecks.append("TENSORFLOW_INTENSIVE")
        
        if 'torch' in libraries:
            bottlenecks.append("PYTORCH_INTENSIVE")
        
        return bottlenecks
    
    def _identify_optimization_opportunities(self, libraries: List[str], bottlenecks: List[str]) -> List[str]:
        """Identify optimization opportunities."""
        opportunities = []
        
        if "NETWORKX_INTENSIVE" in bottlenecks:
            opportunities.append("GRAPH_ALGORITHM_OPTIMIZATION")
        
        if "NUMPY_INTENSIVE" in bottlenecks:
            opportunities.append("NUMERICAL_COMPUTATION_OPTIMIZATION")
        
        if "PANDAS_INTENSIVE" in bottlenecks:
            opportunities.append("DATA_PROCESSING_OPTIMIZATION")
        
        if "SKLEARN_INTENSIVE" in bottlenecks:
            opportunities.append("MACHINE_LEARNING_OPTIMIZATION")
        
        if "TENSORFLOW_INTENSIVE" in bottlenecks:
            opportunities.append("DEEP_LEARNING_OPTIMIZATION")
        
        if "PYTORCH_INTENSIVE" in bottlenecks:
            opportunities.append("DEEP_LEARNING_OPTIMIZATION")
        
        return opportunities
    
    def _assess_thread_safety_issues(self, libraries: List[str], bottlenecks: List[str]) -> List[str]:
        """Assess thread safety issues."""
        issues = []
        
        if 'tensorflow' in libraries or 'torch' in libraries:
            issues.append("ML_LIBRARY_THREAD_SAFETY")
        
        if 'numpy' in libraries and len(libraries) > 3:
            issues.append("NUMERICAL_COMPUTATION_THREAD_SAFETY")
        
        if 'sklearn' in libraries:
            issues.append("ML_ALGORITHM_THREAD_SAFETY")
        
        return issues
    
    def _calculate_complexity(self, libraries: List[str]) -> str:
        """Calculate execution complexity based on libraries."""
        score = 0
        
        for lib in libraries:
            if lib in self.library_performance:
                complexity = self.library_performance[lib]['complexity']
                if complexity == 'CRITICAL':
                    score += 3
                elif complexity == 'HIGH':
                    score += 2
                elif complexity == 'MEDIUM':
                    score += 1
        
        if score >= 6:
            return "CRITICAL"
        elif score >= 4:
            return "HIGH"
        elif score >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_memory_usage(self, libraries: List[str]) -> str:
        """Calculate memory usage based on libraries."""
        score = 0
        
        for lib in libraries:
            if lib in self.library_performance:
                memory = self.library_performance[lib]['memory']
                if memory == 'CRITICAL':
                    score += 3
                elif memory == 'HIGH':
                    score += 2
                elif memory == 'MEDIUM':
                    score += 1
        
        if score >= 6:
            return "CRITICAL"
        elif score >= 4:
            return "HIGH"
        elif score >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_cpu_intensity(self, libraries: List[str]) -> str:
        """Calculate CPU intensity based on libraries."""
        score = 0
        
        for lib in libraries:
            if lib in self.library_performance:
                cpu = self.library_performance[lib]['cpu']
                if cpu == 'CRITICAL':
                    score += 3
                elif cpu == 'HIGH':
                    score += 2
                elif cpu == 'MEDIUM':
                    score += 1
        
        if score >= 6:
            return "CRITICAL"
        elif score >= 4:
            return "HIGH"
        elif score >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _assess_codon_optimization_potential(self, execution_complexity: str,
                                             memory_usage: str, cpu_intensity: str,
                                             bottlenecks: List[str]) -> str:
        """Assess Codon optimization potential."""
        score = 0
        
        # Complexity factor
        if execution_complexity == 'CRITICAL':
            score += 3
        elif execution_complexity == 'HIGH':
            score += 2
        elif execution_complexity == 'MEDIUM':
            score += 1
        
        # Memory factor
        if memory_usage == 'CRITICAL':
            score += 3
        elif memory_usage == 'HIGH':
            score += 2
        elif memory_usage == 'MEDIUM':
            score += 1
        
        # CPU factor
        if cpu_intensity == 'CRITICAL':
            score += 3
        elif cpu_intensity == 'HIGH':
            score += 2
        elif cpu_intensity == 'MEDIUM':
            score += 1
        
        # Bottleneck factors
        if "TENSORFLOW_INTENSIVE" in bottlenecks or "PYTORCH_INTENSIVE" in bottlenecks:
            score += 3
        if "SKLEARN_INTENSIVE" in bottlenecks:
            score += 3
        if "NUMPY_INTENSIVE" in bottlenecks:
            score += 2
        if "NETWORKX_INTENSIVE" in bottlenecks:
            score += 2
        
        if score >= 10:
            return "CRITICAL"
        elif score >= 7:
            return "HIGH"
        elif score >= 4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _estimate_speedup(self, libraries: List[str], bottlenecks: List[str]) -> str:
        """Estimate Codon speedup based on libraries and bottlenecks."""
        max_speedup = 0
        
        for lib in libraries:
            if lib in self.library_performance:
                speedup_str = self.library_performance[lib]['codon_speedup']
                speedup = int(speedup_str.replace('x', ''))
                max_speedup = max(max_speedup, speedup)
        
        # Additional speedup for critical bottlenecks
        if "TENSORFLOW_INTENSIVE" in bottlenecks or "PYTORCH_INTENSIVE" in bottlenecks:
            max_speedup = max(max_speedup, 1000)
        
        if max_speedup >= 1000:
            return "1000x"
        elif max_speedup >= 100:
            return "100x"
        elif max_speedup >= 50:
            return "50x"
        else:
            return "10x"
    
    def run_analysis(self) -> List[PerformanceAnalysis]:
        """Run performance analysis for all components."""
        logger.info("Starting performance analysis...")
        
        for component_name, config in self.components.items():
            file_path = config['file']
            
            if Path(file_path).exists():
                result = self.analyze_component(component_name, file_path)
                if result:
                    self.results.append(result)
                    logger.info(f"Completed analysis for {component_name}")
            else:
                logger.warning(f"File not found: {file_path}")
        
        return self.results

def generate_report(results: List[PerformanceAnalysis], output_file: Optional[str] = None) -> None:
    """Generate a comprehensive performance analysis report."""
    
    report = {
        'scan_timestamp': datetime.now().isoformat(),
        'summary': {
            'total_components_analyzed': len(results),
            'components_with_high_optimization_potential': len([r for r in results if r.codon_optimization_potential in ['HIGH', 'CRITICAL']]),
            'components_with_thread_safety_issues': len([r for r in results if r.thread_safety_issues]),
            'average_complexity': 'HIGH' if any(r.execution_complexity in ['HIGH', 'CRITICAL'] for r in results) else 'MEDIUM',
            'average_memory_usage': 'HIGH' if any(r.memory_usage in ['HIGH', 'CRITICAL'] for r in results) else 'MEDIUM',
            'average_cpu_intensity': 'HIGH' if any(r.cpu_intensity in ['HIGH', 'CRITICAL'] for r in results) else 'MEDIUM'
        },
        'detailed_results': [
            {
                'component_name': r.component_name,
                'file_path': r.file_path,
                'execution_complexity': r.execution_complexity,
                'memory_usage': r.memory_usage,
                'cpu_intensity': r.cpu_intensity,
                'libraries_used': r.libraries_used,
                'bottlenecks': r.bottlenecks,
                'optimization_opportunities': r.optimization_opportunities,
                'thread_safety_issues': r.thread_safety_issues,
                'codon_optimization_potential': r.codon_optimization_potential,
                'estimated_speedup': r.estimated_speedup
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
    """Main function for the performance analyzer."""
    parser = argparse.ArgumentParser(description='Analyze computational components for Codon optimization')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        analyzer = PerformanceAnalyzer()
        results = analyzer.run_analysis()
        
        # Print summary
        print(f"\n=== Performance Analysis Summary ===")
        print(f"Components analyzed: {len(results)}")
        print(f"High optimization potential: {len([r for r in results if r.codon_optimization_potential in ['HIGH', 'CRITICAL']])}")
        print(f"Thread safety issues: {len([r for r in results if r.thread_safety_issues])}")
        
        # Show high-potential components
        high_potential = [r for r in results if r.codon_optimization_potential in ['HIGH', 'CRITICAL']]
        if high_potential:
            print(f"\n=== High Codon Optimization Potential ===")
            for result in high_potential:
                print(f"\nComponent: {result.component_name}")
                print(f"File: {result.file_path}")
                print(f"Optimization Potential: {result.codon_optimization_potential}")
                print(f"Estimated Speedup: {result.estimated_speedup}")
                print(f"Execution Complexity: {result.execution_complexity}")
                print(f"Memory Usage: {result.memory_usage}")
                print(f"CPU Intensity: {result.cpu_intensity}")
                print(f"Libraries: {', '.join(result.libraries_used)}")
                print(f"Bottlenecks: {', '.join(result.bottlenecks)}")
                print(f"Thread Safety Issues: {', '.join(result.thread_safety_issues)}")
        
        # Generate detailed report
        if args.output:
            generate_report(results, args.output)
        
        if any(r.codon_optimization_potential == 'CRITICAL' for r in results):
            sys.exit(1)  # Exit with error if critical optimization needed
            
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 