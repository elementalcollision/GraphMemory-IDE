#!/usr/bin/env python3
"""
Type System Compatibility Detector for Codon

This script uses AST analysis to detect type annotations and patterns that may be
incompatible with Codon's static type checking requirements.

Features Detected:
- Complex type annotations (Union, Optional, etc.)
- Generic type usage
- Callable types
- Protocol types
- TypeVar usage
- NewType definitions
- Literal types
- TYPE_CHECKING imports
- Any usage
- Missing type annotations
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
class TypeSystemFeature:
    """Represents a detected type system feature."""
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
    """Results of type system compatibility detection."""
    total_files_scanned: int
    files_with_type_features: int
    total_type_features: int
    features_by_type: Dict[str, int] = field(default_factory=dict)
    features_by_severity: Dict[str, int] = field(default_factory=dict)
    thread_safety_issues: int = 0
    critical_issues: int = 0
    scan_timestamp: datetime = field(default_factory=datetime.now)

class TypeSystemDetector:
    """AST-based detector for type system compatibility issues."""
    
    def __init__(self):
        self.type_features: List[TypeSystemFeature] = []
        self.feature_patterns = {
            'complex_types': {
                'patterns': ['Union[', 'Optional[', 'List[', 'Dict[', 'Tuple['],
                'description': 'Complex type annotations',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'generic_types': {
                'patterns': ['Generic', 'TypeVar', 'NewType'],
                'description': 'Generic type usage',
                'thread_safety': 'LOW',
                'severity': 'HIGH'
            },
            'callable_types': {
                'patterns': ['Callable[', 'Protocol'],
                'description': 'Callable and Protocol types',
                'thread_safety': 'LOW',
                'severity': 'HIGH'
            },
            'literal_types': {
                'patterns': ['Literal['],
                'description': 'Literal type usage',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'any_usage': {
                'patterns': ['Any', 'typing.Any'],
                'description': 'Any type usage',
                'thread_safety': 'MEDIUM',
                'severity': 'CRITICAL'
            },
            'type_checking': {
                'patterns': ['TYPE_CHECKING', 'if TYPE_CHECKING:'],
                'description': 'TYPE_CHECKING conditional imports',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'missing_annotations': {
                'patterns': ['def ', 'async def '],
                'description': 'Missing type annotations',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'complex_unions': {
                'patterns': ['Union[str, int, float]', 'Union[Dict, List]'],
                'description': 'Complex Union types',
                'thread_safety': 'LOW',
                'severity': 'HIGH'
            }
        }
    
    def scan_directory(self, directory: str) -> DetectionResult:
        """Scan a directory for type system compatibility issues."""
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
                self.type_features.extend(file_features)
        
        return self._generate_result(total_files, files_with_features)
    
    def scan_file(self, file_path: Path) -> List[TypeSystemFeature]:
        """Scan a single file for type system compatibility issues."""
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
    
    def _analyze_node(self, node: ast.AST, file_path: Path, content: str) -> List[TypeSystemFeature]:
        """Analyze a single AST node for type system compatibility issues."""
        features = []
        
        # Check for imports (TYPE_CHECKING, typing imports)
        if isinstance(node, ast.ImportFrom):
            features.extend(self._check_import_from(node, file_path, content))
        
        # Check for function definitions (missing annotations)
        elif isinstance(node, ast.FunctionDef):
            features.extend(self._check_function_def(node, file_path, content))
        
        # Check for async function definitions
        elif isinstance(node, ast.AsyncFunctionDef):
            features.extend(self._check_async_function_def(node, file_path, content))
        
        # Check for variable annotations
        elif isinstance(node, ast.AnnAssign):
            features.extend(self._check_variable_annotation(node, file_path, content))
        
        # Check for type comments (deprecated)
        elif isinstance(node, ast.Expr) and hasattr(node, 'value'):
            features.extend(self._check_type_comment(node, file_path, content))
        
        return features
    
    def _check_import_from(self, node: ast.ImportFrom, file_path: Path, content: str) -> List[TypeSystemFeature]:
        """Check import statements for type system features."""
        features = []
        
        # Check for TYPE_CHECKING imports
        if node.module == 'typing' and any(name.name == 'TYPE_CHECKING' for name in node.names):
            features.append(self._create_feature(
                'type_checking',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                "TYPE_CHECKING import detected",
                str(self.feature_patterns['type_checking']['thread_safety']),
                "Conditional type checking import",
                "Use Python interoperability for conditional imports",
                str(self.feature_patterns['type_checking']['severity'])
            ))
        
        # Check for complex type imports
        complex_types = ['Union', 'Optional', 'List', 'Dict', 'Tuple', 'Callable', 'Protocol', 'TypeVar', 'NewType', 'Literal']
        for name in node.names:
            if name.name in complex_types:
                features.append(self._create_feature(
                    'complex_types',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"Complex type import: {name.name}",
                    str(self.feature_patterns['complex_types']['thread_safety']),
                    "Complex type annotation usage",
                    "Use Python interoperability for complex types",
                    str(self.feature_patterns['complex_types']['severity'])
                ))
        
        return features
    
    def _check_function_def(self, node: ast.FunctionDef, file_path: Path, content: str) -> List[TypeSystemFeature]:
        """Check function definitions for type system issues."""
        features = []
        
        # Check for missing return type annotation
        if node.returns is None:
            features.append(self._create_feature(
                'missing_annotations',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                "Missing return type annotation",
                str(self.feature_patterns['missing_annotations']['thread_safety']),
                "Function missing return type annotation",
                "Add explicit return type annotation",
                str(self.feature_patterns['missing_annotations']['severity'])
            ))
        
        # Check for complex parameter types
        for arg in node.args.args:
            if arg.annotation:
                annotation_str = ast.unparse(arg.annotation)
                if any(pattern in annotation_str for pattern in self.feature_patterns['complex_types']['patterns']):
                    features.append(self._create_feature(
                        'complex_types',
                        file_path,
                        node.lineno,
                        node.col_offset,
                        self._get_code_snippet(content, node.lineno, node.col_offset),
                        f"Complex parameter type: {annotation_str}",
                        str(self.feature_patterns['complex_types']['thread_safety']),
                        "Complex parameter type annotation",
                        "Use Python interoperability for complex parameter types",
                        str(self.feature_patterns['complex_types']['severity'])
                    ))
        
        return features
    
    def _check_async_function_def(self, node: ast.AsyncFunctionDef, file_path: Path, content: str) -> List[TypeSystemFeature]:
        """Check async function definitions for type system issues."""
        features = []
        
        # Check for missing return type annotation
        if node.returns is None:
            features.append(self._create_feature(
                'missing_annotations',
                file_path,
                node.lineno,
                node.col_offset,
                self._get_code_snippet(content, node.lineno, node.col_offset),
                "Missing async function return type annotation",
                str(self.feature_patterns['missing_annotations']['thread_safety']),
                "Async function missing return type annotation",
                "Add explicit return type annotation for async function",
                str(self.feature_patterns['missing_annotations']['severity'])
            ))
        
        return features
    
    def _check_variable_annotation(self, node: ast.AnnAssign, file_path: Path, content: str) -> List[TypeSystemFeature]:
        """Check variable annotations for type system issues."""
        features = []
        
        if node.annotation:
            annotation_str = ast.unparse(node.annotation)
            
            # Check for Any usage
            if 'Any' in annotation_str:
                features.append(self._create_feature(
                    'any_usage',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"Any type annotation: {annotation_str}",
                    str(self.feature_patterns['any_usage']['thread_safety']),
                    "Any type annotation usage",
                    "Replace Any with specific type or use Python interoperability",
                    str(self.feature_patterns['any_usage']['severity'])
                ))
            
            # Check for complex types
            elif any(pattern in annotation_str for pattern in self.feature_patterns['complex_types']['patterns']):
                features.append(self._create_feature(
                    'complex_types',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"Complex variable type: {annotation_str}",
                    str(self.feature_patterns['complex_types']['thread_safety']),
                    "Complex variable type annotation",
                    "Use Python interoperability for complex variable types",
                    str(self.feature_patterns['complex_types']['severity'])
                ))
        
        return features
    
    def _check_type_comment(self, node: ast.Expr, file_path: Path, content: str) -> List[TypeSystemFeature]:
        """Check for deprecated type comments."""
        features = []
        
        # This is a simplified check - in practice, you'd need more sophisticated parsing
        # for type comments since they're not part of the AST
        return features
    
    def _create_feature(self, feature_type: str, file_path: Path, line: int, 
                        column: int, code_snippet: str, description: str,
                        thread_safety: str, business_justification: str,
                        mitigation_strategy: str, severity: str) -> TypeSystemFeature:
        """Create a TypeSystemFeature instance."""
        return TypeSystemFeature(
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
        
        for feature in self.type_features:
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
            files_with_type_features=files_with_features,
            total_type_features=len(self.type_features),
            features_by_type=features_by_type,
            features_by_severity=features_by_severity,
            thread_safety_issues=thread_safety_issues,
            critical_issues=critical_issues
        )

def generate_report(detector: TypeSystemDetector, result: DetectionResult, 
                    output_file: Optional[str] = None) -> None:
    """Generate a comprehensive report of type system compatibility issues."""
    
    report = {
        'scan_timestamp': result.scan_timestamp.isoformat(),
        'summary': {
            'total_files_scanned': result.total_files_scanned,
            'files_with_type_features': result.files_with_type_features,
            'total_type_features': result.total_type_features,
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
            for f in detector.type_features
        ]
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_file}")
    else:
        print(json.dumps(report, indent=2))

def main():
    """Main function for the type system compatibility detector."""
    parser = argparse.ArgumentParser(description='Detect type system compatibility issues for Codon')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan (default: current directory)')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--report-only', action='store_true', help='Generate report from previous scan')
    parser.add_argument('--thread-safety', action='store_true', help='Focus on thread safety issues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    detector = TypeSystemDetector()
    
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
        print(f"\n=== Type System Compatibility Detection Summary ===")
        print(f"Files scanned: {result.total_files_scanned}")
        print(f"Files with type features: {result.files_with_type_features}")
        print(f"Total type features found: {result.total_type_features}")
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
        if detector.type_features:
            print(f"\n=== Critical Type System Issues ===")
            for feature in detector.type_features:
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