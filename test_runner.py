#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated test runner for reproducing Conan Windows env vars issue.
Runs conan create multiple times to catch the ~25% intermittent failure rate.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import json


class TestRunner:
    def __init__(self, runs=10):
        self.runs = runs
        self.results = []
        self.project_dir = Path(__file__).parent

    def run_test(self, run_number):
        """Execute single conan create"""
        print(f"\n{'='*70}")
        print(f"RUN {run_number}/{self.runs} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        
        try:
            # Clean cache to increase likelihood of triggering race condition
            subprocess.run(
                ["conan", "remove", "mypkg/1.0", "-c"],
                cwd=str(self.project_dir),
                capture_output=True,
                timeout=30
            )
        except Exception as e:
            self.results.append({
                'run': run_number,
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return False
        
        try:
            result = subprocess.run(
                ["conan", "create", ".", "--build=missing"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=180
            )
            
            # Check for the critical failure pattern
            output = result.stdout + result.stderr
            
            # Look for signs of missing env vars
            failure_patterns = [
                'MISSING VARIABLES',
                'could not find any instance of Visual Studio',
                'COM initialization error',
                '0x80131904',
                'vswhere.exe',
            ]
            
            is_failed = any(pattern in output for pattern in failure_patterns)
            
            self.results.append({
                'run': run_number,
                'status': 'FAIL' if (is_failed or result.returncode != 0) else 'PASS',
                'returncode': result.returncode,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"Status: {'FAIL' if (is_failed or result.returncode != 0) else 'PASS'}")
            
            if is_failed or result.returncode != 0:
                print("\nOutput:")
                print(output[-2000:])  # Last 2000 chars
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            print("Status: TIMEOUT")
            self.results.append({
                'run': run_number,
                'status': 'TIMEOUT',
                'timestamp': datetime.now().isoformat()
            })
            return False
        except Exception as e:
            print(f"Status: ERROR - {e}")
            self.results.append({
                'run': run_number,
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return False

    def run_all_tests(self):
        """Run all test iterations"""
        print(f"\n{'='*70}")
        print(f"CONAN WINDOWS ENV VARS REPRODUCTION TEST")
        print(f"Running {self.runs} iterations...")
        print(f"Target failure rate: ~25% (intermittent)")
        print(f"{'='*70}")
        
        for i in range(1, self.runs + 1):
            self.run_test(i)
        
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')
        timeouts = sum(1 for r in self.results if r['status'] == 'TIMEOUT')
        
        print(f"\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total Runs:    {self.runs}")
        print(f"Passed:        {passed} ({100*passed/self.runs:.1f}%)")
        print(f"Failed:        {failed} ({100*failed/self.runs:.1f}%)")
        print(f"Errors:        {errors}")
        print(f"Timeouts:      {timeouts}")
        print(f"{'='*70}")
        
        if failed > 0:
            print(f"\n[WARNING] ISSUE REPRODUCED! {failed}/{self.runs} runs failed.")
            print(f"Failure rate: {100*failed/self.runs:.1f}%")
            print("\nThis indicates the Windows environment variables issue is present.")
        else:
            print(f"\n[OK] No failures detected in {self.runs} runs.")
            print("Issue may not be reproducible in current environment.")
        
        # Save results
        results_file = self.project_dir / 'test_results.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {results_file}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Reproduce Conan Windows env vars issue (#19433)'
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=10,
        help='Number of test runs (default: 10)'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(runs=args.runs)
    runner.run_all_tests()
    
    # Exit with error code if any failures detected
    if any(r['status'] != 'PASS' for r in runner.results):
        sys.exit(1)
