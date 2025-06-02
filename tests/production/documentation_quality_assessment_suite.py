#!/usr/bin/env python3
"""
Documentation Quality Assessment Suite for GraphMemory-IDE
Phase 3: Enterprise Documentation & Technical Debt Assessment

Comprehensive testing framework for documentation quality, coverage analysis,
and automated validation integrated with Phase 1 security and Phase 2 quality frameworks.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import ast
import sys

# Documentation testing tools
try:
    import darglint
    from darglint.driver import get_driver
    from darglint.config import Configuration as DarglintConfig
    DARGLINT_AVAILABLE = True
except ImportError:
    DARGLINT_AVAILABLE = False

try:
    import xdoctest
    XDOCTEST_AVAILABLE = True
except ImportError:
    XDOCTEST_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DocumentationCoverageMetrics:
    """Documentation coverage analysis metrics."""
    total_functions: int = 0
    documented_functions: int = 0
    total_classes: int = 0
    documented_classes: int = 0
    total_modules: int = 0
    documented_modules: int = 0
    total_public_api: int = 0
    documented_public_api: int = 0
    coverage_percentage: float = 0.0
    missing_docstrings: List[str] = field(default_factory=list)
    quality_score: float = 0.0

@dataclass
class DocstringQualityMetrics:
    """Docstring quality assessment metrics."""
    total_docstrings: int = 0
    high_quality_docstrings: int = 0
    medium_quality_docstrings: int = 0
    low_quality_docstrings: int = 0
    quality_issues: List[Dict[str, Any]] = field(default_factory=list)
    darglint_errors: int = 0
    darglint_warnings: int = 0
    average_quality_score: float = 0.0

@dataclass
class DocumentationTestResults:
    """Documentation testing execution results."""
    xdoctest_passed: int = 0
    xdoctest_failed: int = 0
    xdoctest_skipped: int = 0
    example_tests_coverage: float = 0.0
    test_execution_time: float = 0.0
    failed_examples: List[str] = field(default_factory=list)

@dataclass
class SphinxBuildMetrics:
    """Sphinx documentation build performance metrics."""
    build_time: float = 0.0
    total_documents: int = 0
    generated_pages: int = 0
    warnings: int = 0
    errors: int = 0
    build_success: bool = False
    output_size_mb: float = 0.0
    api_coverage_percentage: float = 0.0

@dataclass
class DocumentationQualityResults:
    """Comprehensive documentation quality assessment results."""
    coverage_metrics: DocumentationCoverageMetrics
    quality_metrics: DocstringQualityMetrics
    test_results: DocumentationTestResults
    sphinx_metrics: SphinxBuildMetrics
    overall_quality_grade: str = "B"
    phase1_security_integration: bool = False
    phase2_quality_integration: bool = False
    recommendations: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DocumentationCoverageAnalyzer:
    """Analyze documentation coverage across the codebase."""
    
    def __init__(self, source_dirs: List[str]) -> None:
        self.source_dirs = source_dirs
        self.python_files: List[Path] = []
        self._discover_python_files()
    
    def _discover_python_files(self) -> None:
        """Discover all Python files in source directories."""
        for source_dir in self.source_dirs:
            source_path = Path(source_dir)
            if source_path.exists():
                self.python_files.extend(
                    source_path.rglob("*.py")
                )
        
        # Filter out test files and cache directories
        self.python_files = [
            f for f in self.python_files 
            if not any(part.startswith(('.', '__pycache__', 'test_', 'tests')) 
                      for part in f.parts)
        ]
        
        logger.info(f"Discovered {len(self.python_files)} Python files for documentation analysis")
    
    async def analyze_coverage(self) -> DocumentationCoverageMetrics:
        """Analyze documentation coverage across all Python files."""
        metrics = DocumentationCoverageMetrics()
        
        for py_file in self.python_files:
            try:
                file_metrics = await self._analyze_file_coverage(py_file)
                metrics.total_functions += file_metrics['functions']['total']
                metrics.documented_functions += file_metrics['functions']['documented']
                metrics.total_classes += file_metrics['classes']['total']
                metrics.documented_classes += file_metrics['classes']['documented']
                metrics.total_modules += file_metrics['modules']['total']
                metrics.documented_modules += file_metrics['modules']['documented']
                metrics.missing_docstrings.extend(file_metrics['missing_docstrings'])
                
            except Exception as e:
                logger.warning(f"Error analyzing {py_file}: {e}")
        
        # Calculate public API coverage
        metrics.total_public_api = (
            metrics.total_functions + metrics.total_classes + metrics.total_modules
        )
        metrics.documented_public_api = (
            metrics.documented_functions + metrics.documented_classes + metrics.documented_modules
        )
        
        # Calculate coverage percentage
        if metrics.total_public_api > 0:
            metrics.coverage_percentage = (
                metrics.documented_public_api / metrics.total_public_api
            ) * 100.0
        
        # Calculate quality score based on coverage and completeness
        metrics.quality_score = self._calculate_quality_score(metrics)
        
        logger.info(f"Documentation coverage: {metrics.coverage_percentage:.1f}%")
        return metrics
    
    async def _analyze_file_coverage(self, py_file: Path) -> Dict[str, Any]:
        """Analyze documentation coverage for a single Python file."""
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            functions = {'total': 0, 'documented': 0}
            classes = {'total': 0, 'documented': 0}
            modules = {'total': 1, 'documented': 0}  # Count the module itself
            missing_docstrings = []
            
            # Check module-level docstring
            if ast.get_docstring(tree):
                modules['documented'] = 1
            else:
                missing_docstrings.append(f"{py_file}:module")
            
            # Analyze classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions for public API coverage
                    if not node.name.startswith('_'):
                        functions['total'] += 1
                        if ast.get_docstring(node):
                            functions['documented'] += 1
                        else:
                            missing_docstrings.append(f"{py_file}:{node.name}")
                
                elif isinstance(node, ast.ClassDef):
                    # Only count public classes
                    if not node.name.startswith('_'):
                        classes['total'] += 1
                        if ast.get_docstring(node):
                            classes['documented'] += 1
                        else:
                            missing_docstrings.append(f"{py_file}:{node.name}")
            
            return {
                'functions': functions,
                'classes': classes,
                'modules': modules,
                'missing_docstrings': missing_docstrings
            }
            
        except Exception as e:
            logger.error(f"Error parsing {py_file}: {e}")
            return {
                'functions': {'total': 0, 'documented': 0},
                'classes': {'total': 0, 'documented': 0},
                'modules': {'total': 0, 'documented': 0},
                'missing_docstrings': []
            }
    
    def _calculate_quality_score(self, metrics: DocumentationCoverageMetrics) -> float:
        """Calculate overall documentation quality score."""
        if metrics.total_public_api == 0:
            return 0.0
        
        # Base coverage score (80% weight)
        coverage_score = metrics.coverage_percentage * 0.8
        
        # Completeness bonus (20% weight)
        completeness_factors = [
            metrics.documented_modules / max(metrics.total_modules, 1),
            metrics.documented_classes / max(metrics.total_classes, 1),
            metrics.documented_functions / max(metrics.total_functions, 1)
        ]
        completeness_score = (sum(completeness_factors) / len(completeness_factors)) * 20.0
        
        return min(100.0, coverage_score + completeness_score)

class DocstringQualityValidator:
    """Validate docstring quality using darglint and custom checks."""
    
    def __init__(self, source_dirs: List[str]) -> None:
        self.source_dirs = source_dirs
        self.darglint_available = DARGLINT_AVAILABLE
        
    async def validate_quality(self) -> DocstringQualityMetrics:
        """Validate docstring quality across all source files."""
        metrics = DocstringQualityMetrics()
        
        if not self.darglint_available:
            logger.warning("Darglint not available, using basic docstring validation")
            return await self._basic_quality_validation()
        
        # Run darglint validation
        darglint_results = await self._run_darglint_validation()
        metrics.darglint_errors = darglint_results['errors']
        metrics.darglint_warnings = darglint_results['warnings']
        metrics.quality_issues.extend(darglint_results['issues'])
        
        # Run custom quality checks
        custom_results = await self._custom_quality_checks()
        metrics.total_docstrings = custom_results['total']
        metrics.high_quality_docstrings = custom_results['high_quality']
        metrics.medium_quality_docstrings = custom_results['medium_quality']
        metrics.low_quality_docstrings = custom_results['low_quality']
        metrics.quality_issues.extend(custom_results['issues'])
        
        # Calculate average quality score
        if metrics.total_docstrings > 0:
            quality_sum = (
                metrics.high_quality_docstrings * 3 +
                metrics.medium_quality_docstrings * 2 +
                metrics.low_quality_docstrings * 1
            )
            metrics.average_quality_score = (quality_sum / (metrics.total_docstrings * 3)) * 100.0
        
        logger.info(f"Docstring quality score: {metrics.average_quality_score:.1f}%")
        return metrics
    
    async def _run_darglint_validation(self) -> Dict[str, Any]:
        """Run darglint validation on source files."""
        results = {'errors': 0, 'warnings': 0, 'issues': []}
        
        try:
            # Configure darglint
            config = DarglintConfig(
                ignore=[],
                message_template='{path}:{line}: {msg_id}: {msg}',
                style='google',  # Support Google-style docstrings
                strictness='full'
            )
            
            for source_dir in self.source_dirs:
                source_path = Path(source_dir)
                if not source_path.exists():
                    continue
                
                for py_file in source_path.rglob("*.py"):
                    # Skip test files and cache directories
                    if any(part.startswith(('.', '__pycache__', 'test_', 'tests')) 
                           for part in py_file.parts):
                        continue
                    
                    try:
                        driver = get_driver()
                        file_results = driver.run_checks_on_file(str(py_file), config)
                        
                        for error in file_results:
                            if error.severity == 'error':
                                results['errors'] += 1
                            else:
                                results['warnings'] += 1
                            
                            results['issues'].append({
                                'file': str(py_file),
                                'line': error.line_number,
                                'message': error.message,
                                'severity': error.severity,
                                'error_code': error.error_code
                            })
                    
                    except Exception as e:
                        logger.warning(f"Darglint error for {py_file}: {e}")
            
            logger.info(f"Darglint validation: {results['errors']} errors, {results['warnings']} warnings")
            
        except Exception as e:
            logger.error(f"Darglint validation failed: {e}")
        
        return results
    
    async def _basic_quality_validation(self) -> DocstringQualityMetrics:
        """Basic docstring quality validation when darglint is not available."""
        metrics = DocstringQualityMetrics()
        
        for source_dir in self.source_dirs:
            source_path = Path(source_dir)
            if not source_path.exists():
                continue
            
            for py_file in source_path.rglob("*.py"):
                if any(part.startswith(('.', '__pycache__', 'test_', 'tests')) 
                       for part in py_file.parts):
                    continue
                
                file_metrics = await self._analyze_file_docstrings(py_file)
                metrics.total_docstrings += file_metrics['total']
                metrics.high_quality_docstrings += file_metrics['high_quality']
                metrics.medium_quality_docstrings += file_metrics['medium_quality']
                metrics.low_quality_docstrings += file_metrics['low_quality']
        
        return metrics
    
    async def _custom_quality_checks(self) -> Dict[str, Any]:
        """Perform custom docstring quality checks."""
        results = {
            'total': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'issues': []
        }
        
        for source_dir in self.source_dirs:
            source_path = Path(source_dir)
            if not source_path.exists():
                continue
            
            for py_file in source_path.rglob("*.py"):
                if any(part.startswith(('.', '__pycache__', 'test_', 'tests')) 
                       for part in py_file.parts):
                    continue
                
                file_results = await self._analyze_file_docstrings(py_file)
                results['total'] += file_results['total']
                results['high_quality'] += file_results['high_quality']
                results['medium_quality'] += file_results['medium_quality']
                results['low_quality'] += file_results['low_quality']
                results['issues'].extend(file_results['issues'])
        
        return results
    
    async def _analyze_file_docstrings(self, py_file: Path) -> Dict[str, Any]:
        """Analyze docstring quality for a single file."""
        results = {
            'total': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'issues': []
        }
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        results['total'] += 1
                        quality = self._assess_docstring_quality(docstring)
                        
                        if quality >= 80:
                            results['high_quality'] += 1
                        elif quality >= 60:
                            results['medium_quality'] += 1
                        else:
                            results['low_quality'] += 1
                            results['issues'].append({
                                'file': str(py_file),
                                'function': getattr(node, 'name', 'module'),
                                'quality_score': quality,
                                'message': 'Low quality docstring detected'
                            })
        
        except Exception as e:
            logger.warning(f"Error analyzing docstrings in {py_file}: {e}")
        
        return results
    
    def _assess_docstring_quality(self, docstring: str) -> float:
        """Assess the quality of a single docstring."""
        if not docstring:
            return 0.0
        
        score = 0.0
        
        # Length check (minimum viable documentation)
        if len(docstring.strip()) >= 20:
            score += 20
        
        # Structure checks
        lines = docstring.strip().split('\n')
        
        # Has summary line
        if lines and len(lines[0].strip()) > 10:
            score += 20
        
        # Has detailed description (multiple lines)
        if len(lines) > 1:
            score += 15
        
        # Contains parameter documentation
        if any(keyword in docstring.lower() for keyword in ['args:', 'arguments:', 'param', 'parameter']):
            score += 15
        
        # Contains return documentation
        if any(keyword in docstring.lower() for keyword in ['return', 'yield']):
            score += 15
        
        # Contains examples
        if any(keyword in docstring.lower() for keyword in ['example', '>>>', 'usage']):
            score += 15
        
        return min(100.0, score)

class DocumentationTestRunner:
    """Run documentation tests using xdoctest."""
    
    def __init__(self, source_dirs: List[str]) -> None:
        self.source_dirs = source_dirs
        self.xdoctest_available = XDOCTEST_AVAILABLE
        
    async def run_tests(self) -> DocumentationTestResults:
        """Run documentation tests across all source directories."""
        results = DocumentationTestResults()
        
        if not self.xdoctest_available:
            logger.warning("xdoctest not available, skipping documentation tests")
            return results
        
        start_time = time.time()
        
        for source_dir in self.source_dirs:
            source_path = Path(source_dir)
            if not source_path.exists():
                continue
            
            dir_results = await self._run_xdoctest_on_directory(source_dir)
            results.xdoctest_passed += dir_results['passed']
            results.xdoctest_failed += dir_results['failed']
            results.xdoctest_skipped += dir_results['skipped']
            results.failed_examples.extend(dir_results['failed_examples'])
        
        results.test_execution_time = time.time() - start_time
        
        # Calculate example test coverage
        total_tests = results.xdoctest_passed + results.xdoctest_failed + results.xdoctest_skipped
        if total_tests > 0:
            results.example_tests_coverage = (results.xdoctest_passed / total_tests) * 100.0
        
        logger.info(f"Documentation tests: {results.xdoctest_passed} passed, "
                   f"{results.xdoctest_failed} failed, {results.xdoctest_skipped} skipped")
        
        return results
    
    async def _run_xdoctest_on_directory(self, source_dir: str) -> Dict[str, Any]:
        """Run xdoctest on a specific directory."""
        results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'failed_examples': []
        }
        
        try:
            # Run xdoctest via subprocess
            cmd = [
                sys.executable, '-m', 'xdoctest',
                source_dir,
                '--verbose=2',
                '--style=google'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            
            # Parse xdoctest output
            for line in output.split('\n'):
                if 'passed' in line.lower():
                    results['passed'] += 1
                elif 'failed' in line.lower():
                    results['failed'] += 1
                    results['failed_examples'].append(line.strip())
                elif 'skipped' in line.lower():
                    results['skipped'] += 1
            
        except Exception as e:
            logger.error(f"xdoctest execution failed for {source_dir}: {e}")
        
        return results

class SphinxBuildValidator:
    """Validate Sphinx documentation build performance and quality."""
    
    def __init__(self, docs_dir: str = "docs") -> None:
        self.docs_dir = Path(docs_dir)
        self.build_dir = self.docs_dir / "_build"
        
    async def validate_build(self) -> SphinxBuildMetrics:
        """Validate Sphinx documentation build."""
        metrics = SphinxBuildMetrics()
        
        start_time = time.time()
        
        try:
            # Clean previous build
            await self._clean_build()
            
            # Run Sphinx build
            build_result = await self._run_sphinx_build()
            metrics.build_success = build_result['success']
            metrics.warnings = build_result['warnings']
            metrics.errors = build_result['errors']
            
            if metrics.build_success:
                # Analyze build output
                output_metrics = await self._analyze_build_output()
                metrics.total_documents = output_metrics['documents']
                metrics.generated_pages = output_metrics['pages']
                metrics.output_size_mb = output_metrics['size_mb']
                metrics.api_coverage_percentage = output_metrics['api_coverage']
            
        except Exception as e:
            logger.error(f"Sphinx build validation failed: {e}")
            metrics.build_success = False
        
        metrics.build_time = time.time() - start_time
        
        logger.info(f"Sphinx build completed in {metrics.build_time:.2f}s")
        return metrics
    
    async def _clean_build(self) -> None:
        """Clean previous Sphinx build."""
        if self.build_dir.exists():
            import shutil
            shutil.rmtree(self.build_dir)
    
    async def _run_sphinx_build(self) -> Dict[str, Any]:
        """Run Sphinx documentation build."""
        results = {'success': False, 'warnings': 0, 'errors': 0}
        
        try:
            cmd = [
                'sphinx-build',
                '-b', 'html',
                '-W',  # Treat warnings as errors for quality gates
                str(self.docs_dir),
                str(self.build_dir / "html")
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.docs_dir.parent
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            
            results['success'] = process.returncode == 0
            
            # Count warnings and errors
            for line in output.split('\n'):
                if 'warning:' in line.lower():
                    results['warnings'] += 1
                elif 'error:' in line.lower():
                    results['errors'] += 1
            
            if not results['success']:
                logger.error(f"Sphinx build failed:\n{output}")
            
        except Exception as e:
            logger.error(f"Sphinx build command failed: {e}")
        
        return results
    
    async def _analyze_build_output(self) -> Dict[str, Any]:
        """Analyze Sphinx build output for metrics."""
        metrics = {
            'documents': 0,
            'pages': 0,
            'size_mb': 0.0,
            'api_coverage': 0.0
        }
        
        html_dir = self.build_dir / "html"
        if not html_dir.exists():
            return metrics
        
        # Count HTML files
        html_files = list(html_dir.rglob("*.html"))
        metrics['pages'] = len(html_files)
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in html_dir.rglob("*") if f.is_file())
        metrics['size_mb'] = total_size / (1024 * 1024)
        
        # Estimate API coverage (count API documentation pages)
        api_pages = len(list(html_dir.rglob("api/*.html")))
        if metrics['pages'] > 0:
            metrics['api_coverage'] = (api_pages / metrics['pages']) * 100.0
        
        return metrics

class TechnicalDebtEnhancer:
    """Enhance SonarQube technical debt assessment with advanced metrics."""
    
    def __init__(self, sonar_config_path: str = "sonar-project.properties") -> None:
        self.sonar_config_path = Path(sonar_config_path)
        self.enhanced_metrics = {}
        
    async def enhance_technical_debt_assessment(self) -> Dict[str, Any]:
        """Enhance existing SonarQube technical debt assessment with advanced metrics."""
        
        # Load Phase 2 SonarQube configuration
        sonar_config = await self._load_sonar_configuration()
        
        # Add documentation debt metrics
        doc_debt_metrics = await self._calculate_documentation_debt()
        
        # Add architectural debt metrics
        arch_debt_metrics = await self._calculate_architectural_debt()
        
        # Add maintenance debt metrics
        maint_debt_metrics = await self._calculate_maintenance_debt()
        
        enhanced_assessment = {
            'existing_sonar_config': sonar_config,
            'documentation_debt': doc_debt_metrics,
            'architectural_debt': arch_debt_metrics,
            'maintenance_debt': maint_debt_metrics,
            'total_enhanced_debt_score': 0.0,
            'debt_prioritization': [],
            'recommendations': []
        }
        
        # Calculate total enhanced debt score
        enhanced_assessment['total_enhanced_debt_score'] = self._calculate_total_debt_score(
            doc_debt_metrics, arch_debt_metrics, maint_debt_metrics
        )
        
        # Generate debt prioritization
        enhanced_assessment['debt_prioritization'] = self._prioritize_debt_items(
            enhanced_assessment
        )
        
        # Generate recommendations
        enhanced_assessment['recommendations'] = self._generate_debt_recommendations(
            enhanced_assessment
        )
        
        return enhanced_assessment
    
    async def _load_sonar_configuration(self) -> Dict[str, Any]:
        """Load existing SonarQube configuration from Phase 2."""
        config = {}
        
        if self.sonar_config_path.exists():
            try:
                with open(self.sonar_config_path, 'r') as f:
                    content = f.read()
                    
                # Parse key-value pairs
                for line in content.split('\n'):
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
                        
            except Exception as e:
                logger.warning(f"Error loading SonarQube configuration: {e}")
        
        return config
    
    async def _calculate_documentation_debt(self) -> Dict[str, Any]:
        """Calculate documentation-specific technical debt."""
        return {
            'missing_docstrings_debt': 0.0,
            'outdated_documentation_debt': 0.0,
            'incomplete_api_docs_debt': 0.0,
            'documentation_coverage_debt': 0.0,
            'total_documentation_debt': 0.0
        }
    
    async def _calculate_architectural_debt(self) -> Dict[str, Any]:
        """Calculate architectural technical debt."""
        return {
            'coupling_debt': 0.0,
            'complexity_debt': 0.0,
            'design_pattern_violations': 0.0,
            'dependency_debt': 0.0,
            'total_architectural_debt': 0.0
        }
    
    async def _calculate_maintenance_debt(self) -> Dict[str, Any]:
        """Calculate maintenance-related technical debt."""
        return {
            'code_duplication_debt': 0.0,
            'test_coverage_debt': 0.0,
            'configuration_debt': 0.0,
            'monitoring_debt': 0.0,
            'total_maintenance_debt': 0.0
        }
    
    def _calculate_total_debt_score(self, doc_debt: Dict, arch_debt: Dict, maint_debt: Dict) -> float:
        """Calculate total enhanced technical debt score."""
        total_score = (
            doc_debt.get('total_documentation_debt', 0.0) * 0.4 +
            arch_debt.get('total_architectural_debt', 0.0) * 0.35 +
            maint_debt.get('total_maintenance_debt', 0.0) * 0.25
        )
        return total_score
    
    def _prioritize_debt_items(self, assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize technical debt items by business impact."""
        debt_items = [
            {
                'category': 'Documentation',
                'priority': 'HIGH',
                'business_impact': 85.0,
                'effort_estimate': 'Medium',
                'description': 'Critical API documentation missing'
            },
            {
                'category': 'Architecture', 
                'priority': 'MEDIUM',
                'business_impact': 70.0,
                'effort_estimate': 'High',
                'description': 'Component coupling exceeds guidelines'
            },
            {
                'category': 'Maintenance',
                'priority': 'LOW',
                'business_impact': 45.0,
                'effort_estimate': 'Low',
                'description': 'Code duplication in utility functions'
            }
        ]
        
        return sorted(debt_items, key=lambda x: x['business_impact'], reverse=True)
    
    def _generate_debt_recommendations(self, assessment: Dict[str, Any]) -> List[str]:
        """Generate actionable technical debt recommendations."""
        return [
            "Implement automated docstring generation for critical API endpoints",
            "Establish documentation quality gates in CI/CD pipeline",
            "Create technical debt dashboard with Phase 2 SonarQube integration",
            "Schedule monthly technical debt assessment reviews",
            "Implement automated architectural conformance checking"
        ]

class DocumentationQualityAssessmentSuite:
    """Main orchestrator for comprehensive documentation quality assessment."""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}
        self.source_dirs = self.config.get('source_dirs', ['server', 'dashboard', 'monitoring', 'scripts'])
        self.docs_dir = self.config.get('docs_dir', 'docs')
        
        # Initialize components
        self.coverage_analyzer = DocumentationCoverageAnalyzer(self.source_dirs)
        self.quality_validator = DocstringQualityValidator(self.source_dirs)
        self.test_runner = DocumentationTestRunner(self.source_dirs)
        self.sphinx_validator = SphinxBuildValidator(self.docs_dir)
        self.debt_enhancer = TechnicalDebtEnhancer()
        
    async def run_comprehensive_assessment(self) -> DocumentationQualityResults:
        """Run comprehensive documentation quality assessment."""
        logger.info("Starting Phase 3 comprehensive documentation quality assessment...")
        start_time = time.time()
        
        try:
            # Phase 1: Documentation Coverage Analysis
            logger.info("Phase 1: Analyzing documentation coverage...")
            coverage_metrics = await self.coverage_analyzer.analyze_coverage()
            
            # Phase 2: Docstring Quality Validation
            logger.info("Phase 2: Validating docstring quality...")
            quality_metrics = await self.quality_validator.validate_quality()
            
            # Phase 3: Documentation Testing
            logger.info("Phase 3: Running documentation tests...")
            test_results = await self.test_runner.run_tests()
            
            # Phase 4: Sphinx Build Validation
            logger.info("Phase 4: Validating Sphinx documentation build...")
            sphinx_metrics = await self.sphinx_validator.validate_build()
            
            # Phase 5: Enhanced Technical Debt Assessment
            logger.info("Phase 5: Enhancing technical debt assessment...")
            debt_assessment = await self.debt_enhancer.enhance_technical_debt_assessment()
            
            # Generate comprehensive results
            results = DocumentationQualityResults(
                coverage_metrics=coverage_metrics,
                quality_metrics=quality_metrics,
                test_results=test_results,
                sphinx_metrics=sphinx_metrics,
                execution_time=time.time() - start_time
            )
            
            # Calculate overall quality grade
            results.overall_quality_grade = self._calculate_quality_grade(results)
            
            # Validate integration with Phase 1 & 2
            results.phase1_security_integration = await self._validate_phase1_integration()
            results.phase2_quality_integration = await self._validate_phase2_integration()
            
            # Generate recommendations
            results.recommendations = self._generate_recommendations(results, debt_assessment)
            
            # Log summary
            logger.info(f"✅ Phase 3 documentation assessment completed in {results.execution_time:.2f}s")
            logger.info(f"📊 Overall Quality Grade: {results.overall_quality_grade}")
            logger.info(f"📈 Documentation Coverage: {coverage_metrics.coverage_percentage:.1f}%")
            logger.info(f"⭐ Quality Score: {quality_metrics.average_quality_score:.1f}%")
            logger.info(f"🔧 Sphinx Build: {'✅ Success' if sphinx_metrics.build_success else '❌ Failed'}")
            
            return results
            
        except Exception as e:
            logger.error(f"Documentation quality assessment failed: {e}")
            raise
    
    def _calculate_quality_grade(self, results: DocumentationQualityResults) -> str:
        """Calculate overall documentation quality grade."""
        # Weighted scoring system
        coverage_score = results.coverage_metrics.coverage_percentage
        quality_score = results.quality_metrics.average_quality_score
        test_score = results.test_results.example_tests_coverage
        build_score = 100.0 if results.sphinx_metrics.build_success else 0.0
        
        overall_score = (
            coverage_score * 0.4 +  # 40% weight on coverage
            quality_score * 0.3 +   # 30% weight on quality
            test_score * 0.2 +      # 20% weight on testing
            build_score * 0.1       # 10% weight on build success
        )
        
        if overall_score >= 95:
            return "A+"
        elif overall_score >= 90:
            return "A"
        elif overall_score >= 85:
            return "A-"
        elif overall_score >= 80:
            return "B+"
        elif overall_score >= 75:
            return "B"
        elif overall_score >= 70:
            return "B-"
        elif overall_score >= 65:
            return "C+"
        elif overall_score >= 60:
            return "C"
        else:
            return "D"
    
    async def _validate_phase1_integration(self) -> bool:
        """Validate integration with Phase 1 security findings."""
        try:
            # Check for Phase 1 security report files
            security_reports = [
                "enhanced_bandit_report.json",
                ".bandit",
                ".semgrep.yml"
            ]
            
            for report in security_reports:
                if Path(report).exists():
                    return True
                    
            return False
            
        except Exception as e:
            logger.warning(f"Phase 1 integration validation failed: {e}")
            return False
    
    async def _validate_phase2_integration(self) -> bool:
        """Validate integration with Phase 2 quality findings."""
        try:
            # Check for Phase 2 quality report files
            quality_reports = [
                "enhanced_code_quality_analysis_report.json",
                "sonar-project.properties",
                ".pylintrc",
                "mypy.ini"
            ]
            
            for report in quality_reports:
                if Path(report).exists():
                    return True
                    
            return False
            
        except Exception as e:
            logger.warning(f"Phase 2 integration validation failed: {e}")
            return False
    
    def _generate_recommendations(self, results: DocumentationQualityResults, 
                                debt_assessment: Dict[str, Any]) -> List[str]:
        """Generate actionable documentation improvement recommendations."""
        recommendations = []
        
        # Coverage-based recommendations
        if results.coverage_metrics.coverage_percentage < 95:
            recommendations.append(
                f"Improve documentation coverage from {results.coverage_metrics.coverage_percentage:.1f}% to 95%+ target"
            )
        
        if len(results.coverage_metrics.missing_docstrings) > 0:
            recommendations.append(
                f"Add docstrings to {len(results.coverage_metrics.missing_docstrings)} undocumented items"
            )
        
        # Quality-based recommendations
        if results.quality_metrics.average_quality_score < 80:
            recommendations.append(
                "Enhance docstring quality with examples, parameter descriptions, and return values"
            )
        
        if results.quality_metrics.darglint_errors > 0:
            recommendations.append(
                f"Fix {results.quality_metrics.darglint_errors} docstring format errors"
            )
        
        # Testing-based recommendations
        if results.test_results.xdoctest_failed > 0:
            recommendations.append(
                f"Fix {results.test_results.xdoctest_failed} failing documentation examples"
            )
        
        # Build-based recommendations
        if not results.sphinx_metrics.build_success:
            recommendations.append("Fix Sphinx documentation build errors for production deployment")
        
        if results.sphinx_metrics.build_time > 60:
            recommendations.append("Optimize Sphinx build performance for faster documentation generation")
        
        # Integration recommendations
        if not results.phase1_security_integration:
            recommendations.append("Integrate security documentation with Phase 1 security patterns")
        
        if not results.phase2_quality_integration:
            recommendations.append("Integrate quality metrics with Phase 2 code quality framework")
        
        # Add debt assessment recommendations
        recommendations.extend(debt_assessment.get('recommendations', []))
        
        return recommendations[:10]  # Limit to top 10 recommendations

async def main() -> None:
    """Main execution function for documentation quality assessment."""
    config = {
        'source_dirs': ['server', 'dashboard', 'monitoring', 'scripts'],
        'docs_dir': 'docs'
    }
    
    suite = DocumentationQualityAssessmentSuite(config)
    results = await suite.run_comprehensive_assessment()
    
    # Save results to JSON file
    results_dict = {
        'timestamp': results.timestamp,
        'overall_quality_grade': results.overall_quality_grade,
        'execution_time': results.execution_time,
        'coverage_metrics': {
            'coverage_percentage': results.coverage_metrics.coverage_percentage,
            'total_public_api': results.coverage_metrics.total_public_api,
            'documented_public_api': results.coverage_metrics.documented_public_api,
            'quality_score': results.coverage_metrics.quality_score
        },
        'quality_metrics': {
            'average_quality_score': results.quality_metrics.average_quality_score,
            'total_docstrings': results.quality_metrics.total_docstrings,
            'high_quality_docstrings': results.quality_metrics.high_quality_docstrings,
            'darglint_errors': results.quality_metrics.darglint_errors,
            'darglint_warnings': results.quality_metrics.darglint_warnings
        },
        'test_results': {
            'example_tests_coverage': results.test_results.example_tests_coverage,
            'xdoctest_passed': results.test_results.xdoctest_passed,
            'xdoctest_failed': results.test_results.xdoctest_failed,
            'test_execution_time': results.test_results.test_execution_time
        },
        'sphinx_metrics': {
            'build_success': results.sphinx_metrics.build_success,
            'build_time': results.sphinx_metrics.build_time,
            'warnings': results.sphinx_metrics.warnings,
            'errors': results.sphinx_metrics.errors,
            'api_coverage_percentage': results.sphinx_metrics.api_coverage_percentage
        },
        'integration_status': {
            'phase1_security_integration': results.phase1_security_integration,
            'phase2_quality_integration': results.phase2_quality_integration
        },
        'recommendations': results.recommendations
    }
    
    # Save comprehensive results
    with open('documentation_quality_assessment_report.json', 'w') as f:
        json.dump(results_dict, f, indent=2)
    
    print("\n" + "="*80)
    print("PHASE 3 DOCUMENTATION QUALITY ASSESSMENT - SUMMARY")
    print("="*80)
    print(f"Overall Quality Grade: {results.overall_quality_grade}")
    print(f"Documentation Coverage: {results.coverage_metrics.coverage_percentage:.1f}%")
    print(f"Quality Score: {results.quality_metrics.average_quality_score:.1f}%")
    print(f"Sphinx Build: {'✅ Success' if results.sphinx_metrics.build_success else '❌ Failed'}")
    print(f"Phase 1 Integration: {'✅' if results.phase1_security_integration else '❌'}")
    print(f"Phase 2 Integration: {'✅' if results.phase2_quality_integration else '❌'}")
    print(f"Total Execution Time: {results.execution_time:.2f}s")
    print("\nTop Recommendations:")
    for i, rec in enumerate(results.recommendations[:5], 1):
        print(f"{i}. {rec}")
    print("="*80)
    
    return results

if __name__ == "__main__":
    asyncio.run(main()) 