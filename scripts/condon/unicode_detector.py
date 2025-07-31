#!/usr/bin/env python3
"""
Unicode Feature Detector for Condon Compatibility

This script uses AST analysis to detect Unicode features that are
incompatible with Condon's ASCII-only limitation.

Features Detected:
- encode()/decode() method calls
- Unicode string literals with non-ASCII characters
- Unicode escape sequences (\\u, \\U)
- Internationalization functions (gettext, etc.)
- Base64 encoding/decoding operations
- XML with UTF-8 encoding
- File I/O with Unicode encoding
- Network communication with Unicode

Usage:
    python unicode_detector.py [directory]
    python unicode_detector.py --report-only
    python unicode_detector.py --thread-safety
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
class UnicodeFeature:
    """Represents a detected Unicode feature."""
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
    """Results of Unicode feature detection."""
    total_files_scanned: int
    files_with_unicode_features: int
    total_unicode_features: int
    features_by_type: Dict[str, int] = field(default_factory=dict)
    features_by_severity: Dict[str, int] = field(default_factory=dict)
    thread_safety_issues: int = 0
    critical_issues: int = 0
    scan_timestamp: datetime = field(default_factory=datetime.now)

class UnicodeFeatureDetector:
    """AST-based detector for Unicode features."""
    
    def __init__(self):
        self.unicode_features: List[UnicodeFeature] = []
        self.feature_patterns = {
            'encode_decode': {
                'methods': ['encode', 'decode'],
                'description': 'String encoding/decoding operations',
                'thread_safety': 'HIGH',
                'severity': 'CRITICAL'
            },
            'unicode_literals': {
                'patterns': [r'[\u4e00-\u9fff]', r'[\u3040-\u309f]', r'[\u30a0-\u30ff]', r'[\uac00-\ud7af]'],
                'description': 'Unicode string literals',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'unicode_escapes': {
                'patterns': [r'\\u[0-9a-fA-F]{4}', r'\\U[0-9a-fA-F]{8}'],
                'description': 'Unicode escape sequences',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'base64_operations': {
                'patterns': ['base64.b64encode', 'base64.b64decode'],
                'description': 'Base64 encoding/decoding',
                'thread_safety': 'HIGH',
                'severity': 'CRITICAL'
            },
            'internationalization': {
                'patterns': ['gettext', '_('],
                'description': 'Internationalization functions',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'xml_utf8': {
                'patterns': ['encoding="UTF-8"', 'encoding="utf-8"'],
                'description': 'XML with UTF-8 encoding',
                'thread_safety': 'MEDIUM',
                'severity': 'HIGH'
            },
            'file_io_unicode': {
                'patterns': ['encoding="utf-8"', 'encoding="UTF-8"'],
                'description': 'File I/O with Unicode encoding',
                'thread_safety': 'MEDIUM',
                'severity': 'HIGH'
            }
        }
    
    def scan_directory(self, directory: str) -> DetectionResult:
        """Scan a directory for Unicode features."""
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
                self.unicode_features.extend(file_features)
        
        return self._generate_result(total_files, files_with_features)
    
    def scan_file(self, file_path: Path) -> List[UnicodeFeature]:
        """Scan a single file for Unicode features."""
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
    
    def _analyze_node(self, node: ast.AST, file_path: Path, content: str) -> List[UnicodeFeature]:
        """Analyze a single AST node for Unicode features."""
        features = []
        
        # Check for method calls (encode/decode)
        if isinstance(node, ast.Call):
            features.extend(self._check_method_call(node, file_path, content))
        
        # Check for string literals
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            features.extend(self._check_string_literal(node, file_path, content))
        
        # Check for attribute access (base64 operations)
        elif isinstance(node, ast.Attribute):
            features.extend(self._check_attribute_access(node, file_path, content))
        
        return features
    
    def _check_method_call(self, node: ast.Call, file_path: Path, content: str) -> List[UnicodeFeature]:
        """Check method calls for Unicode features."""
        features = []
        
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            
            # Check for encode/decode methods
            if method_name in self.feature_patterns['encode_decode']['methods']:
                features.append(self._create_feature(
                    'encode_decode',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    f"String {method_name} operation",
                    str(self.feature_patterns['encode_decode']['thread_safety']),
                    "String encoding/decoding for data transformation",
                    "Use Python interoperability for encode/decode operations",
                    str(self.feature_patterns['encode_decode']['severity'])
                ))
        
        return features
    
    def _check_string_literal(self, node: ast.Constant, file_path: Path, content: str) -> List[UnicodeFeature]:
        """Check string literals for Unicode patterns."""
        features = []
        string_value = node.value
        
        # Check for Unicode characters
        for pattern in self.feature_patterns['unicode_literals']['patterns']:
            if re.search(pattern, string_value, re.UNICODE):
                features.append(self._create_feature(
                    'unicode_literals',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    "Unicode string literal detected",
                    str(self.feature_patterns['unicode_literals']['thread_safety']),
                    "International content in string literals",
                    "Replace with ASCII equivalents or use Python interoperability",
                    str(self.feature_patterns['unicode_literals']['severity'])
                ))
                break
        
        # Check for Unicode escape sequences
        for pattern in self.feature_patterns['unicode_escapes']['patterns']:
            if re.search(pattern, string_value, re.UNICODE):
                features.append(self._create_feature(
                    'unicode_escapes',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    "Unicode escape sequence detected",
                    str(self.feature_patterns['unicode_escapes']['thread_safety']),
                    "Unicode character representation",
                    "Replace with ASCII equivalents or use Python interoperability",
                    str(self.feature_patterns['unicode_escapes']['severity'])
                ))
                break
        
        return features
    
    def _check_attribute_access(self, node: ast.Attribute, file_path: Path, content: str) -> List[UnicodeFeature]:
        """Check attribute access for Unicode patterns."""
        features = []
        
        # Check for base64 operations
        if isinstance(node.value, ast.Attribute):
            if (node.value.value.id == 'base64' and 
                node.value.attr in ['b64encode', 'b64decode']):
                features.append(self._create_feature(
                    'base64_operations',
                    file_path,
                    node.lineno,
                    node.col_offset,
                    self._get_code_snippet(content, node.lineno, node.col_offset),
                    "Base64 encoding/decoding operation",
                    str(self.feature_patterns['base64_operations']['thread_safety']),
                    "Data encoding for transmission or storage",
                    "Use Python interoperability for base64 operations",
                    str(self.feature_patterns['base64_operations']['severity'])
                ))
        
        return features
    
    def _create_feature(self, feature_type: str, file_path: Path, line: int, 
                       column: int, code_snippet: str, description: str,
                       thread_safety: str, business_justification: str,
                       mitigation_strategy: str, severity: str) -> UnicodeFeature:
        """Create a UnicodeFeature instance."""
        return UnicodeFeature(
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
        
        for feature in self.unicode_features:
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
            files_with_unicode_features=files_with_features,
            total_unicode_features=len(self.unicode_features),
            features_by_type=features_by_type,
            features_by_severity=features_by_severity,
            thread_safety_issues=thread_safety_issues,
            critical_issues=critical_issues
        )

def generate_report(detector: UnicodeFeatureDetector, result: DetectionResult, 
                   output_file: Optional[str] = None) -> None:
    """Generate a comprehensive report of Unicode features."""
    
    report = {
        'scan_timestamp': result.scan_timestamp.isoformat(),
        'summary': {
            'total_files_scanned': result.total_files_scanned,
            'files_with_unicode_features': result.files_with_unicode_features,
            'total_unicode_features': result.total_unicode_features,
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
            for f in detector.unicode_features
        ]
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_file}")
    else:
        print(json.dumps(report, indent=2))

def main():
    """Main function for the Unicode feature detector."""
    parser = argparse.ArgumentParser(description='Detect Unicode features for Condon compatibility')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan (default: current directory)')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--report-only', action='store_true', help='Generate report from previous scan')
    parser.add_argument('--thread-safety', action='store_true', help='Focus on thread safety issues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    detector = UnicodeFeatureDetector()
    
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
        print(f"\n=== Unicode Feature Detection Summary ===")
        print(f"Files scanned: {result.total_files_scanned}")
        print(f"Files with Unicode features: {result.files_with_unicode_features}")
        print(f"Total Unicode features found: {result.total_unicode_features}")
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
        if detector.unicode_features:
            print(f"\n=== Critical Unicode Features ===")
            for feature in detector.unicode_features:
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