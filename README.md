# Conan Windows Environment Variables Issue - Reproduction Project

[![Advanced Testing](https://github.com/grabowski-d/conan-windows-repro/actions/workflows/advanced-test.yml/badge.svg)](https://github.com/grabowski-d/conan-windows-repro/actions/workflows/advanced-test.yml)

**Conan Issue:** [#19433 - Windows environment variables intermittently stripped during recipe execution](https://github.com/conan-io/conan/issues/19433)

## 🆕 Latest Updates

**January 21, 2026 (v2)** - Critical fixes applied:
- ✅ **Fixed missing CMakeLists.txt** - Added minimal CMake configuration
- ✅ **Fixed RuntimeError false positives** - Changed to flag-based failure detection
- ✅ **Fixed CMD batch syntax** - Corrected modulo operator usage
- ✅ **Fixed Bash grep regex** - Added proper `-E` flag
- ✅ **Added syntax validation** - `validate_syntax.py` for pre-commit checks

**January 21, 2026 (v1)** - Advanced testing implementation:
- 🔬 **5 comprehensive test suites** in `conanfile_advanced.py`
- 🔍 **Subprocess monitoring** with `monitor_conan.py` (monkey-patching)
- 🚀 **1,300+ CI iterations** across PowerShell, CMD, and **Git Bash**
- 🧵 **Race condition detection** with 5 concurrent threads

See [ADVANCED_TESTING.md](ADVANCED_TESTING.md) for comprehensive documentation.

## Problem Summary

When running Conan 2.24.0 recipes on Windows, critical system environment variables (`ProgramData`, `SystemRoot`, `COMSPEC`, etc.) are **intermittently missing** during recipe execution. This causes CMake/Visual Studio detection to fail.

- **Failure Rate:** ~25% of identical runs
- **Non-deterministic:** Same code, same machine, different results
- **Impact:** vswhere.exe COM error `0x80131904` - "could not find any instance of Visual Studio"
- **Environment:** GitLab Runner with Git Bash → Python → Conan

## Quick Start

### Advanced Testing (Recommended)

```bash
# Clone repository
git clone https://github.com/grabowski-d/conan-windows-repro.git
cd conan-windows-repro

# Install Conan 2.24.0
pip install conan==2.24.0

# Detect profile
conan profile detect --force

# Single test with monitoring
python monitor_conan.py "conan create . --name=mypkg --version=1.0 -sf=conanfile_advanced.py"

# Multiple iterations (Git Bash for GitLab simulation)
for i in {1..100}; do
    echo "Iteration $i"
    conan create . --name=mypkg --version=1.0 -sf=conanfile_advanced.py
done
```

### GitHub Actions CI

1. Fork this repository
2. Go to **Actions** tab  
3. Workflow runs automatically on push
4. Manual trigger: Select workflow → "Run workflow" → Customize iterations

**What gets tested:**
- PowerShell: 500 iterations
- CMD: 200 iterations
- **Git Bash: 200 iterations** ⚠️ (matches GitLab Runner)
- Parallel stress: 4 × 100 iterations

## 🛠️ Troubleshooting

### Recent Fixes (2026-01-21)

#### Issue 1: "conan create" fails immediately
**Symptom:** `ERROR: [Errno 2] No such file or directory: 'CMakeLists.txt'`  
**Cause:** Missing CMakeLists.txt file  
**Status:** ✅ **FIXED** - Added minimal CMakeLists.txt

#### Issue 2: Workflow exit code 1 with 0 failures
**Symptom:** Tests pass but job fails  
**Cause:** `RuntimeError` raised unconditionally in `_verify_critical_vars()`  
**Status:** ✅ **FIXED** - Changed to `_critical_failure` flag, only raises in `package()` if needed

#### Issue 3: CMD batch syntax error
**Symptom:** `if %%i%%50==0` causes parsing error  
**Cause:** Incorrect modulo operator in batch script  
**Status:** ✅ **FIXED** - Changed to `set /A MOD=%%i %% 50` then `if !MOD!==0`

#### Issue 4: Bash grep regex error
**Symptom:** `grep: Invalid back reference`  
**Cause:** Extended regex without `-E` flag  
**Status:** ✅ **FIXED** - Changed to `grep -E "pattern1|pattern2"`

### Syntax Validation

Before committing changes, validate syntax:

```bash
python validate_syntax.py
```

Validates:
- ✅ Python files (AST parsing)
- ✅ YAML workflows (if PyYAML installed)
- ✅ Bash scripts (basic checks)

## 🎯 Root Cause Hypothesis

Based on [Python subprocess documentation](https://github.com/python/cpython/issues/120836):

```python
# WRONG - loses environment variables
subprocess.run(['cmake', ...], env={'SOME_VAR': 'value'})

# CORRECT - preserves all variables
env = os.environ.copy()
env['SOME_VAR'] = 'value'
subprocess.run(['cmake', ...], env=env)
```

If Conan creates subprocess environment without copying `os.environ`, critical Windows variables (`ProgramData`, `SystemRoot`, `COMSPEC`) are lost, causing COM initialization failures.

## Testing Methodology

### 1. Advanced Conanfile (`conanfile_advanced.py`)

**5 Test Suites:**
- **TEST 1**: Subprocess environment inheritance (default, copy, empty)
- **TEST 2**: Race condition detection (5 concurrent threads × 10 checks)
- **TEST 3**: Environment modification monitoring (before/after snapshots)
- **TEST 4**: Different subprocess.Popen env passing methods
- **TEST 5**: Comprehensive reporting across all execution points

### 2. Monitoring Script (`monitor_conan.py`)

**Capabilities:**
- Monkey-patches `subprocess.Popen` globally
- Intercepts ALL subprocess calls from Conan
- Logs environment passed to each subprocess
- Detects missing critical variables
- Generates JSON reports: `conan_monitor_*.json`

**Usage:**
```bash
python monitor_conan.py "conan create . --name=mypkg --version=1.0"
# Check conan_monitor_*.json for subprocess details
```

### 3. CI Testing Matrix

| Shell | Iterations | Why Important |
|-------|------------|---------------|
| PowerShell | 500 | Standard Windows automation |
| CMD | 200 | Classic batch environment |
| **Git Bash** | **200** | **⚠️ Matches GitLab Runner** |
| Parallel | 4×100 | Stress test for race conditions |

**Total:** 1,300+ tests per workflow run

## Expected Results

### Success (All Tests Pass)

```
[TEST 1A] subprocess inherits: ProgramData=C:\ProgramData
[TEST 1B] explicit env copy works: SystemRoot=C:\Windows
[TEST 2] No race conditions in 50 concurrent checks
[TEST 3] Environment stable - no modifications detected
[TEST 4-default] Default (inherit): OK
[TEST 4-copy] os.environ.copy(): OK

FINAL REPORT
============
Total snapshots taken: 6
Snapshot 1: layout          [OK]
Snapshot 2: generate_start  [OK]
Snapshot 3: generate_end    [OK]
Snapshot 4: build_start     [OK]
Snapshot 5: build_end       [OK]
Snapshot 6: package         [OK]

✓ All environment checks passed
TEST RESULT: SUCCESS - All tests passed
```

### Failure (Issue Reproduced)

```
[TEST 1A] FAILED: ProgramData not inherited: %ProgramData%
[TEST 2] RACE CONDITION DETECTED: 5/50 checks failed
  - missing: ['ProgramData', 'SystemRoot']

FINAL REPORT
============
Snapshot 3: build_start     [FAILED]
  Missing: ProgramData, SystemRoot

⚠️  ISSUE DETECTED at: build_start
TEST RESULT: FAILURE - Critical issues detected

ERROR: RuntimeError: Critical environment variable issues detected.
```

## 📊 Current Status

### Testing Progress

- **PowerShell (500 iter)**: ✅ All pass - environment stable in standard shell
- **CMD (200 iter)**: 🔄 Testing after syntax fixes
- **Git Bash (200 iter)**: 🔄 Testing after fixes - **critical for GitLab simulation**
- **Parallel (400 iter)**: 🔄 Testing after fixes

### Key Findings

1. **Standard environments work** - No failures in PowerShell/CMD suggest issue is environment-specific
2. **Git Bash is critical** - MSYS2 environment translation may be root cause
3. **Monitoring needed** - `monitor_conan.py` will show exact subprocess calls if failure occurs

## 📦 Repository Structure

```
.
├── conanfile_advanced.py       # 🧵 Advanced 5-test conanfile
├── monitor_conan.py            # 🔍 Subprocess monitoring script
├── CMakeLists.txt              # ⚙️ Minimal CMake configuration
├── validate_syntax.py          # ✅ Pre-commit syntax checker
├── .github/workflows/
│   └── advanced-test.yml       # 🚀 1,300+ iteration CI
├── ADVANCED_TESTING.md         # 📖 Full documentation
├── INVESTIGATION.md            # 🔬 Technical analysis
└── README.md                   # 📝 This file
```

## Workaround (Production)

If you encounter this in production:

```python
def generate(self):
    import os
    # Workaround: ensure critical vars exist
    critical_vars = {
        'ProgramData': 'C:\\ProgramData',
        'SystemRoot': 'C:\\Windows',
        'COMSPEC': 'C:\\Windows\\system32\\cmd.exe'
    }
    for var, default in critical_vars.items():
        if not os.environ.get(var):
            os.environ[var] = default
            self.output.warning(f"Set missing {var}={default}")
```

## 🤝 Contributing

If you can reproduce or have insights:

1. **Run monitoring**: `python monitor_conan.py "conan create ..."`
2. **Save reports**: Keep `conan_monitor_*.json` files
3. **Comment on issue**: [conan-io/conan#19433](https://github.com/conan-io/conan/issues/19433)
4. **Share environment**: OS version, Python version, shell type, runner details

## 📚 Documentation

- [ADVANCED_TESTING.md](ADVANCED_TESTING.md) - Complete testing guide
- [INVESTIGATION.md](INVESTIGATION.md) - Technical root cause analysis  
- [MEMSHARDED_IMPROVEMENTS.md](MEMSHARDED_IMPROVEMENTS.md) - Conan team collaboration

## 👤 Contact

**Issue Reporter:** [@grabowski-d](https://github.com/grabowski-d)  
**Related Issue:** [conan-io/conan#19433](https://github.com/conan-io/conan/issues/19433)  
**Conan Team:** [@memsharded](https://github.com/memsharded) (Diego Rodriguez-Losada)

---

**License:** MIT - Free to use for debugging similar environment issues
