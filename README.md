# Conan Windows Environment Variables Issue - Reproduction Project

**Conan Issue:** [#19433 - Windows environment variables intermittently stripped during recipe execution](https://github.com/conan-io/conan/issues/19433)

## 🆕 Latest Updates

**January 21, 2026** - Implemented improvements suggested by [memsharded](https://github.com/memsharded) (Conan co-founder):
- ⚡ **Ultra-fast testing** - `conan create` now completes in ~2 seconds (no actual build)
- 🔍 **Multi-location checks** - Environment variables monitored in 6+ locations (global scope, generate, build, etc.)
- 🤖 **Automated CI** - 300+ test iterations per push, hourly scheduled runs
- 📊 **Instant failure detection** - Tests fail immediately when env vars go missing

See [MEMSHARDED_IMPROVEMENTS.md](MEMSHARDED_IMPROVEMENTS.md) for detailed documentation.

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

## Quick Start

### Prerequisites

```bash
# Install Conan 2.24.0
pip install conan==2.24.0

# Install CMake 3.31.6 (recommended for testing)
choco install cmake --version=3.31.6

# Ensure Visual Studio is installed with C++ workload
```

### Single Test (Fast - ~2 seconds)

```bash
# Clone this repository
git clone https://github.com/grabowski-d/conan-windows-repro.git
cd conan-windows-repro

# Detect Conan profile
conan profile detect --force

# Run single test
conan create . --build=missing
```

### Stress Test (Recommended)

```powershell
# Run 50 consecutive builds to catch intermittent failures
python test_runner.py --runs 50

# Or more intensive testing
python test_runner.py --runs 200
```

### CI Testing

The repository includes GitHub Actions workflow that automatically:
- Runs quick test on every push
- Runs 300 stress test iterations (3x100 parallel)
- Runs 200 rapid-fire tests every hour
- Fails immediately when env vars go missing
- Uploads detailed failure logs

Manually trigger workflow:
1. Go to [Actions tab](https://github.com/grabowski-d/conan-windows-repro/actions)
2. Select "Conan Windows Env Vars Test"
3. Click "Run workflow"
4. Enter desired iteration count

## Expected Output

### Success Case

```
============================================================
[GLOBAL SCOPE] Environment Variables Check
============================================================
[GLOBAL][OK] ProgramData: C:\ProgramData
[GLOBAL][OK] SystemRoot: C:\Windows
[GLOBAL][OK] COMSPEC: C:\Windows\system32\cmd.exe
...

mypkg/1.0: Calling generate()
======================================================================
[GENERATE] Environment Variables Check
======================================================================
[GENERATE] [OK] ProgramData: C:\ProgramData
[GENERATE] SUCCESS: All 6 critical variables present

mypkg/1.0: Calling build()
======================================================================
[BUILD] Environment Variables Check
======================================================================
[BUILD] [OK] ProgramData: C:\ProgramData
[BUILD] SUCCESS: All 6 critical variables present
[BUILD] Skipping actual build - just checking environment

mypkg/1.0: Package created
```

### Failure Case (If Issue Occurs)

```
mypkg/1.0: Calling build()
======================================================================
[BUILD] Environment Variables Check
======================================================================
[BUILD] [CRITICAL MISSING] ProgramData
[BUILD] [CRITICAL MISSING] SystemRoot
[BUILD] FAILURE: 2/6 variables missing: ProgramData, SystemRoot

ERROR: RuntimeError: Critical environment variables missing at [BUILD]: ProgramData, SystemRoot
```

## Testing Strategy

Based on memsharded's recommendations, this repository uses a multi-tiered testing approach:

### Tier 1: Minimal Recipe Testing
- **Speed:** ~2 seconds per iteration
- **Purpose:** Rapidly iterate to catch intermittent issues
- **Method:** No actual build, only env var validation
- **Location:** `conanfile.py` with stripped `build()` method

### Tier 2: Multi-location Monitoring
- **Locations checked:**
  - Global scope (before class definition)
  - `__init__()` method
  - `layout()` method
  - `generate()` method
  - `build()` method
  - `package()` method
- **Purpose:** Identify exactly where env vars disappear

### Tier 3: Continuous CI Testing
- **Quick test:** Single run on every commit
- **Stress test:** 300 iterations per push (3 parallel runners)
- **Scheduled test:** 200 iterations every hour
- **Manual test:** Custom iteration count on demand

## Critical Environment Variables Monitored

1. **ProgramData** - Common application data (originally reported issue)
2. **SystemRoot** - Windows installation directory
3. **COMSPEC** - Command processor path
4. **PATH** - Executable search paths
5. **TEMP** - Temporary files directory
6. **TMP** - Alternative temporary files directory

## Workaround

If you encounter this issue in production, temporarily set variables explicitly:

```python
def build(self):
    import os
    # Workaround: ensure critical vars are present
    if not os.environ.get('ProgramData'):
        os.environ['ProgramData'] = 'C:\\ProgramData'
    if not os.environ.get('SystemRoot'):
        os.environ['SystemRoot'] = 'C:\\Windows'
    if not os.environ.get('COMSPEC'):
        os.environ['COMSPEC'] = 'C:\\Windows\\system32\\cmd.exe'
    
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
```

## Investigation Documents

- [MEMSHARDED_IMPROVEMENTS.md](MEMSHARDED_IMPROVEMENTS.md) - Latest improvements based on Conan team feedback
- [INVESTIGATION.md](INVESTIGATION.md) - Technical root cause analysis
- [STATUS.md](STATUS.md) - Current reproduction status
- [LOCAL_TESTING.md](LOCAL_TESTING.md) - Local testing guide

## Contributing

If you can reproduce this issue:

1. Run the stress test: `python test_runner.py --runs 100`
2. If failures occur, save the `test_results.json` file
3. Comment on [Issue #19433](https://github.com/conan-io/conan/issues/19433) with:
   - Your environment details
   - Failure rate observed
   - Test results file
   - Any patterns you noticed

## Contact

Original issue reporter: [@grabowski-d](https://github.com/grabowski-d)

Conan team contact: [@memsharded](https://github.com/memsharded) (Diego Rodriguez-Losada, Conan co-founder)
