from conan import ConanFile
from conan.tools.cmake import cmake_layout, CMakeToolchain
import os
import sys

# Global scope - check environment variables immediately
print("=" * 80)
print("[GLOBAL SCOPE] Environment Variables Check - BEFORE ConanFile class")
print("=" * 80)

CRITICAL_VARS = ['ProgramData', 'SystemRoot', 'COMSPEC', 'PATH', 'TEMP', 'TMP']

for var in CRITICAL_VARS:
    value = os.environ.get(var)
    if value:
        display = value[:50] + '...' if len(value) > 50 else value
        print(f"[GLOBAL][OK] {var}: {display}")
    else:
        print(f"[GLOBAL][MISSING] {var}: NOT FOUND")

print(f"[GLOBAL] Python: {sys.version}")
print(f"[GLOBAL] CWD: {os.getcwd()}")
print("=" * 80)


class MyPackageConan(ConanFile):
    name = "mypkg"
    version = "1.0"
    settings = "os", "compiler", "build_type", "arch"
    # Minimal exports - no actual source files needed
    exports_sources = "CMakeLists.txt"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_env("[__INIT__]")

    def layout(self):
        self._log_env("[LAYOUT]")
        cmake_layout(self)

    def generate(self):
        """Generate phase - critical for env var checking"""
        self._log_env("[GENERATE]", detailed=True)
        
        # Still generate toolchain for completeness
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        """Build phase - STRIPPED TO MINIMUM"""
        self._log_env("[BUILD]", detailed=True)
        
        # NO ACTUAL BUILD - just verify environment is correct
        # This makes conan create almost instantaneous
        self.output.info("[BUILD] Skipping actual build - just checking environment")
        
        # Optional: uncomment to enable real build for verification
        # cmake = CMake(self)
        # cmake.configure()
        # cmake.build()

    def package(self):
        """Package phase - minimal"""
        self._log_env("[PACKAGE]")
        # No actual packaging needed for env var testing

    def _log_env(self, location, detailed=False):
        """Check and log critical Windows environment variables
        
        Args:
            location: String identifier for the calling method
            detailed: If True, log all variables. If False, only log missing ones.
        """
        self.output.info("=" * 70)
        self.output.info(f"{location} Environment Variables Check")
        self.output.info("=" * 70)
        
        missing = []
        present = []
        
        for var in CRITICAL_VARS:
            value = os.environ.get(var)
            if value:
                display = value[:50] + '...' if len(value) > 50 else value
                present.append((var, display))
            else:
                missing.append(var)
        
        # Always log missing variables
        if missing:
            for var in missing:
                self.output.error(f"{location} [CRITICAL MISSING] {var}")
        
        # Log present variables if detailed or if there are missing ones
        if detailed or missing:
            for var, val in present:
                self.output.info(f"{location} [OK] {var}: {val}")
        
        # Summary
        if missing:
            self.output.warning(
                f"{location} FAILURE: {len(missing)}/{len(CRITICAL_VARS)} "
                f"variables missing: {', '.join(missing)}"
            )
            # Raise exception to fail the build clearly
            raise RuntimeError(
                f"Critical environment variables missing at {location}: {', '.join(missing)}"
            )
        else:
            self.output.success(
                f"{location} SUCCESS: All {len(CRITICAL_VARS)} critical variables present"
            )
        
        # Additional diagnostics
        self.output.info(f"{location} Python: {sys.executable}")
        self.output.info(f"{location} CWD: {os.getcwd()}")
        self.output.info("=" * 70)
