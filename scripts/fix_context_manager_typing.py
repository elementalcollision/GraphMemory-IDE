#!/usr/bin/env python3
"""
Context Manager Type Annotation Fixer

This script automatically fixes common context manager typing issues found by MyPy
to improve code quality across the GraphMemory-IDE codebase.

Based on research from:
- Adam Johnson's Python type hints guide
- MyPy documentation on context managers
- GitHub discussions on async context manager patterns
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
from types import TracebackType

def add_required_imports(content: str) -> Tuple[str, int]:
    """Add required typing imports if missing"""
    fixes_made = 0
    
    # Check what imports we need
    needs_generator = "@contextmanager" in content or "Generator[" in content
    needs_optional = "__aexit__" in content or "__aexit" in content
    needs_type = "__aexit__" in content or "Type[" in content
    needs_traceback = "__aexit__" in content or "TracebackType" in content
    needs_contextmanager = "@contextmanager" in content and "from contextlib import" not in content
    needs_asynccontextmanager = "@asynccontextmanager" in content and "from contextlib import" not in content
    
    # Find existing imports
    import_lines = []
    has_typing_import = False
    has_contextlib_import = False
    has_types_import = False
    
    for line in content.split('\n'):
        if line.strip().startswith('from typing import') or line.strip().startswith('import typing'):
            has_typing_import = True
        if line.strip().startswith('from contextlib import') or line.strip().startswith('import contextlib'):
            has_contextlib_import = True
        if line.strip().startswith('from types import') or line.strip().startswith('import types'):
            has_types_import = True
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            import_lines.append(line)
    
    # Build import additions
    additions = []
    
    if needs_contextmanager or needs_asynccontextmanager:
        if not has_contextlib_import:
            contextlib_imports = []
            if needs_contextmanager:
                contextlib_imports.append("contextmanager")
            if needs_asynccontextmanager:
                contextlib_imports.append("asynccontextmanager")
            additions.append(f"from contextlib import {', '.join(contextlib_imports)}")
            fixes_made += 1
    
    if needs_generator or needs_optional or needs_type:
        if not has_typing_import:
            typing_imports = []
            if needs_generator:
                typing_imports.append("Generator")
            if needs_optional:
                typing_imports.append("Optional")
            if needs_type:
                typing_imports.append("Type")
            if typing_imports:
                additions.append(f"from typing import {', '.join(typing_imports)}")
                fixes_made += 1
    
    if needs_traceback and not has_types_import:
        additions.append("from types import TracebackType")
        fixes_made += 1
    
    # Add the imports after existing imports
    if additions:
        lines = content.split('\n')
        insert_position = 0
        
        # Find last import line
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                insert_position = i + 1
        
        # Insert new imports
        for addition in reversed(additions):
            lines.insert(insert_position, addition)
        
        content = '\n'.join(lines)
    
    return content, fixes_made

def fix_contextmanager_return_types(content: str) -> Tuple[str, int]:
    """Fix @contextmanager return type annotations"""
    fixes_made = 0
    original_content = content
    
    # Pattern for @contextmanager functions with wrong return types
    patterns = [
        # @contextmanager with Any return type
        (r'(@contextmanager\s+def\s+\w+\s*\([^)]*\)\s*->\s*)Any\s*:', r'\1Generator[None, None, None]:'),
        # @contextmanager with missing return type
        (r'(@contextmanager\s+def\s+\w+\s*\([^)]*\)\s*):', r'\1-> Generator[None, None, None]:'),
        # @asynccontextmanager with wrong return types
        (r'(@asynccontextmanager\s+async\s+def\s+\w+\s*\([^)]*\)\s*->\s*)Any\s*:', r'\1AsyncGenerator[None, None]:'),
        (r'(@asynccontextmanager\s+async\s+def\s+\w+\s*\([^)]*\)\s*):', r'\1-> AsyncGenerator[None, None]:'),
    ]
    
    for pattern, replacement in patterns:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            matches = len(re.findall(pattern, content, flags=re.MULTILINE))
            fixes_made += matches
            content = new_content
    
    return content, fixes_made

def fix_aexit_method_signatures(content: str) -> Tuple[str, int]:
    """Fix __aexit__ method signatures to use Optional types"""
    fixes_made = [0]  # Use list to make it mutable in nested function
    
    # Pattern for __aexit__ methods without Optional types
    aexit_pattern = r'(async\s+)?def\s+__aexit__\s*\(\s*self\s*,([^)]*)\)\s*(->\s*[^:]*)?:'
    
    def fix_aexit_params(match):
        async_prefix = match.group(1) if match.group(1) else ""
        params = match.group(2).strip()
        return_type = match.group(3) if match.group(3) else "-> Optional[bool]"
        
        # Check if already properly typed
        if "Optional[" in params and "Type[BaseException]" in params and "TracebackType" in params:
            return match.group(0)  # Already correct
        
        # Standard __aexit__ signature
        fixed_params = """
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]"""
        
        fixes_made[0] += 1
        return f"{async_prefix}def __aexit__(self,{fixed_params}) {return_type}:"
    
    content = re.sub(aexit_pattern, fix_aexit_params, content, flags=re.MULTILINE | re.DOTALL)
    
    return content, fixes_made[0]

def fix_context_manager_classes(content: str) -> Tuple[str, int]:
    """Fix context manager class implementations"""
    fixes_made = 0
    
    # Pattern for __enter__ methods without return types
    enter_pattern = r'(def\s+__enter__\s*\([^)]*\)\s*):'
    replacement = r'\1-> Any:'
    
    new_content = re.sub(enter_pattern, replacement, content)
    if new_content != content:
        fixes_made += len(re.findall(enter_pattern, content))
        content = new_content
    
    # Pattern for __aenter__ methods without return types
    aenter_pattern = r'(async\s+def\s+__aenter__\s*\([^)]*\)\s*):'
    replacement = r'\1-> Any:'
    
    new_content = re.sub(aenter_pattern, replacement, content)
    if new_content != content:
        fixes_made += len(re.findall(aenter_pattern, content))
        content = new_content
    
    return content, fixes_made

def should_process_file(file_path: str) -> bool:
    """Check if file should be processed"""
    # Skip certain directories and file types
    skip_patterns = [
        '.venv/', '__pycache__/', '.git/', '.mypy_cache/',
        '.pytest_cache/', 'node_modules/', '.DS_Store',
        '.pyc', '.pyo', '.pyd', '.so'
    ]
    
    for pattern in skip_patterns:
        if pattern in file_path:
            return False
    
    # Only process Python files with context manager patterns
    if not file_path.endswith('.py'):
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Only process files that contain context manager patterns
            return any(pattern in content for pattern in [
                '@contextmanager', '@asynccontextmanager', '__enter__', '__exit__', 
                '__aenter__', '__aexit__'
            ])
    except Exception:
        return False

def process_file(file_path: str) -> Dict[str, int]:
    """Process a single file and fix context manager typing issues"""
    results = {
        'imports_added': 0,
        'return_types_fixed': 0,
        'aexit_signatures_fixed': 0,
        'class_methods_fixed': 0,
        'total_fixes': 0
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply fixes in order
        content, import_fixes = add_required_imports(content)
        content, return_fixes = fix_contextmanager_return_types(content)
        content, aexit_fixes = fix_aexit_method_signatures(content)
        content, class_fixes = fix_context_manager_classes(content)
        
        results['imports_added'] = import_fixes
        results['return_types_fixed'] = return_fixes
        results['aexit_signatures_fixed'] = aexit_fixes
        results['class_methods_fixed'] = class_fixes
        results['total_fixes'] = import_fixes + return_fixes + aexit_fixes + class_fixes
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {file_path}: {results['total_fixes']} context manager typing issues")
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return results

def process_directory(directory: str) -> Dict[str, int]:
    """Process all Python files in a directory"""
    total_results = {
        'files_processed': 0,
        'imports_added': 0,
        'return_types_fixed': 0,
        'aexit_signatures_fixed': 0,
        'class_methods_fixed': 0,
        'total_fixes': 0
    }
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            if should_process_file(file_path):
                results = process_file(file_path)
                
                total_results['files_processed'] += 1
                for key in ['imports_added', 'return_types_fixed', 'aexit_signatures_fixed', 'class_methods_fixed', 'total_fixes']:
                    total_results[key] += results[key]
    
    return total_results

def main() -> None:
    """Main function"""
    print("🔧 Starting Context Manager Type Annotation Fixer")
    print("=" * 60)
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Directories to process
    target_dirs = [
        'server/',
        'dashboard/',
        'monitoring/',
        'scripts/',
        'tests/'
    ]
    
    total_results = {
        'files_processed': 0,
        'imports_added': 0,
        'return_types_fixed': 0,
        'aexit_signatures_fixed': 0,
        'class_methods_fixed': 0,
        'total_fixes': 0
    }
    
    for target_dir in target_dirs:
        dir_path = project_root / target_dir
        if dir_path.exists():
            print(f"\n📁 Processing {target_dir}...")
            results = process_directory(str(dir_path))
            
            # Accumulate results
            for key in total_results:
                total_results[key] += results[key]
            
            if results['total_fixes'] > 0:
                print(f"   Files processed: {results['files_processed']}")
                print(f"   Imports added: {results['imports_added']}")
                print(f"   Return types fixed: {results['return_types_fixed']}")
                print(f"   __aexit__ signatures fixed: {results['aexit_signatures_fixed']}")
                print(f"   Class methods fixed: {results['class_methods_fixed']}")
                print(f"   Total fixes: {results['total_fixes']}")
    
    print("\n" + "=" * 60)
    print("📊 CONTEXT MANAGER TYPING FIXES SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {total_results['files_processed']}")
    print(f"Imports added: {total_results['imports_added']}")
    print(f"@contextmanager return types fixed: {total_results['return_types_fixed']}")
    print(f"__aexit__ method signatures fixed: {total_results['aexit_signatures_fixed']}")
    print(f"Context manager class methods fixed: {total_results['class_methods_fixed']}")
    print(f"Total fixes applied: {total_results['total_fixes']}")
    
    if total_results['total_fixes'] > 0:
        print("\n✅ Context manager typing fixes completed successfully!")
        print("💡 Run MyPy again to verify context manager improvements")
    else:
        print("\n✅ No context manager typing fixes needed - code is already well-typed!")

if __name__ == "__main__":
    main() 