from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain
import os
import sys


class MyPackageConan(ConanFile):
    name = "mypkg"
    version = "1.0"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "src/*", "include/*"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def generate(self):
        """Generate CMake toolchain - check env vars here too"""
        self.output.info("="*60)
        self.output.info("GENERATE() method - Environment Variables Check")
        self.output.info("="*60)
        self._check_env_vars()
        
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        """Build phase - main problem area"""
        self.output.info("="*60)
        self.output.info("BUILD() method - Environment Variables Check")
        self.output.info("="*60)
        self._check_env_vars()
        
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        """Package phase"""
        cmake = CMake(self)
        cmake.install()

    def _check_env_vars(self):
        """Check critical Windows environment variables"""
        # Critical variables for Windows builds
        critical_vars = [
            'ProgramData',
            'SystemRoot',
            'COMSPEC',
            'PATH',
            'PATHEXT',
            'TEMP',
            'TMP',
            'USERPROFILE',
            'HOMEDRIVE',
            'HOMEPATH',
            'WINDIR',
            'PROCESSOR_ARCHITECTURE',
            'NUMBER_OF_PROCESSORS',
        ]
        
        # Visual Studio related variables
        vs_vars = [
            'VSINSTALLDIR',
            'VisualStudioVersion',
            'VCINSTALLDIR',
            'VCToolsInstallDir',
            'INCLUDE',
            'LIB',
        ]
        
        all_critical = critical_vars + vs_vars
        missing_vars = []
        present_vars = []
        
        for var in all_critical:
            value = os.environ.get(var)
            if value:
                # Truncate long values
                display_val = value[:40] + '...' if len(value) > 40 else value
                present_vars.append((var, display_val))
            else:
                missing_vars.append(var)
        
        # Log present variables
        if present_vars:
            for var, val in present_vars:
                self.output.info(f"[PRESENT] {var}: {val}")
        
        # Log missing variables
        if missing_vars:
            critical_missing = [v for v in missing_vars if v in critical_vars]
            vs_missing = [v for v in missing_vars if v in vs_vars]
            
            if critical_missing:
                self.output.warning(
                    f"[CRITICAL] MISSING {len(critical_missing)} critical vars: {', '.join(critical_missing[:3])}{'...' if len(critical_missing) > 3 else ''}"
                )
            
            if vs_missing:
                self.output.info(
                    f"[INFO] {len(vs_missing)} Visual Studio vars not set (may be OK): {', '.join(vs_missing[:2])}{'...' if len(vs_missing) > 2 else ''}"
                )
        else:
            self.output.success(f"[OK] All {len(all_critical)} environment variables present")
        
        # Detailed diagnostics
        self.output.verbose(f"\nPython: {sys.version}")
        self.output.verbose(f"Python executable: {sys.executable}")
        self.output.verbose(f"System platform: {sys.platform}")
        self.output.verbose(f"Current directory: {os.getcwd()}")
