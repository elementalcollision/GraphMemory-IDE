"""
Codon Dependency Analyzer for Compilation Planning

This module provides comprehensive dependency analysis for Codon compilation planning.
It analyzes all Python files, builds dependency graphs, identifies circular dependencies,
and creates optimal compilation order plans.

Key Features:
- Static import analysis across the entire codebase
- Circular dependency detection and resolution strategies
- Module initialization order planning
- Thread safety assessment at module level
- Codon-specific compilation optimization
"""

import ast
import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of module dependencies"""

    DIRECT_IMPORT = "direct_import"
    CONDITIONAL_IMPORT = "conditional_import"
    DYNAMIC_IMPORT = "dynamic_import"
    PLUGIN_IMPORT = "plugin_import"
    EXTERNAL_IMPORT = "external_import"


class ModuleStatus(Enum):
    """Module compilation status for Codon"""

    CONDON_COMPATIBLE = "codon_compatible"
    CONDON_OPTIMIZABLE = "codon_optimizable"
    CONDON_LIMITED = "codon_limited"
    CONDON_INCOMPATIBLE = "codon_incompatible"


@dataclass
class ModuleInfo:
    """Information about a Python module"""

    path: str
    name: str
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    import_types: Dict[str, DependencyType] = field(default_factory=dict)
    conditional_imports: List[str] = field(default_factory=list)
    dynamic_imports: List[str] = field(default_factory=list)
    external_dependencies: Set[str] = field(default_factory=set)
    thread_safety_issues: List[str] = field(default_factory=list)
    codon_status: ModuleStatus = ModuleStatus.CONDON_COMPATIBLE
    compilation_priority: int = 0
    estimated_compilation_time: float = 0.0


@dataclass
class DependencyGraph:
    """Complete dependency graph for compilation planning"""

    modules: Dict[str, ModuleInfo] = field(default_factory=dict)
    circular_dependencies: List[List[str]] = field(default_factory=list)
    compilation_order: List[str] = field(default_factory=list)
    thread_safety_issues: List[str] = field(default_factory=list)
    codon_optimization_opportunities: List[str] = field(default_factory=list)


class CodonDependencyAnalyzer:
    """Comprehensive dependency analyzer for Codon compilation planning"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.graph = DependencyGraph()
        self.import_patterns = {
            "threading": ["threading", "threading.Lock", "threading.Thread"],
            "asyncio": ["asyncio", "asyncio.Lock", "asyncio.gather"],
            "singleton": ["_instance", "get_instance", "singleton"],
            "global_state": ["global ", "GLOBAL_", "_global"],
            "dynamic_import": ["importlib", "__import__", "getattr"],
            "conditional_import": ["try:", "except ImportError"],
        }

    def analyze_codebase(self) -> DependencyGraph:
        """Analyze the entire codebase for dependencies"""
        logger.info("Starting comprehensive dependency analysis...")

        # Find all Python files
        python_files = self._find_python_files()
        logger.info(f"Found {len(python_files)} Python files")

        # Analyze each file
        for file_path in python_files:
            self._analyze_file(file_path)

        # Build dependency graph
        self._build_dependency_graph()

        # Detect circular dependencies
        self._detect_circular_dependencies()

        # Create compilation order
        self._create_compilation_order()

        # Assess thread safety
        self._assess_thread_safety()

        # Assess Codon compatibility
        self._assess_codon_compatibility()

        logger.info("Dependency analysis completed")
        return self.graph

    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project"""
        python_files = []

        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["__pycache__", "node_modules", "venv"]
            ]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        return python_files

    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for dependencies"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            # Extract module information
            module_name = self._get_module_name(file_path)
            module_info = ModuleInfo(path=str(file_path), name=module_name)

            # Analyze imports
            self._analyze_imports(tree, module_info, content)

            # Analyze thread safety patterns
            self._analyze_thread_safety_patterns(content, module_info)

            # Store module info
            self.graph.modules[module_name] = module_info

        except Exception as e:
            logger.warning(f"Error analyzing {file_path}: {e}")

    def _get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name"""
        relative_path = file_path.relative_to(self.project_root)
        module_name = str(relative_path).replace("/", ".").replace("\\", ".")

        if module_name.endswith(".py"):
            module_name = module_name[:-3]

        return module_name

    def _analyze_imports(
        self, tree: ast.AST, module_info: ModuleInfo, content: str
    ) -> None:
        """Analyze import statements in the AST"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_info.dependencies.add(alias.name)
                    module_info.import_types[alias.name] = DependencyType.DIRECT_IMPORT

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_info.dependencies.add(node.module)
                    module_info.import_types[node.module] = DependencyType.DIRECT_IMPORT

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                    # Dynamic import detection
                    if node.args and isinstance(node.args[0], ast.Constant):
                        module_name = node.args[0].value
                        module_info.dependencies.add(module_name)
                        module_info.import_types[module_name] = (
                            DependencyType.DYNAMIC_IMPORT
                        )
                        module_info.dynamic_imports.append(module_name)

        # Analyze conditional imports from content
        self._analyze_conditional_imports(content, module_info)

    def _analyze_conditional_imports(
        self, content: str, module_info: ModuleInfo
    ) -> None:
        """Analyze conditional import patterns in content"""
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()

            # Check for try/except ImportError patterns
            if line.startswith("try:") or line.startswith("except ImportError"):
                # Look for imports in the next few lines
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith("import ") or next_line.startswith("from "):
                        # Extract module name
                        if next_line.startswith("import "):
                            module_name = next_line[7:].split()[0]
                        else:  # from ... import
                            parts = next_line[5:].split(" import ")
                            if len(parts) == 2:
                                module_name = parts[0].strip()
                            else:
                                continue

                        module_info.dependencies.add(module_name)
                        module_info.import_types[module_name] = (
                            DependencyType.CONDITIONAL_IMPORT
                        )
                        module_info.conditional_imports.append(module_name)
                        break

    def _analyze_thread_safety_patterns(
        self, content: str, module_info: ModuleInfo
    ) -> None:
        """Analyze thread safety patterns in module content"""
        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            # Check for threading patterns
            if any(pattern in line for pattern in self.import_patterns["threading"]):
                module_info.thread_safety_issues.append("Uses threading module")

            # Check for asyncio patterns
            if any(pattern in line for pattern in self.import_patterns["asyncio"]):
                module_info.thread_safety_issues.append("Uses asyncio module")

            # Check for singleton patterns
            if any(pattern in line for pattern in self.import_patterns["singleton"]):
                module_info.thread_safety_issues.append("Uses singleton pattern")

            # Check for global state
            if any(pattern in line for pattern in self.import_patterns["global_state"]):
                module_info.thread_safety_issues.append("Uses global state")

    def _build_dependency_graph(self) -> None:
        """Build the complete dependency graph"""
        # Create NetworkX graph for analysis
        G = nx.DiGraph()

        # Add nodes and edges
        for module_name, module_info in self.graph.modules.items():
            G.add_node(module_name)

            for dep in module_info.dependencies:
                if dep in self.graph.modules:
                    G.add_edge(module_name, dep)
                    # Update dependents
                    self.graph.modules[dep].dependents.add(module_name)

        # Store graph for further analysis
        self.nx_graph = G

    def _detect_circular_dependencies(self) -> None:
        """Detect circular dependencies in the graph"""
        try:
            cycles = list(nx.simple_cycles(self.nx_graph))
            self.graph.circular_dependencies = cycles

            for cycle in cycles:
                logger.warning(f"Circular dependency detected: {' -> '.join(cycle)}")

        except Exception as e:
            logger.error(f"Error detecting circular dependencies: {e}")

    def _create_compilation_order(self) -> None:
        """Create optimal compilation order for Codon"""
        try:
            # Use topological sort for compilation order
            if nx.is_directed_acyclic_graph(self.nx_graph):
                compilation_order = list(nx.topological_sort(self.nx_graph))
                self.graph.compilation_order = compilation_order

                # Assign compilation priorities
                for i, module_name in enumerate(compilation_order):
                    if module_name in self.graph.modules:
                        self.graph.modules[module_name].compilation_priority = i

            else:
                logger.warning(
                    "Graph contains cycles - cannot create complete topological order"
                )
                # Create partial order by removing cycles
                self._create_partial_compilation_order()

        except Exception as e:
            logger.error(f"Error creating compilation order: {e}")

    def _create_partial_compilation_order(self) -> None:
        """Create partial compilation order when cycles exist"""
        # Remove cycles and create partial order
        G_copy = self.nx_graph.copy()

        # Remove edges that create cycles
        for cycle in self.graph.circular_dependencies:
            for i in range(len(cycle)):
                u, v = cycle[i], cycle[(i + 1) % len(cycle)]
                if G_copy.has_edge(u, v):
                    G_copy.remove_edge(u, v)

        # Create partial order
        try:
            partial_order = list(nx.topological_sort(G_copy))
            self.graph.compilation_order = partial_order

            # Assign priorities
            for i, module_name in enumerate(partial_order):
                if module_name in self.graph.modules:
                    self.graph.modules[module_name].compilation_priority = i

        except Exception as e:
            logger.error(f"Error creating partial compilation order: {e}")

    def _assess_thread_safety(self) -> None:
        """Assess thread safety at module level"""
        for module_name, module_info in self.graph.modules.items():
            if module_info.thread_safety_issues:
                self.graph.thread_safety_issues.append(
                    f"Module {module_name}: {', '.join(module_info.thread_safety_issues)}"
                )

    def _assess_codon_compatibility(self) -> None:
        """Assess Codon compatibility for each module"""
        for module_name, module_info in self.graph.modules.items():
            # Check for Codon-incompatible patterns
            incompatibilities = []

            # Check for dynamic imports
            if module_info.dynamic_imports:
                incompatibilities.append("Uses dynamic imports")

            # Check for external dependencies
            if module_info.external_dependencies:
                incompatibilities.append("Uses external dependencies")

            # Check for complex conditional imports
            if len(module_info.conditional_imports) > 5:
                incompatibilities.append("Many conditional imports")

            # Determine Codon status
            if incompatibilities:
                if len(incompatibilities) > 3:
                    module_info.codon_status = ModuleStatus.CONDON_INCOMPATIBLE
                elif len(incompatibilities) > 1:
                    module_info.codon_status = ModuleStatus.CONDON_LIMITED
                else:
                    module_info.codon_status = ModuleStatus.CONDON_OPTIMIZABLE
            else:
                module_info.codon_status = ModuleStatus.CONDON_COMPATIBLE

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive dependency analysis report"""
        report = {
            "summary": {
                "total_modules": len(self.graph.modules),
                "circular_dependencies": len(self.graph.circular_dependencies),
                "thread_safety_issues": len(self.graph.thread_safety_issues),
                "codon_compatible": len(
                    [
                        m
                        for m in self.graph.modules.values()
                        if m.codon_status == ModuleStatus.CONDON_COMPATIBLE
                    ]
                ),
                "codon_optimizable": len(
                    [
                        m
                        for m in self.graph.modules.values()
                        if m.codon_status == ModuleStatus.CONDON_OPTIMIZABLE
                    ]
                ),
                "codon_limited": len(
                    [
                        m
                        for m in self.graph.modules.values()
                        if m.codon_status == ModuleStatus.CONDON_LIMITED
                    ]
                ),
                "codon_incompatible": len(
                    [
                        m
                        for m in self.graph.modules.values()
                        if m.codon_status == ModuleStatus.CONDON_INCOMPATIBLE
                    ]
                ),
            },
            "compilation_order": self.graph.compilation_order,
            "circular_dependencies": self.graph.circular_dependencies,
            "thread_safety_issues": self.graph.thread_safety_issues,
            "modules": {
                name: {
                    "path": info.path,
                    "dependencies": list(info.dependencies),
                    "dependents": list(info.dependents),
                    "import_types": {k: v.value for k, v in info.import_types.items()},
                    "conditional_imports": info.conditional_imports,
                    "dynamic_imports": info.dynamic_imports,
                    "thread_safety_issues": info.thread_safety_issues,
                    "codon_status": info.codon_status.value,
                    "compilation_priority": info.compilation_priority,
                }
                for name, info in self.graph.modules.items()
            },
        }

        return report

    def save_report(self, output_path: str) -> None:
        """Save dependency analysis report to file"""
        report = self.generate_report()

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Dependency analysis report saved to {output_path}")


def main():
    """Main function for dependency analysis"""
    import argparse

    parser = argparse.ArgumentParser(description="Codon Dependency Analyzer")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument(
        "--output", default="dependency_analysis.json", help="Output file path"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    # Run analysis
    analyzer = CodonDependencyAnalyzer(args.project_root)
    graph = analyzer.analyze_codebase()

    # Save report
    analyzer.save_report(args.output)

    # Print summary
    report = analyzer.generate_report()
    summary = report["summary"]

    print(f"\nDependency Analysis Summary:")
    print(f"Total modules: {summary['total_modules']}")
    print(f"Circular dependencies: {summary['circular_dependencies']}")
    print(f"Thread safety issues: {summary['thread_safety_issues']}")
    print(f"Codon compatible: {summary['codon_compatible']}")
    print(f"Codon optimizable: {summary['codon_optimizable']}")
    print(f"Codon limited: {summary['codon_limited']}")
    print(f"Codon incompatible: {summary['codon_incompatible']}")


if __name__ == "__main__":
    main()
