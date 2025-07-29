#!/usr/bin/env python3
import re
import os

def fix_missing_return_annotations(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix specific patterns where functions clearly don't return anything
    patterns = [
        # def test_function(...): -> def test_function(...) -> None:
        (r'(\s+def\s+test_\w+\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # async def test_function(...): -> async def test_function(...) -> None:
        (r'(\s+async\s+def\s+test_\w+\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # def __init__(self): -> def __init__(self) -> None:
        (r'(\s+def\s+__init__\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # def setup_method(self): -> def setup_method(self) -> None:
        (r'(\s+def\s+setup_method\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # def teardown_method(self): -> def teardown_method(self) -> None:
        (r'(\s+def\s+teardown_method\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # async def main(): -> async def main() -> None:
        (r'(\s+async\s+def\s+main\s*\([^)]*\)\s*):', r'\1 -> None:'),
        # def main(): -> def main() -> None:  
        (r'(\s+def\s+main\s*\([^)]*\)\s*):', r'\1 -> None:'),
    ]
    
    for pattern, replacement in patterns:
        # Only apply if the function doesn't already have a return type
        pattern_with_return = pattern.replace(':', r'\s*->\s*\w+\s*:')
        if not re.search(pattern_with_return, content):
            content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f'Fixed {file_path}')
        return True
    return False

# Fix test files that have many missing annotations
test_files_to_fix = [
    'server/dashboard/test_step2_validation_layer.py',
    'server/dashboard/test_analytics_client_basic.py',
    'server/dashboard/test_enhanced_circuit_breaker.py',
    'server/dashboard/test_cache_manager.py',
    'server/test_main.py'
]

fixed_count = 0
for file_path in test_files_to_fix:
    if os.path.exists(file_path):
        if fix_missing_return_annotations(file_path):
            fixed_count += 1

print(f'Fixed {fixed_count} files') 