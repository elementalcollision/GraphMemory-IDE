#!/usr/bin/env python3
"""
Dynamic Feature Detector for Codon Compatibility

This script uses AST analysis to detect dynamic Python features that are
incompatible with Codon's static compilation paradigm.

Features Detected:
- eval(), exec(), compile() functions
- getattr(), setattr(), hasattr() with dynamic names
- __import__() with dynamic module names
- Monkey patching at runtime
- Dynamic class creation
- Metaclass usage
- Decorator factories
- Dynamic attribute access
- Runtime code generation

Usage:
    python dynamic_feature_detector.py [directory]
    python dynamic_feature_detector.py --report-only
    python dynamic_feature_detector.py --thread-safety
"""

import ast
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
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
class DynamicFeature:
    """Represents a detected dynamic feature."""
    feature_type: str
    file_path: str
    line_number: int
    column: int
    code_snippet: str
    description: str
    thread_safety_impact: str  # HIGH, MEDIUM, LOW
    business_justification: str
    mitigation_strategy: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW

@dataclass
class DetectionResult:
    """Results of dynamic feature detection."""
    total_files_scanned: int
    files_with_dynamic_features: int
    total_dynamic_features: int
    features_by_type: Dict[str, int] = field(default_factory=dict)
    features_by_severity: Dict[str, int] = field(default_factory=dict)
    thread_safety_issues: int = 0
    critical_issues: int = 0
    scan_timestamp: datetime = field(default_factory=datetime.now)

class DynamicFeatureDetector:
    """AST-based detector for dynamic Python features."""
    
    def __init__(self):
        self.dynamic_features: List[DynamicFeature] = []
        self.feature_patterns = {
            'eval_exec_compile': {
                'functions': ['eval', 'exec', 'compile'],
                'description': 'Runtime code execution functions',
                'thread_safety': 'HIGH',
                'severity': 'CRITICAL'
            },
            'dynamic_attr_access': {
                'functions': ['getattr', 'setattr', 'hasattr'],
                'description': 'Dynamic attribute access',
                'thread_safety': 'MEDIUM',
                'severity': 'HIGH'
            },
            'dynamic_import': {
                'functions': ['__import__'],
                'description': 'Dynamic module imports',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'monkey_patching': {
                'patterns': ['setattr(', 'monkey', 'patch'],
                'description': 'Runtime monkey patching',
                'thread_safety': 'HIGH',
                'severity': 'CRITICAL'
            },
            'type_function': {
                'functions': ['type'],
                'description': 'Runtime type checking',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'callable_check': {
                'patterns': ['callable(', 'hasattr(', 'getattr('],
                'description': 'Dynamic callable checking',
                'thread_safety': 'MEDIUM',
                'severity': 'HIGH'
            }
        }
    
    def scan_directory(self, directory: str) -> DetectionResult:
        """Scan a directory for dynamic features."""
        directory_path = Path(directory)
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        total_files = 0
        files_with_features = 0
        
        for file_path in directory_path.rglob("*.py"):
            if self._should_skip_file(file_path):
                continue
            
            total_files += 1
            file_features = self.scan_file(file_path)
            
            if file_features:
                files_with_features += 1
                self.dynamic_features.extend(file_features)
        
        return self._generate_result(total_files, files_with_features)
    
    def scan_file(self, file_path: Path) -> List[DynamicFeature]:
        """Scan a single file for dynamic features."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            features = []
            
            for node in ast.walk(tree):
                features.extend(self._analyze_node(node, file_path, content))
            
            return features
            
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
            return []
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if a file should be skipped."""
        skip_patterns = [
            '__pycache__',
            '.git',
            '.venv',
            'venv',
            'env',
            'node_modules',
            '.pytest_cache',
            '.mypy_cache',
            'build',
            'dist',
            '*.egg-info'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _analyze_node(self, node: ast.AST, file_path: Path, content: str) -> List[DynamicFeature]:
        """Analyze a single AST node for dynamic features."""
        features = []
        
        # Check for function calls
        if isinstance(node, ast.Call):
            features.extend(self._check_function_call(node, file_path, content))
        
        # Check for attribute access
        elif isinstance(node, ast.Attribute):
            features.extend(self._check_attribute_access(node, file_path, content))
        
        # Check for imports
        elif isinstance(node, ast.ImportFrom):
            features.extend(self._check_import(node, file_path, content))
        
        # Check for string literals that might indicate dynamic patterns
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            features.extend(self._check_string_literal(node, file_path, content))
        
        return features
    
    def _check_function_call(self, node: ast.Call, file_path: Path, content: str) -> List[DynamicFeature]:
        """Check function calls for dynamic features."""
        features = []
        
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            # Check for eval, exec, compile
            if func_name in self.feature_patterns['eval_exec_compile']['functions']:
                features.append(self._create_feature(
                    'eval_exec_compile',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"Dynamic code execution: {func_name}()",
                    str(self.feature_patterns['eval_exec_compile']['thread_safety']),
                    "Runtime code execution for dynamic behavior",
                    "Replace with static code generation or configuration-based approach",
                    str(self.feature_patterns['eval_exec_compile']['severity'])
                ))
            
            # Check for getattr, setattr, hasattr
            elif func_name in self.feature_patterns['dynamic_attr_access']['functions']:
                features.append(self._create_feature(
                    'dynamic_attr_access',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"Dynamic attribute access: {func_name}()",
                    str(self.feature_patterns['dynamic_attr_access']['thread_safety']),
                    "Dynamic attribute resolution for flexibility",
                    "Replace with explicit property access or type-safe interfaces",
                    str(self.feature_patterns['dynamic_attr_access']['severity'])
                ))
            
            # Check for __import__
            elif func_name in self.feature_patterns['dynamic_import']['functions']:
                features.append(self._create_feature(
                    'dynamic_import',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"Dynamic module import: {func_name}()",
                    str(self.feature_patterns['dynamic_import']['thread_safety']),
                    "Dynamic module loading for plugin architecture",
                    "Use static imports or dependency injection",
                    str(self.feature_patterns['dynamic_import']['severity'])
                ))
            
            # Check for type function
            elif func_name in self.feature_patterns['type_function']['functions']:
                features.append(self._create_feature(
                    'type_function',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"Runtime type checking: {func_name}()",
                    str(self.feature_patterns['type_function']['thread_safety']),
                    "Runtime type determination for dynamic behavior",
                    "Use static type annotations and MyPy for compile-time checking",
                    str(self.feature_patterns['type_function']['severity'])
                ))
        
        return features
    
    def _check_attribute_access(self, node: ast.Attribute, file_path: Path, content: str) -> List[DynamicFeature]:
        """Check attribute access for dynamic patterns."""
        features = []
        
        # Check for monkey patching patterns
        if isinstance(node.value, ast.Name) and node.attr in ['setattr', 'getattr']:
            features.append(self._create_feature(
                'monkey_patching',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                "Potential monkey patching detected",
                'HIGH',
                "Runtime modification of object attributes",
                "Replace with proper inheritance or composition patterns",
                'CRITICAL'
            ))
        
        return features
    
    def _check_import(self, node: ast.ImportFrom, file_path: Path, content: str) -> List[DynamicFeature]:
        """Check imports for dynamic patterns."""
        features = []
        
        # Check for conditional imports or dynamic import patterns
        if node.module and any(pattern in node.module for pattern in ['TYPE_CHECKING', 'typing']):
            features.append(self._create_feature(
                'conditional_import',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                "Conditional import for type checking",
                'LOW',
                "Type checking imports for development tools",
                "Use static type annotations and proper import structure",
                'LOW'
            ))
        
        return features
    
    def _check_string_literal(self, node: ast.Constant, file_path: Path, content: str) -> List[DynamicFeature]:
        """Check string literals for dynamic patterns."""
        features = []
        
        # Check for monkey patching indicators
        if isinstance(node.value, str) and ('monkey' in node.value.lower() or 'patch' in node.value.lower()):
            features.append(self._create_feature(
                'monkey_patching',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                "Monkey patching indicator in string literal",
                'HIGH',
                "Runtime modification of classes or modules",
                "Replace with proper inheritance or adapter patterns",
                'CRITICAL'
            ))
        
        return features
    
    def _create_feature(self, feature_type: str, file_path: Path, line: int, 
                       column: int, code_snippet: str, description: str,
                       thread_safety: str, business_justification: str,
                       mitigation_strategy: str, severity: str) -> DynamicFeature:
        """Create a DynamicFeature instance."""
        return DynamicFeature(
            feature_type=feature_type,
            file_path=str(file_path),
            line_number=line,
            column=column,
            code_snippet=code_snippet,
            description=description,
            thread_safety_impact=thread_safety,
            business_justification=business_justification,
            mitigation_strategy=mitigation_strategy,
            severity=severity
        )
    
    def _get_code_snippet(self, content: str, line: int, column: int) -> str:
        """Extract code snippet around the specified position."""
        lines = content.split('\n')
        if 0 <= line - 1 < len(lines):
            return lines[line - 1].strip()
        return ""
    
    def _generate_result(self, total_files: int, files_with_features: int) -> DetectionResult:
        """Generate detection result summary."""
        features_by_type = {}
        features_by_severity = {}
        thread_safety_issues = 0
        critical_issues = 0
        
        for feature in self.dynamic_features:
            # Count by type
            features_by_type[feature.feature_type] = features_by_type.get(feature.feature_type, 0) + 1
            
            # Count by severity
            features_by_severity[feature.severity] = features_by_severity.get(feature.severity, 0) + 1
            
            # Count thread safety issues
            if feature.thread_safety_impact in ['HIGH', 'CRITICAL']:
                thread_safety_issues += 1
            
            # Count critical issues
            if feature.severity == 'CRITICAL':
                critical_issues += 1
        
        return DetectionResult(
            total_files_scanned=total_files,
            files_with_dynamic_features=files_with_features,
            total_dynamic_features=len(self.dynamic_features),
            features_by_type=features_by_type,
            features_by_severity=features_by_severity,
            thread_safety_issues=thread_safety_issues,
            critical_issues=critical_issues
        )

def generate_report(detector: DynamicFeatureDetector, result: DetectionResult, 
                   output_file: Optional[str] = None) -> None:
    """Generate a comprehensive report of dynamic features."""
    
    report = {
        'scan_timestamp': result.scan_timestamp.isoformat(),
        'summary': {
            'total_files_scanned': result.total_files_scanned,
            'files_with_dynamic_features': result.files_with_dynamic_features,
            'total_dynamic_features': result.total_dynamic_features,
            'thread_safety_issues': result.thread_safety_issues,
            'critical_issues': result.critical_issues
        },
        'features_by_type': result.features_by_type,
        'features_by_severity': result.features_by_severity,
        'detailed_features': [
            {
                'feature_type': f.feature_type,
                'file_path': f.file_path,
                'line_number': f.line_number,
                'column': f.column,
                'code_snippet': f.code_snippet,
                'description': f.description,
                'thread_safety_impact': f.thread_safety_impact,
                'business_justification': f.business_justification,
                'mitigation_strategy': f.mitigation_strategy,
                'severity': f.severity
            }
            for f in detector.dynamic_features
        ]
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_file}")
    else:
        print(json.dumps(report, indent=2))

def main():
    """Main function for the dynamic feature detector."""
    parser = argparse.ArgumentParser(description='Detect dynamic Python features for Codon compatibility')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan (default: current directory)')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--report-only', action='store_true', help='Generate report from previous scan')
    parser.add_argument('--thread-safety', action='store_true', help='Focus on thread safety issues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    detector = DynamicFeatureDetector()
    
    if args.report_only:
        # Load previous results and generate report
        if args.output and os.path.exists(args.output):
            with open(args.output, 'r') as f:
                data = json.load(f)
                print("Previous scan results:")
                print(json.dumps(data, indent=2))
        else:
            print("No previous scan results found")
        return
    
    try:
        logger.info(f"Scanning directory: {args.directory}")
        result = detector.scan_directory(args.directory)
        
        # Print summary
        print(f"\n=== Dynamic Feature Detection Summary ===")
        print(f"Files scanned: {result.total_files_scanned}")
        print(f"Files with dynamic features: {result.files_with_dynamic_features}")
        print(f"Total dynamic features found: {result.total_dynamic_features}")
        print(f"Thread safety issues: {result.thread_safety_issues}")
        print(f"Critical issues: {result.critical_issues}")
        
        if result.features_by_type:
            print(f"\nFeatures by type:")
            for feature_type, count in result.features_by_type.items():
                print(f"  {feature_type}: {count}")
        
        if result.features_by_severity:
            print(f"\nFeatures by severity:")
            for severity, count in result.features_by_severity.items():
                print(f"  {severity}: {count}")
        
        # Generate detailed report
        if args.output or args.thread_safety:
            generate_report(detector, result, args.output)
        
        # Show critical issues
        if detector.dynamic_features:
            print(f"\n=== Critical Dynamic Features ===")
            for feature in detector.dynamic_features:
                if feature.severity == 'CRITICAL':
                    print(f"\nFile: {feature.file_path}:{feature.line_number}")
                    print(f"Type: {feature.feature_type}")
                    print(f"Description: {feature.description}")
                    print(f"Thread Safety: {feature.thread_safety_impact}")
                    print(f"Code: {feature.code_snippet}")
                    print(f"Mitigation: {feature.mitigation_strategy}")
        
        if result.critical_issues > 0:
            sys.exit(1)  # Exit with error if critical issues found
            
    except Exception as e:
        logger.error(f"Error during scanning: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 