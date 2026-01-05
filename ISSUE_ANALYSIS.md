# GitHub Issue #19433 Environment Analysis

**Issue:** [Windows environment variables intermittently stripped during recipe execution](https://github.com/conan-io/conan/issues/19433)  
**Reporter:** grabowski-d (same user)  
**Date:** 2026-01-05  
**Status:** Reproducer setup complete

## Environment Comparison: Issue Report vs This Reproduction Setup

### Software Versions

| Component | Issue Report | Our Workflow | Status | Notes |
|-----------|--------------|--------------|--------|-------|
| **Conan** | 2.24.0 | 2.24.0 | ✅ EXACT | Exact version match |
| **Python** | 3.7.8 | 3.7.9 | ✅ COMPATIBLE | Patch release (minor) |
| **Operating System** | Windows Server 2022 | windows-2022 | ✅ EXACT | GitHub Actions runner |
| **CMake** | 3.31.6 | 3.31.6 | ✅ EXACT | Now specified exactly |
| **Visual Studio** | 2022 Enterprise (v17, toolset v143) | 2022 BuildTools | ✅ COMPATIBLE | BuildTools include v17 toolset |
| **Windows SDK** | 10.0.19041.0 (implied) | Latest available | ⚠️ AUTO | Installed with VS BuildTools |

### Installation & CI Method

| Aspect | Issue Report | Our Workflow | Notes |
|--------|--------------|--------------|-------|
| **Conan Install** | pipx | pip | Ours is more direct; pipx may isolate env vars |
| **CI Platform** | GitLab Runner 18.2.2 | GitHub Actions | Different CI systems, but tests same Conan code |
| **Shell Executor** | Git Bash (shell) | PowerShell (default) | Different shell - possible env var behavior differences |
| **Python Environment** | Inherited from runner | setup-python@v4 | Controlled environment |

## Key Findings

### ✅ Exact Matches

1. **Conan 2.24.0** - Exact version
2. **Windows Server 2022** - Same OS version
3. **CMake 3.31.6** - Now exactly matched (was 'latest')
4. **Python 3.7.x** - 3.7.9 is compatible with 3.7.8
5. **Visual Studio 2022** - BuildTools contain same toolset v143

### ⚠️ Potential Differences

1. **CI System:**
   - Issue: GitLab Runner with shell executor (Git Bash)
   - Ours: GitHub Actions with PowerShell
   - **Impact:** Environment variable handling may differ between shell implementations
   - **Mitigation:** Both use Windows Server 2022, should expose same env vars

2. **Conan Installation:**
   - Issue: pipx (isolated environment)
   - Ours: pip (system/runner environment)
   - **Impact:** pipx isolation could mask or exacerbate env var issues
   - **Status:** Our approach is more direct and realistic for CI/CD

3. **Python Version:**
   - Issue: 3.7.8
   - Ours: 3.7.9
   - **Impact:** Negligible - patch release only

## Issue Description Summary

**Problem:** On Windows, basic system environment variables (`ProgramData`, `SystemRoot`, `COMSPEC`, etc.) are **intermittently missing** (~25% failure rate) during Conan recipe execution.

**Symptoms:**
- Non-deterministic failures across 10 identical runs
- CMake fails to find Visual Studio (vswhere.exe COM error 0x80131904)
- Only affects Windows, consistent across multiple machines
- Workaround: Manually set env vars in recipe

**Root Cause:** Suspected race condition in Conan environment setup on Windows

## Reproduction Strategy

This reproducer implements:

1. **Stress Testing:** Run 10 iterations to catch ~25% failure rate
2. **Diagnostics:** Log all critical env vars in conanfile.py
3. **Environment Match:** Exact versions from issue report
4. **CMake Integration:** Uses CMake with Visual Studio generator (triggers vswhere.exe)
5. **Results Export:** JSON output for analysis

## Test Execution Flow

```
1. Setup Environment (Python 3.7.9, Conan 2.24.0, CMake 3.31.6, VS 2022)
2. Detect Conan Profile (conan profile detect --force)
3. Single Test Run (conan create . --build=missing)
4. Stress Test (10 iterations with conan remove cache between runs)
5. Capture Results (test_results.json with pass/fail status)
6. Upload Artifacts (GitHub Actions artifact storage)
```

## Expected Outcomes

### If Issue Reproduces (GitHub Actions)
✅ Will see ~25% failure rate (2-3 failures in 10 runs)
✅ Confirms issue is not GitLab-specific
✅ Can be used to validate future Conan patches

### If Issue Does NOT Reproduce (GitHub Actions)
⚠️ May indicate the issue is GitLab/shell-executor specific
⚠️ May have been fixed in newer Conan versions
⚠️ GitHub Actions environment may handle env vars differently

## Files Involved

- `.github/workflows/test.yml` - GitHub Actions workflow (exact versions)
- `conanfile.py` - Conan recipe with env var diagnostics
- `CMakeLists.txt` - CMake project (triggers Visual Studio discovery)
- `test_runner.py` - Stress test harness (10 iterations)
- `SETUP_VERSIONS.md` - Detailed version documentation
- `test_results.json` - Test results artifact

## Next Steps

1. Run workflow and observe results
2. If failures occur: capture logs and submit to Conan project
3. If no failures: test with GitLab Runner setup to isolate CI differences
4. Use reproducer as benchmark for future Conan versions
