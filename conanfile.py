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
        
        missing_vars = []
        present_vars = []
        
        for var in critical_vars:
            value = os.environ.get(var)
            if value:
                present_vars.append((var, value[:50] + '...' if len(value) > 50 else value))
            else:
                missing_vars.append(var)
        
        # Log present variables
        for var, val in present_vars:
            self.output.info(f"✓ {var}: {val}")
        
        # Log missing variables - THIS IS THE ISSUE
        if missing_vars:
            self.output.warning(f"✗ MISSING VARIABLES ({len(missing_vars)}): {', '.join(missing_vars)}")
        else:
            self.output.success("✓ All critical environment variables present")
        
        # Full env dump for debugging
        self.output.verbose(f"\nFull environment dump:\n{os.environ}")
