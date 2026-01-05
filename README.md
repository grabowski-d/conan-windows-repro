# Conan Windows Environment Variables Issue - Reproduction Project

**Conan Issue:** [#19433 - Windows environment variables intermittently stripped during recipe execution](https://github.com/conan-io/conan/issues/19433)

## Problem Summary

When running Conan 2.24.0 recipes on Windows, critical system environment variables (`ProgramData`, `SystemRoot`, `COMSPEC`, etc.) are **intermittently missing** during recipe execution (`generate()`, `build()`). This causes CMake to fail discovering Visual Studio.

- **Failure Rate:** ~25% of identical runs fail
- **Non-deterministic:** Same code, same machine, random failures
- **Impact:** Visual Studio detection fails with COM initialization error `0x80131904`

## Environment

- **Conan:** 2.24.0
- **Python:** 3.7.8+
- **OS:** Windows Server 2022 (or Windows 10/11)
- **CMake:** 3.28.0+
- **Visual Studio:** 2019 Enterprise or 2022 Enterprise
- **CI:** GitLab Runner, GitHub Actions, or local Windows shell

## How to Reproduce

### Prerequisites

```bash
# Install Conan 2.24.0
pip install conan==2.24.0

# Install CMake
# (download from https://cmake.org or use chocolatey: choco install cmake)

# Ensure Visual Studio is installed with C++ workload
```

### Single Run

```bash
# Clone this repository
git clone https://github.com/grabowski-d/conan-windows-repro.git
cd conan-windows-repro

# Run conan create
conan create . --build=missing
```

### Stress Test (to trigger intermittent failures)

```powershell
# Run 10 consecutive builds to catch the ~25% failure rate
python test_runner.py --runs 10
```

## Expected Output (Success)

```
mypkg/1.0: Exporting sources
mypkg/1.0: Calling generate()
============================================================
GENERATE() method - Environment Variables Check
============================================================
✓ ProgramData: C:\ProgramData
✓ SystemRoot: C:\Windows
✓ COMSPEC: C:\Windows\system32\cmd.exe
✓ PATH: C:\Program Files\...
✓ All critical environment variables present

mypkg/1.0: Calling build()
============================================================
BUILD() method - Environment Variables Check
============================================================
✓ ProgramData: C:\ProgramData
✓ SystemRoot: C:\Windows
✓ COMSPEC: C:\Windows\system32\cmd.exe
✓ All critical environment variables present

-- Selecting Windows SDK version 10.0.19041.0
-- The CXX compiler identification is MSVC 19.43.34808.0
-- Build files have been written to: build/...
```

## Failure Output (Intermittent)

```
mypkg/1.0: Calling build()
============================================================
BUILD() method - Environment Variables Check
============================================================
✗ MISSING VARIABLES (3): ProgramData, SystemRoot, COMSPEC

CMake Error at CMakeLists.txt:2 (project):
  Generator
      Visual Studio 17 2022
  could not find any instance of Visual Studio.
-- Configuring incomplete, errors occurred!
```

## Workaround

Set environment variables explicitly in the recipe:

```python
def build(self):
    import os
    # Workaround: set critical vars explicitly
    os.environ['ProgramData'] = os.environ.get('ProgramData', 'C:\\ProgramData')
    os.environ['SystemRoot'] = os.environ.get('SystemRoot', 'C:\\Windows')
    os.environ['COMSPEC'] = os.environ.get('COMSPEC', 'C:\\Windows\\system32\\cmd.exe')
    
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
```

## Investigation Hypothesis

See `INVESTIGATION.md` for detailed analysis.

## Files

- `conanfile.py` - Main recipe with environment variable checking
- `CMakeLists.txt` - Simple C++ library build configuration
- `src/math.cpp` - Simple C++ source
- `include/math.h` - Header file
- `test_runner.py` - Automated test script for stress testing
- `INVESTIGATION.md` - Technical investigation and root cause hypothesis

## Contact

Original issue reporter: [@grabowski-d](https://github.com/grabowski-d)
