from conan import ConanFile
from conan.tools.cmake import cmake_layout, CMakeToolchain
import os
import sys
import subprocess
import threading
import time

# Critical environment variables to monitor
CRITICAL_VARS = ['ProgramData', 'SystemRoot', 'COMSPEC', 'PATH', 'TEMP', 'TMP']


class MyPackageConanAdvanced(ConanFile):
    name = "mypkg"
    version = "1.0"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._env_snapshots = []
        self._subprocess_calls = []
        self._critical_failure = False
    
    def layout(self):
        self._snapshot_env("layout")
        cmake_layout(self)

    def generate(self):
        self._snapshot_env("generate_start")
        
        # Test 1: Check if subprocess inherits environment correctly
        self._test_subprocess_inheritance()
        
        # Test 2: Check for race conditions with threading
        self._test_race_conditions()
        
        # Generate toolchain
        tc = CMakeToolchain(self)
        tc.generate()
        
        self._snapshot_env("generate_end")

    def build(self):
        self._snapshot_env("build_start")
        
        # Test 3: Verify environment before any build operations
        self._verify_critical_vars("build_start")
        
        # Test 4: Monitor os.environ modifications
        self._monitor_environ_modifications()
        
        # Test 5: Check subprocess behavior
        self._test_subprocess_env_passing()
        
        self.output.info("[BUILD] Skipping actual build - environment testing only")
        
        self._snapshot_env("build_end")

    def package(self):
        self._snapshot_env("package")
        self._report_findings()
        
        # Only raise if critical failure detected
        if self._critical_failure:
            raise RuntimeError(
                "Critical environment variable issues detected. See logs above for details."
            )

    def _snapshot_env(self, location):
        """Take snapshot of environment variables"""
        snapshot = {
            'location': location,
            'timestamp': time.time(),
            'thread_id': threading.get_ident(),
            'vars': {var: os.environ.get(var) for var in CRITICAL_VARS}
        }
        self._env_snapshots.append(snapshot)
        
        if hasattr(self, 'output'):
            missing = [var for var in CRITICAL_VARS if not snapshot['vars'][var]]
            if missing:
                self.output.error(f"[{location}] CRITICAL MISSING: {', '.join(missing)}")
                self._critical_failure = True

    def _test_subprocess_inheritance(self):
        """Test if subprocess properly inherits environment"""
        if not hasattr(self, 'output'):
            return
            
        self.output.info("=" * 70)
        self.output.info("[TEST 1] Subprocess Environment Inheritance")
        self.output.info("=" * 70)
        
        # Test A: Default subprocess (should inherit)
        try:
            result = subprocess.run(
                ['cmd', '/c', 'echo', '%ProgramData%'],
                capture_output=True,
                text=True,
                timeout=5
            )
            program_data = result.stdout.strip()
            if program_data and program_data != '%ProgramData%':
                self.output.success(f"[TEST 1A] subprocess inherits: ProgramData={program_data}")
            else:
                self.output.error(f"[TEST 1A] FAILED: ProgramData not inherited: {program_data}")
                self._critical_failure = True
        except Exception as e:
            self.output.error(f"[TEST 1A] Exception: {e}")
        
        # Test B: Explicit env passing
        try:
            result = subprocess.run(
                ['cmd', '/c', 'echo', '%SystemRoot%'],
                capture_output=True,
                text=True,
                env=os.environ.copy(),  # Explicit copy
                timeout=5
            )
            system_root = result.stdout.strip()
            if system_root and system_root != '%SystemRoot%':
                self.output.success(f"[TEST 1B] explicit env copy works: SystemRoot={system_root}")
            else:
                self.output.error(f"[TEST 1B] FAILED: SystemRoot not in env copy: {system_root}")
                self._critical_failure = True
        except Exception as e:
            self.output.error(f"[TEST 1B] Exception: {e}")
        
        # Test C: Empty env (should fail)
        try:
            result = subprocess.run(
                ['cmd', '/c', 'echo', '%COMSPEC%'],
                capture_output=True,
                text=True,
                env={},  # Empty environment
                timeout=5
            )
            comspec = result.stdout.strip()
            if comspec == '%COMSPEC%' or not comspec:
                self.output.info(f"[TEST 1C] empty env fails as expected: {comspec}")
            else:
                self.output.warning(f"[TEST 1C] unexpected: COMSPEC still available: {comspec}")
        except Exception as e:
            self.output.info(f"[TEST 1C] Exception (expected with empty env): {e}")

    def _test_race_conditions(self):
        """Test for race conditions in environment access"""
        if not hasattr(self, 'output'):
            return
            
        self.output.info("=" * 70)
        self.output.info("[TEST 2] Race Condition Detection")
        self.output.info("=" * 70)
        
        results = {'missing': 0, 'present': 0, 'inconsistent': []}
        
        def check_env():
            for _ in range(10):
                snapshot = {var: os.environ.get(var) for var in CRITICAL_VARS}
                missing = [var for var, val in snapshot.items() if not val]
                if missing:
                    results['missing'] += 1
                    results['inconsistent'].append(('missing', missing, time.time()))
                else:
                    results['present'] += 1
                time.sleep(0.001)  # Small delay
        
        # Run multiple threads simultaneously
        threads = [threading.Thread(target=check_env) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        total_checks = results['missing'] + results['present']
        if results['missing'] > 0:
            self.output.error(
                f"[TEST 2] RACE CONDITION DETECTED: {results['missing']}/{total_checks} checks failed"
            )
            for issue_type, vars_list, timestamp in results['inconsistent'][:3]:
                self.output.error(f"  - {issue_type}: {vars_list}")
            self._critical_failure = True
        else:
            self.output.success(f"[TEST 2] No race conditions in {total_checks} concurrent checks")

    def _verify_critical_vars(self, location):
        """Verify and log critical variables"""
        if not hasattr(self, 'output'):
            return
            
        self.output.info("=" * 70)
        self.output.info(f"[{location}] Critical Variables Check")
        self.output.info("=" * 70)
        
        missing = []
        for var in CRITICAL_VARS:
            value = os.environ.get(var)
            if value:
                display = value[:40] + '...' if len(value) > 40 else value
                self.output.info(f"[{location}] ✓ {var}: {display}")
            else:
                self.output.error(f"[{location}] ✗ {var}: MISSING")
                missing.append(var)
        
        if missing:
            self.output.error(
                f"[{location}] Critical environment variables missing: {', '.join(missing)}"
            )
            self._critical_failure = True

    def _monitor_environ_modifications(self):
        """Monitor if os.environ is being modified"""
        if not hasattr(self, 'output'):
            return
            
        self.output.info("=" * 70)
        self.output.info("[TEST 3] Environment Modification Monitor")
        self.output.info("=" * 70)
        
        # Take snapshot before
        before = {var: os.environ.get(var) for var in CRITICAL_VARS}
        
        # Simulate some operations that Conan might do
        time.sleep(0.1)
        
        # Take snapshot after
        after = {var: os.environ.get(var) for var in CRITICAL_VARS}
        
        # Compare
        changes = []
        for var in CRITICAL_VARS:
            if before[var] != after[var]:
                changes.append((var, before[var], after[var]))
        
        if changes:
            self.output.warning(f"[TEST 3] Environment changed during execution:")
            for var, old, new in changes:
                self.output.warning(f"  {var}: '{old}' -> '{new}'")
                if old and not new:  # Variable disappeared
                    self._critical_failure = True
        else:
            self.output.success("[TEST 3] Environment stable - no modifications detected")

    def _test_subprocess_env_passing(self):
        """Test different ways of passing environment to subprocess"""
        if not hasattr(self, 'output'):
            return
            
        self.output.info("=" * 70)
        self.output.info("[TEST 4] Subprocess Environment Passing Methods")
        self.output.info("=" * 70)
        
        tests = [
            ('default', None, "Default (inherit)"),
            ('copy', os.environ.copy(), "os.environ.copy()"),
            ('dict', dict(os.environ), "dict(os.environ)"),
        ]
        
        for test_name, env_arg, description in tests:
            try:
                kwargs = {'capture_output': True, 'text': True, 'timeout': 5}
                if env_arg is not None:
                    kwargs['env'] = env_arg
                
                result = subprocess.run(
                    ['cmd', '/c', 'set', 'ProgramData'],
                    **kwargs
                )
                
                if 'ProgramData=' in result.stdout:
                    self.output.success(f"[TEST 4-{test_name}] {description}: OK")
                else:
                    self.output.error(f"[TEST 4-{test_name}] {description}: FAILED")
                    self.output.error(f"  Output: {result.stdout[:100]}")
                    self._critical_failure = True
            except Exception as e:
                self.output.error(f"[TEST 4-{test_name}] {description}: Exception - {e}")

    def _report_findings(self):
        """Generate comprehensive report of all findings"""
        if not hasattr(self, 'output'):
            return
            
        self.output.info("=" * 70)
        self.output.info("FINAL REPORT")
        self.output.info("=" * 70)
        
        # Analyze snapshots
        self.output.info(f"Total snapshots taken: {len(self._env_snapshots)}")
        
        for i, snapshot in enumerate(self._env_snapshots):
            missing = [var for var, val in snapshot['vars'].items() if not val]
            status = "FAILED" if missing else "OK"
            self.output.info(
                f"Snapshot {i+1}: {snapshot['location']:<15} [{status}] "
                f"Thread: {snapshot['thread_id']}"
            )
            if missing:
                self.output.error(f"  Missing: {', '.join(missing)}")
        
        # Check for inconsistencies
        locations_with_issues = [s['location'] for s in self._env_snapshots 
                                 if any(not val for val in s['vars'].values())]
        
        if locations_with_issues:
            self.output.error(
                f"\n⚠️  ISSUE DETECTED at: {', '.join(set(locations_with_issues))}"
            )
        else:
            self.output.success("\n✓ All environment checks passed")
        
        # Final verdict
        if self._critical_failure:
            self.output.error("\n" + "="*70)
            self.output.error("TEST RESULT: FAILURE - Critical issues detected")
            self.output.error("="*70)
        else:
            self.output.success("\n" + "="*70)
            self.output.success("TEST RESULT: SUCCESS - All tests passed")
            self.output.success("="*70)
