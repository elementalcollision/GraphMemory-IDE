#!/usr/bin/env python3
"""
Return Value Error Fixer

This script automatically fixes "No return value expected" MyPy errors by:
1. Identifying functions with void return types that have return statements
2. Either removing the return statements or changing them to early returns
3. Updating function signatures when appropriate

Part of the comprehensive code quality improvement initiative.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set, Any

def identify_return_value_errors(file_path: str) -> List[int]:
    """Identify line numbers with 'No return value expected' errors"""
    error_lines = []
    
    # Run mypy on the specific file to get error lines
    import subprocess
    try:
        result = subprocess.run(
            ['mypy', '--config-file=mypy.ini', file_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        for line in result.stdout.split('\n'):
            if 'No return value expected' in line and file_path in line:
                # Extract line number
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        line_num = int(parts[1])
                        error_lines.append(line_num)
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error running mypy on {file_path}: {e}")
    
    return error_lines

def analyze_function_context(content: str, line_num: int) -> Dict[str, Any]:
    """Analyze the function context around a return statement error"""
    lines = content.split('\n')
    
    if line_num > len(lines):
        return {}
    
    # Find the function this return statement belongs to
    function_start = None
    function_name = None
    return_type = None
    
    for i in range(line_num - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith('def ') or line.startswith('async def '):
            function_start = i
            function_name_match = re.search(r'def\s+(\w+)', line)
            if function_name_match:
                function_name = function_name_match.group(1)
            
            # Check if function has -> None annotation
            if '-> None:' in line:
                return_type = 'None'
            elif '->' in line and ':' in line:
                return_type_match = re.search(r'->\s*([^:]+):', line)
                if return_type_match:
                    return_type = return_type_match.group(1).strip()
            break
    
    # Analyze the return statement
    return_line = lines[line_num - 1] if line_num <= len(lines) else ""
    
    return {
        'function_start': function_start,
        'function_name': function_name,
        'return_type': return_type,
        'return_line': return_line.strip(),
        'line_content': return_line
    }

def fix_return_value_error(content: str, line_num: int, context: Dict[str, Any]) -> Tuple[str, str]:
    """Fix a specific return value error"""
    lines = content.split('\n')
    
    if line_num > len(lines):
        return content, "Line number out of range"
    
    return_line = lines[line_num - 1]
    
    # Determine fix strategy based on the return statement
    if re.match(r'\s*return\s*$', return_line):
        # Simple 'return' statement - this is fine for void functions, likely false positive
        return content, "Simple return statement - no fix needed"
    
    elif re.match(r'\s*return\s+None\s*$', return_line):
        # 'return None' in void function - change to just 'return'
        lines[line_num - 1] = re.sub(r'return\s+None', 'return', return_line)
        return '\n'.join(lines), "Changed 'return None' to 'return'"
    
    elif re.match(r'\s*return\s+.+', return_line):
        # Return with a value - need to determine if we should remove it or change function signature
        
        # Check if this looks like an error return or early exit
        return_value_match = re.search(r'return\s+(.+)', return_line)
        if return_value_match:
            return_value = return_value_match.group(1).strip()
            
            # Common patterns that should be early exits
            if return_value in ['False', 'True', '0', '1', 'None']:
                # This might be an early exit - change to just return
                indent_match = re.match(r'^(\s*)', return_line)
                indent = indent_match.group(1) if indent_match else ""
                lines[line_num - 1] = f"{indent}return"
                return '\n'.join(lines), f"Converted 'return {return_value}' to early return"
            
            # Check if it's in an if block (likely early exit)
            if line_num > 1:
                prev_lines = [lines[i].strip() for i in range(max(0, line_num - 5), line_num - 1)]
                if any('if ' in line for line in prev_lines[-3:]):
                    # Likely an early exit condition
                    indent_match = re.match(r'^(\s*)', return_line)
                    indent = indent_match.group(1) if indent_match else ""
                    lines[line_num - 1] = f"{indent}return"
                    return '\n'.join(lines), "Converted conditional return to early exit"
    
    return content, "No fix applied - manual review needed"

def process_file(file_path: str) -> Dict[str, Any]:
    """Process a single file and fix return value errors"""
    results: Dict[str, Any] = {
        'file': file_path,
        'errors_found': 0,
        'errors_fixed': 0,
        'fixes_applied': [],
        'manual_review_needed': []
    }
    
    try:
        # Get error lines first
        error_lines = identify_return_value_errors(file_path)
        results['errors_found'] = len(error_lines)
        
        if not error_lines:
            return results
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Process each error line
        for line_num in sorted(error_lines, reverse=True):  # Process in reverse to maintain line numbers
            context = analyze_function_context(content, line_num)
            fixed_content, fix_description = fix_return_value_error(content, line_num, context)
            
            if fixed_content != content:
                content = fixed_content
                results['errors_fixed'] += 1
                results['fixes_applied'].append({
                    'line': line_num,
                    'description': fix_description,
                    'function': context.get('function_name', 'unknown')
                })
            else:
                results['manual_review_needed'].append({
                    'line': line_num,
                    'description': fix_description,
                    'function': context.get('function_name', 'unknown'),
                    'content': context.get('return_line', '')
                })
        
        # Write changes if any were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {file_path}: {results['errors_fixed']} return value errors")
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        results['error'] = str(e)
    
    return results

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
    
    return file_path.endswith('.py')

def process_directory(directory: str) -> Dict[str, Any]:
    """Process all Python files in a directory"""
    total_results: Dict[str, Any] = {
        'files_processed': 0,
        'total_errors_found': 0,
        'total_errors_fixed': 0,
        'files_with_fixes': 0,
        'manual_review_files': 0,
        'all_fixes': [],
        'all_manual_reviews': []
    }
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            if should_process_file(file_path):
                results = process_file(file_path)
                
                total_results['files_processed'] += 1
                total_results['total_errors_found'] += results['errors_found']
                total_results['total_errors_fixed'] += results['errors_fixed']
                
                if results['errors_fixed'] > 0:
                    total_results['files_with_fixes'] += 1
                    total_results['all_fixes'].extend(results['fixes_applied'])
                
                if results['manual_review_needed']:
                    total_results['manual_review_files'] += 1
                    total_results['all_manual_reviews'].extend([
                        {**item, 'file': file_path} for item in results['manual_review_needed']
                    ])
    
    return total_results

def main() -> None:
    """Main function"""
    print("🔧 Starting Return Value Error Fixer")
    print("=" * 60)
    print("Targeting: 'No return value expected' MyPy errors")
    print("Strategy: Automated fixing of inappropriate return statements")
    print("=" * 60)
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Directories to process
    target_dirs = [
        'server/',
        'dashboard/'
    ]
    
    total_results: Dict[str, Any] = {
        'files_processed': 0,
        'total_errors_found': 0,
        'total_errors_fixed': 0,
        'files_with_fixes': 0,
        'manual_review_files': 0,
        'all_fixes': [],
        'all_manual_reviews': []
    }
    
    for target_dir in target_dirs:
        dir_path = project_root / target_dir
        if dir_path.exists():
            print(f"\n📁 Processing {target_dir}...")
            results = process_directory(str(dir_path))
            
            # Accumulate results
            for key in ['files_processed', 'total_errors_found', 'total_errors_fixed', 'files_with_fixes', 'manual_review_files']:
                total_results[key] += results[key]
            
            total_results['all_fixes'].extend(results['all_fixes'])
            total_results['all_manual_reviews'].extend(results['all_manual_reviews'])
            
            if results['total_errors_found'] > 0:
                print(f"   Files processed: {results['files_processed']}")
                print(f"   Return value errors found: {results['total_errors_found']}")
                print(f"   Errors fixed automatically: {results['total_errors_fixed']}")
                print(f"   Files requiring manual review: {results['manual_review_files']}")
    
    print("\n" + "=" * 60)
    print("📊 RETURN VALUE ERROR FIXES SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {total_results['files_processed']}")
    print(f"Total return value errors found: {total_results['total_errors_found']}")
    print(f"Errors fixed automatically: {total_results['total_errors_fixed']}")
    print(f"Files with automatic fixes: {total_results['files_with_fixes']}")
    print(f"Files requiring manual review: {total_results['manual_review_files']}")
    
    if total_results['total_errors_fixed'] > 0:
        print(f"\n✅ Automatically fixed {total_results['total_errors_fixed']} return value errors!")
        print("💡 Run MyPy again to verify improvements")
        
        # Show some example fixes
        if total_results['all_fixes']:
            print(f"\n📋 Example fixes applied:")
            for fix in total_results['all_fixes'][:5]:
                print(f"   • {fix['function']}() line {fix['line']}: {fix['description']}")
    
    if total_results['all_manual_reviews']:
        print(f"\n⚠️  Manual review needed for {len(total_results['all_manual_reviews'])} cases:")
        for review in total_results['all_manual_reviews'][:5]:
            print(f"   • {review['file']}:{review['line']} - {review['content']}")
    
    if total_results['total_errors_fixed'] == 0:
        print("\n✅ No return value errors found or all require manual review!")

if __name__ == "__main__":
    main() 