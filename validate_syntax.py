#!/usr/bin/env python3
"""
Syntax Validation Script

Validates all scripts before committing to catch syntax errors early.
"""

import ast
import sys
import os
from pathlib import Path


def validate_python_file(filepath):
    """Validate Python file syntax"""
    print(f"Validating Python: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f"  ✓ OK")
        return True
    except SyntaxError as e:
        print(f"  ✗ SYNTAX ERROR: Line {e.lineno}: {e.msg}")
        print(f"    {e.text}")
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


def validate_yaml_file(filepath):
    """Validate YAML file syntax"""
    print(f"Validating YAML: {filepath}")
    try:
        import yaml
        with open(filepath, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print(f"  ✓ OK")
        return True
    except ImportError:
        print(f"  ! SKIPPED (PyYAML not installed)")
        return True  # Don't fail if PyYAML not available
    except yaml.YAMLError as e:
        print(f"  ✗ YAML ERROR: {e}")
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


def validate_bash_script(filepath):
    """Basic Bash script validation"""
    print(f"Checking Bash script: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic checks
        issues = []
        
        # Check for common bash errors
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for unmatched quotes
            single_quotes = line.count("'") - line.count("\\'")
            double_quotes = line.count('"') - line.count('\\"')
            
            if single_quotes % 2 != 0:
                issues.append(f"Line {i}: Unmatched single quote")
            if double_quotes % 2 != 0:
                issues.append(f"Line {i}: Unmatched double quote")
        
        if issues:
            for issue in issues:
                print(f"  ⚠️  {issue}")
            return False
        
        print(f"  ✓ Basic checks passed")
        return True
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


def main():
    print("="*70)
    print("SYNTAX VALIDATION")
    print("="*70)
    print()
    
    all_ok = True
    
    # Validate Python files
    python_files = [
        'conanfile_advanced.py',
        'monitor_conan.py',
        'validate_syntax.py'
    ]
    
    for pyfile in python_files:
        if os.path.exists(pyfile):
            if not validate_python_file(pyfile):
                all_ok = False
        print()
    
    # Validate YAML workflows
    workflow_dir = Path('.github/workflows')
    if workflow_dir.exists():
        for yamlfile in workflow_dir.glob('*.yml'):
            if not validate_yaml_file(str(yamlfile)):
                all_ok = False
            print()
    
    # Summary
    print("="*70)
    if all_ok:
        print("✓ ALL VALIDATIONS PASSED")
        print("="*70)
        return 0
    else:
        print("✗ VALIDATION FAILED - Fix errors above")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
