#!/usr/bin/env python3
"""
Dictionary Order Dependency Detector for Condon Compatibility

This script uses AST analysis to detect dictionary usage patterns that rely on
insertion order preservation, which is incompatible with Condon's dictionary type.

Features Detected:
- OrderedDict usage
- Dictionary iteration that assumes order
- Dictionary comprehensions with order requirements
- JSON serialization/deserialization patterns
- Configuration dictionaries
- Cache implementations
- Dictionary-based data structures
"""

import ast
import os
import sys
import json
import argparse
import re
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
class DictionaryOrderFeature:
    """Represents a detected dictionary order dependency."""
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
    """Results of dictionary order dependency detection."""
    total_files_scanned: int
    files_with_order_dependencies: int
    total_order_dependencies: int
    features_by_type: Dict[str, int] = field(default_factory=dict)
    features_by_severity: Dict[str, int] = field(default_factory=dict)
    thread_safety_issues: int = 0
    critical_issues: int = 0
    scan_timestamp: datetime = field(default_factory=datetime.now)

class DictionaryOrderDetector:
    """AST-based detector for dictionary order dependencies."""
    
    def __init__(self):
        self.order_features: List[DictionaryOrderFeature] = []
        self.feature_patterns = {
            'ordered_dict_usage': {
                'patterns': ['OrderedDict', 'collections.OrderedDict'],
                'description': 'Explicit OrderedDict usage',
                'thread_safety': 'LOW',
                'severity': 'HIGH'
            },
            'dictionary_iteration': {
                'methods': ['items', 'keys', 'values'],
                'description': 'Dictionary iteration that may assume order',
                'thread_safety': 'MEDIUM',
                'severity': 'MEDIUM'
            },
            'json_serialization': {
                'patterns': ['json.dumps', 'json.loads'],
                'description': 'JSON serialization/deserialization',
                'thread_safety': 'LOW',
                'severity': 'HIGH'
            },
            'to_dict_methods': {
                'patterns': ['to_dict', 'from_dict'],
                'description': 'Dictionary serialization methods',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'dictionary_comprehension': {
                'patterns': ['{k: v for', '{k: v if', 'dict('],
                'description': 'Dictionary comprehensions with order requirements',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'cache_implementations': {
                'patterns': ['cache', 'Cache', '_cache'],
                'description': 'Cache implementations using dictionaries',
                'thread_safety': 'HIGH',
                'severity': 'CRITICAL'
            },
            'configuration_dicts': {
                'patterns': ['config', 'Config', 'settings', 'Settings'],
                'description': 'Configuration dictionaries',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            }
        }
    
    def scan_directory(self, directory: str) -> DetectionResult:
        """Scan a directory for dictionary order dependencies."""
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
                self.order_features.extend(file_features)
        
        return self._generate_result(total_files, files_with_features)
    
    def scan_file(self, file_path: Path) -> List[DictionaryOrderFeature]:
        """Scan a single file for dictionary order dependencies."""
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
    
    def _analyze_node(self, node: ast.AST, file_path: Path, content: str) -> List[DictionaryOrderFeature]:
        """Analyze a single AST node for dictionary order dependencies."""
        features = []
        
        # Check for imports (OrderedDict)
        if isinstance(node, ast.ImportFrom):
            features.extend(self._check_import_from(node, file_path, content))
        
        # Check for function calls (json.dumps, etc.)
        elif isinstance(node, ast.Call):
            features.extend(self._check_function_call(node, file_path, content))
        
        # Check for attribute access (dict.items, etc.)
        elif isinstance(node, ast.Attribute):
            features.extend(self._check_attribute_access(node, file_path, content))
        
        # Check for dictionary literals and comprehensions
        elif isinstance(node, ast.Dict):
            features.extend(self._check_dict_literal(node, file_path, content))
        
        return features
    
    def _check_import_from(self, node: ast.ImportFrom, file_path: Path, content: str) -> List[DictionaryOrderFeature]:
        """Check import statements for OrderedDict usage."""
        features = []
        
        if node.module == 'collections' and any(name.name == 'OrderedDict' for name in node.names):
            features.append(self._create_feature(
                'ordered_dict_usage',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                "OrderedDict import detected",
                str(self.feature_patterns['ordered_dict_usage']['thread_safety']),
                "Explicit order preservation requirement",
                "Replace with regular dict or use Python interoperability",
                str(self.feature_patterns['ordered_dict_usage']['severity'])
            ))
        
        return features
    
    def _check_function_call(self, node: ast.Call, file_path: Path, content: str) -> List[DictionaryOrderFeature]:
        """Check function calls for dictionary order dependencies."""
        features = []
        
        if isinstance(node.func, ast.Attribute):
            # Check for json.dumps/json.loads
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == 'json' and 
                node.func.attr in ['dumps', 'loads']):
                features.append(self._create_feature(
                    'json_serialization',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"JSON {node.func.attr} operation",
                    str(self.feature_patterns['json_serialization']['thread_safety']),
                    "JSON serialization/deserialization",
                    "Use Python interoperability for JSON operations",
                    str(self.feature_patterns['json_serialization']['severity'])
                ))
        
        return features
    
    def _check_attribute_access(self, node: ast.Attribute, file_path: Path, content: str) -> List[DictionaryOrderFeature]:
        """Check attribute access for dictionary order dependencies."""
        features = []
        
        # Check for dict.items(), dict.keys(), dict.values()
        if (isinstance(node.value, ast.Name) and 
            node.attr in self.feature_patterns['dictionary_iteration']['methods']):
            features.append(self._create_feature(
                'dictionary_iteration',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                f"Dictionary {node.attr}() iteration",
                str(self.feature_patterns['dictionary_iteration']['thread_safety']),
                "Dictionary iteration that may assume order",
                "Use sorted() or explicit ordering if order matters",
                str(self.feature_patterns['dictionary_iteration']['severity'])
            ))
        
        # Check for to_dict/from_dict methods
        elif node.attr in ['to_dict', 'from_dict']:
            features.append(self._create_feature(
                'to_dict_methods',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                f"{node.attr} method usage",
                str(self.feature_patterns['to_dict_methods']['thread_safety']),
                "Dictionary serialization method",
                "Ensure serialization doesn't depend on order",
                str(self.feature_patterns['to_dict_methods']['severity'])
            ))
        
        return features
    
    def _check_dict_literal(self, node: ast.Dict, file_path: Path, content: str) -> List[DictionaryOrderFeature]:
        """Check dictionary literals for order dependencies."""
        features = []
        
        # Check if this is part of a comprehension or complex structure
        parent = getattr(node, 'parent', None)
        if parent and isinstance(parent, ast.DictComp):
            features.append(self._create_feature(
                'dictionary_comprehension',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                "Dictionary comprehension detected",
                str(self.feature_patterns['dictionary_comprehension']['thread_safety']),
                "Dictionary comprehension with potential order requirements",
                "Ensure comprehension doesn't depend on insertion order",
                str(self.feature_patterns['dictionary_comprehension']['severity'])
            ))
        
        return features
    
    def _create_feature(self, feature_type: str, file_path: Path, line: int, 
                        column: int, code_snippet: str, description: str,
                        thread_safety: str, business_justification: str,
                        mitigation_strategy: str, severity: str) -> DictionaryOrderFeature:
        """Create a DictionaryOrderFeature instance."""
        return DictionaryOrderFeature(
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
        
        for feature in self.order_features:
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
            files_with_order_dependencies=files_with_features,
            total_order_dependencies=len(self.order_features),
            features_by_type=features_by_type,
            features_by_severity=features_by_severity,
            thread_safety_issues=thread_safety_issues,
            critical_issues=critical_issues
        )

def generate_report(detector: DictionaryOrderDetector, result: DetectionResult, 
                    output_file: Optional[str] = None) -> None:
    """Generate a comprehensive report of dictionary order dependencies."""
    
    report = {
        'scan_timestamp': result.scan_timestamp.isoformat(),
        'summary': {
            'total_files_scanned': result.total_files_scanned,
            'files_with_order_dependencies': result.files_with_order_dependencies,
            'total_order_dependencies': result.total_order_dependencies,
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
            for f in detector.order_features
        ]
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_file}")
    else:
        print(json.dumps(report, indent=2))

def main():
    """Main function for the dictionary order dependency detector."""
    parser = argparse.ArgumentParser(description='Detect dictionary order dependencies for Condon compatibility')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan (default: current directory)')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--report-only', action='store_true', help='Generate report from previous scan')
    parser.add_argument('--thread-safety', action='store_true', help='Focus on thread safety issues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    detector = DictionaryOrderDetector()
    
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
        print(f"\n=== Dictionary Order Dependency Detection Summary ===")
        print(f"Files scanned: {result.total_files_scanned}")
        print(f"Files with order dependencies: {result.files_with_order_dependencies}")
        print(f"Total order dependencies found: {result.total_order_dependencies}")
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
        if detector.order_features:
            print(f"\n=== Critical Dictionary Order Dependencies ===")
            for feature in detector.order_features:
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