# Setup Versions & Configuration

**Last Updated:** 2026-01-05 18:36 CET  
**Status:** Configuration locked for reproducibility

## Software Versions

### Python
- **Version:** 3.7.9 (Python 3.7)
- **Installation:** GitHub Actions setup-python action
- **Reason:** Legacy environment testing, minimal python version for Windows CI

```yaml
- name: Set up Python 3.7
  uses: actions/setup-python@v4
  with:
    python-version: '3.7'
```

### Conan
- **Version:** 2.24.0
- **Installation Method:** pip (not pipx)
- **Why not pipx?** Pipx requires Python 3.8+, but we need 3.7 support

```bash
python -m pip install --upgrade pip
python -m pip install conan==2.24.0
```

### CMake
- **Version:** Latest (3.31.6)
- **Installation:** lukka/get-cmake GitHub Action

```yaml
- name: Install CMake
  uses: lukka/get-cmake@latest
  with:
    cmake-version: 3.31.6
```

### Visual Studio Build Tools
- **Version:** 2022
- **Workload:** Native Desktop Development
- **Installation:** Chocolatey

```bash
choco install visualstudio2022buildtools \
  --packageParameters "--add Microsoft.VisualStudio.Workload.NativeDesktop --passive --norestart"
```

### Windows Runner
- **OS:** windows-2022
- **GitHub Actions:** ubuntu-latest equivalent for Windows

## Command Invocation Pattern

### Why `python -m conans.client.command` instead of `conan`?

When using `pip install conan`, the command line entry point may not be available in GitHub Actions environment. Using the module directly is more reliable:

```bash
# This might not work in CI:
conan --version

# This always works:
python -m conans.client.command --version
```

### Test Execution

**Profile Detection:**
```bash
python -m conans.client.command profile detect --force
```

**Single Test:**
```bash
python -m conans.client.command create . --build=missing
```

**Stress Test (10 iterations):**
```bash
python test_runner.py --runs 10
```

## Environment Variables Checked

### Critical Windows Variables
- `ProgramData` - Windows program data directory
- `SystemRoot` - Windows system directory (usually C:\Windows)
- `COMSPEC` - Command interpreter (cmd.exe)
- `PATH` - Executable search path
- `PATHEXT` - Executable extensions
- `TEMP` / `TMP` - Temporary directory
- `USERPROFILE` - User home directory
- `HOMEDRIVE` / `HOMEPATH` - User home path parts
- `WINDIR` - Windows directory
- `PROCESSOR_ARCHITECTURE` - CPU architecture
- `NUMBER_OF_PROCESSORS` - CPU count

### Visual Studio Variables (Optional)
- `VSINSTALLDIR` - Visual Studio installation
- `VisualStudioVersion` - VS version
- `VCINSTALLDIR` - VC++ installation
- `VCToolsInstallDir` - VC++ tools location
- `INCLUDE` - C++ include paths
- `LIB` - C++ library paths

## Issue Being Reproduced

**GitHub Issue:** [conan#19433](https://github.com/conan-io/conan/issues/19433)  
**Symptom:** Intermittent (~25%) CMake build failures due to missing environment variables  
**Root Cause:** Race condition in Conan environment setup on Windows  
**Expected Failure Rate:** ~25% across 10 runs

## Output Files

### Test Results
- **File:** `test_results.json`
- **Format:** JSON array of test run results
- **Retention:** Uploaded as GitHub Actions artifact

```json
[
  {
    "run": 1,
    "status": "PASS",
    "returncode": 0,
    "timestamp": "2026-01-05T18:36:45.123456"
  },
  {
    "run": 2,
    "status": "FAIL",
    "returncode": 1,
    "timestamp": "2026-01-05T18:36:52.654321"
  }
]
```

## Debugging Commands

If you need to debug locally:

```bash
# Install Conan
python -m pip install conan==2.24.0

# Detect profile
python -m conans.client.command profile detect --force

# Run single test
python -m conans.client.command create . --build=missing

# Run stress test
python test_runner.py --runs 10

# View test results
cat test_results.json | python -m json.tool
```

## Related Files

- `.github/workflows/test.yml` - GitHub Actions workflow
- `test_runner.py` - Stress test harness
- `conanfile.py` - Conan recipe with env var diagnostics
- `CMakeLists.txt` - CMake build configuration
- `test_results.json` - Test results artifact
