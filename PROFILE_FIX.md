# Conan Profile Detection Fix

**Date:** 2026-01-05 15:25 CET  
**Issue:** Missing default Conan profile in GitHub Actions runner  
**Solution:** Add `conan profile detect --force` step

## Problem

```
ERROR: The default build profile 'C:\Users\runneradmin\.conan2\profiles\default' doesn't exist.
You need to create a default profile (type 'conan profile detect' command)
```

W GitHub Actions runner, Conan 2.24.0 wymaga domyślnego profilu, który nie istnieje z automatu.

## Solution Applied

**Commit:** `a2c55aa39f0b32f53574a5353cdceeddc3cf3e9e`

Dodany nowy step w workflow:

```yaml
- name: Detect Conan Profile
  run: conan profile detect --force
```

## Co to robi?

`conan profile detect --force` automatycznie:
1. Skanuje system w poszukiwaniu dostępnych kompilatorów
2. Tworzy domyślny profil w `~/.conan2/profiles/default`
3. Konfiguruje:
   - Architekturę (x86_64)
   - Compiler (MSVC/GCC/Clang)
   - Build type (Release/Debug)
   - Wersję C++ standard

## Workflow Order

```yaml
1. Install Python 3.7
2. Install CMake
3. Install Visual Studio 2022 Build Tools
4. Install Conan 2.24.0
5. Verify Conan version
6. ✅ Detect Conan Profile (NEW)
7. Run single test: conan create
8. Run stress test
9. Upload artifacts
```

## Status

✅ **Profile detection added**
✅ **Workflow ready to proceed**
✅ **conan create should now work**

## Expected Output

```
Detecting default profile...

Found MSVC compiler at C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Tools\MSVC\14.43.34808
Gcc (the compiler program seems to be MSVC)
Compiler: MSVC
Compiler version: 193
CMake: 3.31.6
MS Build: 17.12.3.64512

Profile generated at: C:\Users\runneradmin\.conan2\profiles\default
```

## Reference

- [Conan Profile Detect Docs](https://docs.conan.io/2.x/cli/commands/profile.html#conan-profile-detect)
- [Conan GitHub Actions Setup](https://docs.conan.io/2.x/integrations/github_actions.html)
