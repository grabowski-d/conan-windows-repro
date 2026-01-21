#!/usr/bin/env python3
"""
Conan Subprocess Monitor

This script monkey-patches subprocess.Popen to intercept and monitor
all subprocess calls made by Conan, with special focus on environment
variable handling.

Usage:
    python monitor_conan.py "conan create . --name=mypkg --version=1.0"
"""

import subprocess
import os
import sys
import json
import time
from datetime import datetime

# Critical Windows environment variables
CRITICAL_VARS = ['ProgramData', 'SystemRoot', 'COMSPEC', 'PATH', 'TEMP', 'TMP']

# Storage for monitoring data
subprocess_calls = []
env_modifications = []

# Store original subprocess.Popen
original_popen = subprocess.Popen

class MonitoredPopen(original_popen):
    """Wrapper around subprocess.Popen that monitors environment passing"""
    
    def __init__(self, *args, **kwargs):
        # Capture call details
        call_info = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'args': str(args[0]) if args else None,
            'cwd': kwargs.get('cwd', os.getcwd()),
            'env_provided': 'env' in kwargs,
            'env_type': type(kwargs.get('env')).__name__ if 'env' in kwargs else 'inherited',
        }
        
        # Check environment passing
        if 'env' in kwargs:
            env = kwargs['env']
            call_info['env_is_none'] = env is None
            call_info['env_is_empty'] = len(env) == 0 if env is not None else None
            
            if env:
                # Check for critical variables
                missing_vars = [var for var in CRITICAL_VARS if var not in env]
                call_info['missing_critical_vars'] = missing_vars
                call_info['critical_vars_count'] = len(CRITICAL_VARS) - len(missing_vars)
                
                if missing_vars:
                    print(f"\n⚠️  WARNING: subprocess call missing {len(missing_vars)} critical vars: {missing_vars}", 
                          file=sys.stderr)
                    print(f"   Command: {call_info['args']}", file=sys.stderr)
        else:
            # No env specified - will inherit
            call_info['inherits_environment'] = True
            current_env_missing = [var for var in CRITICAL_VARS if var not in os.environ]
            call_info['parent_env_missing'] = current_env_missing
            
            if current_env_missing:
                print(f"\n⚠️  WARNING: Parent environment missing vars: {current_env_missing}", 
                      file=sys.stderr)
        
        subprocess_calls.append(call_info)
        
        # Call original
        try:
            super().__init__(*args, **kwargs)
        except Exception as e:
            call_info['exception'] = str(e)
            raise

# Monkey-patch subprocess.Popen
subprocess.Popen = MonitoredPopen

def monitor_os_environ():
    """Take snapshot of os.environ critical variables"""
    return {
        'timestamp': time.time(),
        'datetime': datetime.now().isoformat(),
        'vars': {var: os.environ.get(var) for var in CRITICAL_VARS}
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python monitor_conan.py <conan command>")
        print("Example: python monitor_conan.py 'conan create . --name=mypkg --version=1.0'")
        sys.exit(1)
    
    command = sys.argv[1]
    
    print("="*80)
    print("Conan Subprocess Monitor")
    print("="*80)
    print(f"Command: {command}")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*80)
    
    # Initial environment snapshot
    initial_env = monitor_os_environ()
    print("\nInitial environment:")
    for var, val in initial_env['vars'].items():
        status = "✓" if val else "✗"
        display = (val[:50] + '...') if val and len(val) > 50 else (val or 'MISSING')
        print(f"  {status} {var}: {display}")
    
    # Execute command
    print(f"\nExecuting: {command}")
    print("-"*80)
    
    start_time = time.time()
    exit_code = os.system(command)
    elapsed = time.time() - start_time
    
    print("-"*80)
    print(f"\nCompleted in {elapsed:.2f}s with exit code {exit_code}")
    
    # Final environment snapshot
    final_env = monitor_os_environ()
    
    # Analyze results
    print("\n" + "="*80)
    print("MONITORING REPORT")
    print("="*80)
    
    print(f"\nTotal subprocess calls intercepted: {len(subprocess_calls)}")
    
    if subprocess_calls:
        print("\nSubprocess calls with missing environment variables:")
        problematic_calls = [c for c in subprocess_calls 
                           if c.get('missing_critical_vars')]
        
        if problematic_calls:
            print(f"  Found {len(problematic_calls)} problematic calls:")
            for i, call in enumerate(problematic_calls[:5], 1):
                print(f"\n  Call {i}:")
                print(f"    Command: {call['args'][:80]}..." if len(str(call['args'])) > 80 else f"    Command: {call['args']}")
                print(f"    Missing vars: {call['missing_critical_vars']}")
                print(f"    Time: {call['datetime']}")
        else:
            print("  ✓ All subprocess calls had complete environment")
        
        print("\nSubprocess calls by environment type:")
        env_types = {}
        for call in subprocess_calls:
            env_type = call.get('env_type', 'inherited')
            env_types[env_type] = env_types.get(env_type, 0) + 1
        for env_type, count in env_types.items():
            print(f"  {env_type}: {count} calls")
    
    # Check for environment changes
    print("\nEnvironment stability check:")
    changes = []
    for var in CRITICAL_VARS:
        initial = initial_env['vars'][var]
        final = final_env['vars'][var]
        if initial != final:
            changes.append((var, initial, final))
    
    if changes:
        print("  ⚠️  Environment changed during execution:")
        for var, old, new in changes:
            print(f"    {var}: '{old}' -> '{new}'")
    else:
        print("  ✓ Environment remained stable")
    
    # Save detailed report
    report = {
        'command': command,
        'exit_code': exit_code,
        'elapsed_time': elapsed,
        'initial_env': initial_env,
        'final_env': final_env,
        'subprocess_calls': subprocess_calls,
        'env_changes': changes,
        'summary': {
            'total_subprocess_calls': len(subprocess_calls),
            'problematic_calls': len(problematic_calls) if subprocess_calls else 0,
            'env_stable': len(changes) == 0
        }
    }
    
    report_file = f"conan_monitor_{int(time.time())}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Exit with same code as conan
    sys.exit(exit_code >> 8 if exit_code > 255 else exit_code)

if __name__ == '__main__':
    main()
