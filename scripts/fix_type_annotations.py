#!/usr/bin/env python3
"""
Automated Type Annotation Fixer

This script automatically fixes common type annotation issues found by MyPy
to improve code quality across the GraphMemory-IDE codebase.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

def fix_missing_return_annotations(file_path: str) -> int:
    """Fix missing return type annotations in a file"""
    fixes_made = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern for functions missing return type annotations
    patterns = [
        # def function_name() -> None:
        (r'(\s+def\s+\w+\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # async def function_name() -> None:
        (r'(\s+async\s+def\s+\w+\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # def __init__(self) -> None:
        (r'(\s+def\s+__init__\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # def test_function() -> None:
        (r'(\s+def\s+test_\w+\s*\([^)]*\)\s*):', r'\1 -> None:'),
    ]
    
    for pattern, replacement in patterns:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            fixes_made += len(re.findall(pattern, content))
            content = new_content
    
    # Only write if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return fixes_made

def fix_unused_type_ignores(file_path: str) -> int:
    """Remove unused type: ignore comments"""
    fixes_made = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    original_lines = lines.copy()
    
    # Remove lines with unused type: ignore
    new_lines = []
    for line in lines:
        if '# type: ignore' in line and 'Unused "type: ignore"' not in line:
            # Keep the line but remove the type: ignore comment
            cleaned_line = re.sub(r'\s*#\s*type:\s*ignore.*$', '', line)
            new_lines.append(cleaned_line)
            if cleaned_line != line:
                fixes_made += 1
        else:
            new_lines.append(line)
    
    # Only write if changes were made
    if new_lines != original_lines:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    
    return fixes_made

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
    
    # Only process Python files
    return file_path.endswith('.py')

def process_directory(directory: str) -> Dict[str, int]:
    """Process all Python files in a directory"""
    results = {
        'files_processed': 0,
        'return_annotations_fixed': 0,
        'unused_ignores_removed': 0,
        'total_fixes': 0
    }
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            if should_process_file(file_path):
                try:
                    return_fixes = fix_missing_return_annotations(file_path)
                    ignore_fixes = fix_unused_type_ignores(file_path)
                    
                    if return_fixes > 0 or ignore_fixes > 0:
                        print(f"Fixed {file_path}: {return_fixes} return annotations, {ignore_fixes} unused ignores")
                    
                    results['files_processed'] += 1
                    results['return_annotations_fixed'] += return_fixes
                    results['unused_ignores_removed'] += ignore_fixes
                    results['total_fixes'] += return_fixes + ignore_fixes
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    return results

def main() -> None:
    """Main function"""
    print("🔧 Starting Automated Type Annotation Fixer")
    print("=" * 50)
    
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
        'return_annotations_fixed': 0,
        'unused_ignores_removed': 0,
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
            
            print(f"   Files processed: {results['files_processed']}")
            print(f"   Return annotations fixed: {results['return_annotations_fixed']}")
            print(f"   Unused ignores removed: {results['unused_ignores_removed']}")
            print(f"   Total fixes: {results['total_fixes']}")
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Total files processed: {total_results['files_processed']}")
    print(f"Return annotations fixed: {total_results['return_annotations_fixed']}")
    print(f"Unused type ignores removed: {total_results['unused_ignores_removed']}")
    print(f"Total fixes applied: {total_results['total_fixes']}")
    
    if total_results['total_fixes'] > 0:
        print("\n✅ Type annotation fixes completed successfully!")
        print("💡 Run MyPy again to verify improvements")
    else:
        print("\n✅ No fixes needed - code is already well-typed!")

if __name__ == "__main__":
    main() 