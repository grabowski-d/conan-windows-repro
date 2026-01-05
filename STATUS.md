# Conan Windows Repro - Status Report

**Last Updated:** 2026-01-05 15:19 CET  
**Repository:** [conan-windows-repro](https://github.com/grabowski-d/conan-windows-repro)

## Issue Summary

**Original Issue:** [conan-io/conan#19433](https://github.com/conan-io/conan/issues/19433)  
**Problem:** Windows environment variables intermittently stripped during Conan 2.24.0 recipe execution (~25% failure rate)

## Repository Status

✅ **Repository Created**
- Owner: grabowski-d
- Type: Private
- Status: Ready for testing

## Workflow Status

### First Attempt ❌
- **Run ID:** 20719861814
- **Status:** Failed
- **Error:** YAML syntax errors in `.github/workflows/test.yml`
  - Malformed escape characters `\"`
  - Missing newlines in YAML blocks
  - Python 3.7 version (deprecated)

### Fixes Applied ✅

**Commit:** `dbbe6f1dca9f0d08579012431f8d74aa879a519b`

1. **YAML Syntax Correction**
   - Removed escaped quotes `\"` → proper YAML formatting
   - Fixed indentation and block structure
   - Added proper line breaks between steps

2. **Python Version Update**
   - Changed from `3.7` → `3.11` (3.7 reached EOL)
   - Ensures compatibility with current pip packages

3. **Build Tools Installation**
   - Added `|| true` fallback for Visual Studio install
   - Prevents workflow failure if VS already installed

4. **Proper YAML Structure**
   ```yaml
   - name: Install Conan
     run: pip install conan==2.24.0
   
   - name: Verify Conan Installation
     run: conan --version
   ```

### Second Attempt (Pending) ⏳

**Commit:** `6a414ceaacd4a2796ca2b27dedf20a21d851860e`

- Workflow triggered by push
- Expected to run on: `windows-2022` runner
- Pipeline steps:
  1. Checkout code
  2. Install Python 3.11
  3. Install CMake
  4. Install Visual Studio Build Tools 2022
  5. Install Conan 2.24.0
  6. Run single `conan create` test
  7. Run stress test (10 iterations)
  8. Upload `test_results.json`

**Status:** Check [Actions tab](https://github.com/grabowski-d/conan-windows-repro/actions) for real-time status

## Files & Structure

```
conan-windows-repro/
├── conanfile.py                    # Conan recipe with env var diagnostics
├── CMakeLists.txt                  # C++ build configuration
├── include/math.h                  # Library header
├── src/math.cpp                    # Library implementation
├── test_runner.py                  # Stress test script (10+ runs)
├── README.md                       # Project overview
├── LOCAL_TESTING.md                # Windows local testing guide
├── INVESTIGATION.md                # Technical analysis
├── WORKFLOW_FIX.md                 # This fix documentation
├── STATUS.md                       # This file
├── .gitignore                      # Git ignores
└── .github/workflows/test.yml      # GitHub Actions workflow (FIXED)
```

## Key Features

✅ **Comprehensive Testing**
- Single run test: `conan create . --build=missing`
- Stress test: `python test_runner.py --runs 10`
- Automated CI/CD via GitHub Actions

✅ **Environment Diagnostics**
- Logs 13 critical Windows env vars
- Marks MISSING vars with ✗ indicator
- JSON test results for analysis

✅ **Documentation**
- Step-by-step local testing guide (Polish)
- Technical investigation & hypotheses
- Workaround code examples

## How to Use

### Local Testing (Windows)
```powershell
# Clone repo
git clone https://github.com/grabowski-d/conan-windows-repro.git
cd conan-windows-repro

# Single test
conan create . --build=missing

# Stress test (to catch ~25% failure)
python test_runner.py --runs 10
```

### Monitor CI/CD
- Go to: https://github.com/grabowski-d/conan-windows-repro/actions
- Watch workflow progress
- Download `test_results.json` artifact

## Expected Outcomes

✅ **Success Scenario**
- All steps complete without errors
- Single test: `conan create` succeeds
- Stress test: 10/10 passes (or shows consistent failure pattern)
- Artifacts uploaded: `test_results.json`

❌ **Failure Scenario**
- Stress test shows ~25% FAIL rate
- Env vars appear as "MISSING"
- CMake fails to find Visual Studio
- Confirms issue is reproducible

## Next Steps

1. **Monitor Workflow Execution**
   - Check [Actions](https://github.com/grabowski-d/conan-windows-repro/actions) tab
   - Review logs if failure occurs

2. **Analyze Test Results**
   - Download `test_results.json`
   - Review failure patterns

3. **Local Testing** (if needed)
   - Follow `LOCAL_TESTING.md`
   - Run stress tests on your machine
   - Capture detailed logs

4. **Report to Conan Team**
   - Use findings to create detailed bug report
   - Include reproduction steps
   - Reference `INVESTIGATION.md` hypothesis

## Links

- **Original Issue:** https://github.com/conan-io/conan/issues/19433
- **Repository:** https://github.com/grabowski-d/conan-windows-repro
- **Actions:** https://github.com/grabowski-d/conan-windows-repro/actions
- **Conan Docs:** https://docs.conan.io/

---

**Repository Owner:** [@grabowski-d](https://github.com/grabowski-d)  
**Created:** 2026-01-05  
**Type:** Private (Conan issue reproduction)
