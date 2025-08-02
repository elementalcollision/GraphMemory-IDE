#!/usr/bin/env python3
"""
Dependency Compatibility Detector for Codon

This script uses AST analysis to detect external dependencies and assess their
compatibility with Codon's compilation requirements.

Features Detected:
- External library imports
- Database drivers
- Web frameworks
- Data science libraries
- Machine learning libraries
- Authentication libraries
- Monitoring libraries
- Testing frameworks
- Utility libraries
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
class DependencyFeature:
    """Represents a detected external dependency."""
    dependency_name: str
    file_path: str
    line_number: int
    column: int
    code_snippet: str
    description: str
    compatibility_status: str  # COMPATIBLE, PARTIAL, INCOMPATIBLE, UNKNOWN
    thread_safety_impact: str  # HIGH, MEDIUM, LOW
    business_justification: str
    mitigation_strategy: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW

@dataclass
class DetectionResult:
    """Results of dependency compatibility detection."""
    total_files_scanned: int
    files_with_dependencies: int
    total_dependencies: int
    dependencies_by_category: Dict[str, int] = field(default_factory=dict)
    dependencies_by_compatibility: Dict[str, int] = field(default_factory=dict)
    thread_safety_issues: int = 0
    critical_issues: int = 0
    scan_timestamp: datetime = field(default_factory=datetime.now)

class DependencyCompatibilityDetector:
    """AST-based detector for external dependency compatibility issues."""
    
    def __init__(self):
        self.dependency_features: List[DependencyFeature] = []
        self.dependency_categories = {
            'web_frameworks': {
                'libraries': ['fastapi', 'starlette', 'uvicorn', 'flask', 'django'],
                'description': 'Web framework dependencies',
                'compatibility': 'PARTIAL',
                'thread_safety': 'MEDIUM',
                'severity': 'HIGH'
            },
            'database_drivers': {
                'libraries': ['asyncpg', 'psycopg2', 'redis', 'sqlalchemy', 'alembic'],
                'description': 'Database driver dependencies',
                'compatibility': 'INCOMPATIBLE',
                'thread_safety': 'HIGH',
                'severity': 'CRITICAL'
            },
            'data_science': {
                'libraries': ['numpy', 'pandas', 'scipy', 'scikit-learn', 'matplotlib'],
                'description': 'Data science library dependencies',
                'compatibility': 'PARTIAL',
                'thread_safety': 'MEDIUM',
                'severity': 'HIGH'
            },
            'machine_learning': {
                'libraries': ['torch', 'tensorflow', 'transformers', 'sentence-transformers'],
                'description': 'Machine learning library dependencies',
                'compatibility': 'INCOMPATIBLE',
                'thread_safety': 'HIGH',
                'severity': 'CRITICAL'
            },
            'authentication': {
                'libraries': ['python-jose', 'passlib', 'pyjwt', 'bcrypt'],
                'description': 'Authentication library dependencies',
                'compatibility': 'PARTIAL',
                'thread_safety': 'MEDIUM',
                'severity': 'HIGH'
            },
            'monitoring': {
                'libraries': ['prometheus_client', 'grafana', 'jaeger'],
                'description': 'Monitoring library dependencies',
                'compatibility': 'PARTIAL',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'testing': {
                'libraries': ['pytest', 'locust', 'coverage'],
                'description': 'Testing framework dependencies',
                'compatibility': 'COMPATIBLE',
                'thread_safety': 'LOW',
                'severity': 'LOW'
            },
            'utilities': {
                'libraries': ['requests', 'httpx', 'pydantic', 'click'],
                'description': 'Utility library dependencies',
                'compatibility': 'PARTIAL',
                'thread_safety': 'LOW',
                'severity': 'MEDIUM'
            },
            'documentation': {
                'libraries': ['mkdocs', 'sphinx'],
                'description': 'Documentation library dependencies',
                'compatibility': 'COMPATIBLE',
                'thread_safety': 'LOW',
                'severity': 'LOW'
            }
        }
    
    def scan_directory(self, directory: str) -> DetectionResult:
        """Scan a directory for external dependency compatibility issues."""
        directory_path = Path(directory)
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        total_files = 0
        files_with_dependencies = 0
        
        for file_path in directory_path.rglob("*.py"):
            if self._should_skip_file(file_path):
                continue
            
            total_files += 1
            file_features = self.scan_file(file_path)
            
            if file_features:
                files_with_dependencies += 1
                self.dependency_features.extend(file_features)
        
        return self._generate_result(total_files, files_with_dependencies)
    
    def scan_file(self, file_path: Path) -> List[DependencyFeature]:
        """Scan a single file for external dependency compatibility issues."""
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
    
    def _analyze_node(self, node: ast.AST, file_path: Path, content: str) -> List[DependencyFeature]:
        """Analyze a single AST node for external dependency compatibility issues."""
        features = []
        
        # Check for import statements
        if isinstance(node, ast.Import):
            features.extend(self._check_import(node, file_path, content))
        
        # Check for from import statements
        elif isinstance(node, ast.ImportFrom):
            features.extend(self._check_import_from(node, file_path, content))
        
        return features
    
    def _check_import(self, node: ast.Import, file_path: Path, content: str) -> List[DependencyFeature]:
        """Check import statements for external dependencies."""
        features = []
        
        for alias in node.names:
            module_name = alias.name.split('.')[0]  # Get the root module name
            
            for category, config in self.dependency_categories.items():
                if module_name.lower() in [lib.lower() for lib in config['libraries']]:
                    features.append(self._create_feature(
                        module_name,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        self._get_code_snippet(content, node.lineno, node.col_offset),
                        f"{category}: {module_name}",
                        str(config['compatibility']),
                        str(config['thread_safety']),
                        f"External {category} dependency",
                        self._get_mitigation_strategy(config['compatibility'], module_name),
                        str(config['severity'])
                    ))
        
        return features
    
    def _check_import_from(self, node: ast.ImportFrom, file_path: Path, content: str) -> List[DependencyFeature]:
        """Check from import statements for external dependencies."""
        features = []
        
        if node.module:
            module_name = node.module.split('.')[0]  # Get the root module name
            
            for category, config in self.dependency_categories.items():
                if module_name.lower() in [lib.lower() for lib in config['libraries']]:
                    features.append(self._create_feature(
                        module_name,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        self._get_code_snippet(content, node.lineno, node.col_offset),
                        f"{category}: {module_name}",
                        str(config['compatibility']),
                        str(config['thread_safety']),
                        f"External {category} dependency",
                        self._get_mitigation_strategy(config['compatibility'], module_name),
                        str(config['severity'])
                    ))
        
        return features
    
    def _get_mitigation_strategy(self, compatibility: str, module_name: str) -> str:
        """Get mitigation strategy based on compatibility status."""
        if compatibility == 'COMPATIBLE':
            return f"Use {module_name} directly in Codon"
        elif compatibility == 'PARTIAL':
            return f"Use Python interoperability for {module_name}: @python decorator"
        elif compatibility == 'INCOMPATIBLE':
            return f"Replace {module_name} with Codon-compatible alternative or use Python interoperability"
        else:
            return f"Test {module_name} compatibility with Codon or use Python interoperability"
    
    def _create_feature(self, dependency_name: str, file_path: Path, line: int, 
                        column: int, code_snippet: str, description: str,
                        compatibility_status: str, thread_safety: str, 
                        business_justification: str, mitigation_strategy: str, 
                        severity: str) -> DependencyFeature:
        """Create a DependencyFeature instance."""
        return DependencyFeature(
            dependency_name=dependency_name,
            file_path=str(file_path),
            line_number=line,
            column=column,
            code_snippet=code_snippet,
            description=description,
            compatibility_status=compatibility_status,
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
    
    def _generate_result(self, total_files: int, files_with_dependencies: int) -> DetectionResult:
        """Generate detection result summary."""
        dependencies_by_category = {}
        dependencies_by_compatibility = {}
        thread_safety_issues = 0
        critical_issues = 0
        
        for feature in self.dependency_features:
            # Extract category from description
            category = feature.description.split(':')[0] if ':' in feature.description else 'unknown'
            dependencies_by_category[category] = dependencies_by_category.get(category, 0) + 1
            
            # Count by compatibility
            dependencies_by_compatibility[feature.compatibility_status] = dependencies_by_compatibility.get(feature.compatibility_status, 0) + 1
            
            # Count thread safety issues
            if feature.thread_safety_impact in ['HIGH', 'CRITICAL']:
                thread_safety_issues += 1
            
            # Count critical issues
            if feature.severity == 'CRITICAL':
                critical_issues += 1
        
        return DetectionResult(
            total_files_scanned=total_files,
            files_with_dependencies=files_with_dependencies,
            total_dependencies=len(self.dependency_features),
            dependencies_by_category=dependencies_by_category,
            dependencies_by_compatibility=dependencies_by_compatibility,
            thread_safety_issues=thread_safety_issues,
            critical_issues=critical_issues
        )

def generate_report(detector: DependencyCompatibilityDetector, result: DetectionResult, 
                    output_file: Optional[str] = None) -> None:
    """Generate a comprehensive report of dependency compatibility issues."""
    
    report = {
        'scan_timestamp': result.scan_timestamp.isoformat(),
        'summary': {
            'total_files_scanned': result.total_files_scanned,
            'files_with_dependencies': result.files_with_dependencies,
            'total_dependencies': result.total_dependencies,
            'thread_safety_issues': result.thread_safety_issues,
            'critical_issues': result.critical_issues
        },
        'dependencies_by_category': result.dependencies_by_category,
        'dependencies_by_compatibility': result.dependencies_by_compatibility,
        'detailed_dependencies': [
            {
                'dependency_name': f.dependency_name,
                'file_path': f.file_path,
                'line_number': f.line_number,
                'column': f.column,
                'code_snippet': f.code_snippet,
                'description': f.description,
                'compatibility_status': f.compatibility_status,
                'thread_safety_impact': f.thread_safety_impact,
                'business_justification': f.business_justification,
                'mitigation_strategy': f.mitigation_strategy,
                'severity': f.severity
            }
            for f in detector.dependency_features
        ]
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_file}")
    else:
        print(json.dumps(report, indent=2))

def main():
    """Main function for the dependency compatibility detector."""
    parser = argparse.ArgumentParser(description='Detect external dependency compatibility issues for Codon')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan (default: current directory)')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--report-only', action='store_true', help='Generate report from previous scan')
    parser.add_argument('--thread-safety', action='store_true', help='Focus on thread safety issues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    detector = DependencyCompatibilityDetector()
    
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
        print(f"\n=== External Dependency Compatibility Detection Summary ===")
        print(f"Files scanned: {result.total_files_scanned}")
        print(f"Files with dependencies: {result.files_with_dependencies}")
        print(f"Total dependencies found: {result.total_dependencies}")
        print(f"Thread safety issues: {result.thread_safety_issues}")
        print(f"Critical issues: {result.critical_issues}")
        
        if result.dependencies_by_category:
            print(f"\nDependencies by category:")
            for category, count in result.dependencies_by_category.items():
                print(f"  {category}: {count}")
        
        if result.dependencies_by_compatibility:
            print(f"\nDependencies by compatibility:")
            for compatibility, count in result.dependencies_by_compatibility.items():
                print(f"  {compatibility}: {count}")
        
        # Generate detailed report
        if args.output or args.thread_safety:
            generate_report(detector, result, args.output)
        
        # Show critical issues
        if detector.dependency_features:
            print(f"\n=== Critical Dependency Issues ===")
            for feature in detector.dependency_features:
                if feature.severity == 'CRITICAL':
                    print(f"\nFile: {feature.file_path}:{feature.line_number}")
                    print(f"Dependency: {feature.dependency_name}")
                    print(f"Category: {feature.description}")
                    print(f"Compatibility: {feature.compatibility_status}")
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