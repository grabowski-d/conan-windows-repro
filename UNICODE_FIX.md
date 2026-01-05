# Unicode Encoding Fix for Python 3.7 Windows

**Date:** 2026-01-05 15:37 CET  
**Issue:** UnicodeEncodeError on Windows with Python 3.7  
**Root Cause:** Windows command prompt uses cp1252 encoding, can't handle Unicode symbols  
**Solution:** Replace Unicode characters with ASCII equivalents

## Problem

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 2: character maps to <undefined>
  File "C:\hostedtoolcache\windows\Python\3.7.9\x64\lib\encodings\cp1252.py", line 19, in encode
```

Python 3.7 na Windows domyślnie używa cp1252 encoding, który nie obsługuje wielu Unicode symboli, takich jak:
- `✓` (U+2713 - CHECK MARK)
- `✗` (U+2717 - BALLOT X)
- `⚠` (U+26A0 - WARNING SIGN)

## Solution

Zastąpić Unicode symbole ASCII equivalentami:

| Unicode | ASCII |
|---------|-------|
| `✓` | `[OK]` |
| `✗` | `[MISSING]` |
| `⚠` | `[WARNING]` |

## Files Changed

### 1. `test_runner.py`

**Before:**
```python
if failed > 0:
    print(f"\n⚠ ISSUE REPRODUCED! {failed}/{self.runs} runs failed.")
    ...
else:
    print(f"\n✓ No failures detected in {self.runs} runs.")
```

**After:**
```python
if failed > 0:
    print(f"\n[WARNING] ISSUE REPRODUCED! {failed}/{self.runs} runs failed.")
    ...
else:
    print(f"\n[OK] No failures detected in {self.runs} runs.")
```

### 2. `conanfile.py`

**Before:**
```python
for var, val in present_vars:
    self.output.info(f"✓ {var}: {val}")

if missing_vars:
    self.output.warning(f"✗ MISSING VARIABLES ({len(missing_vars)}): {', '.join(missing_vars)}")
else:
    self.output.success("✓ All critical environment variables present")
```

**After:**
```python
for var, val in present_vars:
    self.output.info(f"[OK] {var}: {val}")

if missing_vars:
    self.output.warning(f"[MISSING] MISSING VARIABLES ({len(missing_vars)}): {', '.join(missing_vars)}")
else:
    self.output.success("[OK] All critical environment variables present")
```

## Commits

1. **5980b7c** - Fix test_runner.py for cp1252 compatibility
2. **0056ba5** - Fix conanfile.py for cp1252 compatibility

## Why This Happens

Windows console (cmd.exe) uses **cp1252** (Windows-1252) encoding:
- Limited to ~256 characters
- Doesn't include modern Unicode symbols
- Common in legacy Windows systems

Python 3.8+ improved Unicode handling, but 3.7 requires explicit handling.

## Impact

✅ **Before:** Script crashes with UnicodeEncodeError  
✅ **After:** Script runs successfully and produces clean output

## Example Output (Fixed)

```
======================================================================
TEST SUMMARY
======================================================================
Total Runs:    10
Passed:        10 (100.0%)
Failed:        0 (0.0%)
Errors:        0
Timeouts:      0
======================================================================

[OK] No failures detected in 10 runs.
Issue may not be reproducible in current environment.

Results saved to: test_results.json
```

## References

- [Python 3.7 Unicode Support](https://docs.python.org/3.7/howto/unicode.html)
- [Windows cp1252 Encoding](https://en.wikipedia.org/wiki/Windows-1252)
- [Python sys.stdout encoding](https://docs.python.org/3/library/sys.html#sys.stdout)
