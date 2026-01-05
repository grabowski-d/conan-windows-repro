# Local Testing Instructions

Bezśrednie testowanie problemu na lokalnej maszynie Windows.

## Wymagania

### Obowiązkowe
- **Windows 10/11 lub Windows Server 2019+**
- **Python 3.7+** (najlepiej 3.9+)
- **Visual Studio 2019 Enterprise lub 2022 Enterprise** (z C++ workload)
- **CMake 3.25+**
- **Git**

### Instalacja

#### 1. Zainstaluj Conan 2.24.0

```powershell
# Preferowana metoda: pipx (izolowane środowisko)
pip install pipx
pipx install conan==2.24.0

# Lub bezpośrednio w pip
pip install conan==2.24.0

# Weryfikacja
conan --version
# Output: Conan version 2.24.0
```

#### 2. Zainstaluj CMake

**Opcja A: Chocolatey (najszybsza)**
```powershell
choco install cmake
cmake --version
```

**Opcja B: Pobranie z cmake.org**
```powershell
# Przejdź do https://cmake.org/download/
# Pobierz: cmake-3.31.6-windows-x86_64.msi
# Zainstaluj i dodaj do PATH
cmake --version
```

#### 3. Weryfikuj Visual Studio

```powershell
# Sprawdzi czy vswhere.exe znalazł VS
vswhere -all
# Powinien zwrócić: Visual Studio 2022, v17.x, ...
```

## Klonowanie Repozytorium

```powershell
git clone https://github.com/grabowski-d/conan-windows-repro.git
cd conan-windows-repro
```

## Test 1: Pojedyncze Uruchomienie

```powershell
# Czyszczenie cache'u
conan remove mypkg/* -c

# Uruchomienie
conan create . --build=missing
```

### Oczekiwany Wynik (Sukces)

```
mypkg/1.0: Exporting sources
mypkg/1.0: Calling generate()
============================================================
GENERATE() method - Environment Variables Check
============================================================
✓ ProgramData: C:\ProgramData
✓ SystemRoot: C:\Windows
✓ COMSPEC: C:\Windows\system32\cmd.exe
...
✓ All critical environment variables present

mypkg/1.0: Calling build()
============================================================
BUILD() method - Environment Variables Check
============================================================
✓ ProgramData: C:\ProgramData
...
-- The CXX compiler identification is MSVC 19.43.34808.0
-- Build files have been written to: build/...
```

### Wynik Niepowodzenia (Intermittent)

Jeśli zobaczysz:

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
```

**Toę problem! Zażę wygęnę Test 2 (Stress Test) aby złapać pattern.**

## Test 2: Stress Test (10+ Iteracji)

Zamiast pojedynczego uruchomienia, uruchom wiele razy aby złapać 25% failure rate:

```powershell
# Uruchom 10 iteracji
python test_runner.py --runs 10
```

Lub użyj PowerShell loop:

```powershell
for ($i = 1; $i -le 10; $i++) {
    Write-Host "\n=== RUN $i ===" -ForegroundColor Yellow
    conan remove mypkg/* -c -q
    conan create . --build=missing 2>&1 | Select-String "MISSING|could not find"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED" -ForegroundColor Red
    } else {
        Write-Host "PASSED" -ForegroundColor Green
    }
}
```

### Analiza Wyników

Po zakończeniu skrypt stworzy `test_results.json`:

```json
[
  {"run": 1, "status": "PASS", "timestamp": "2026-01-05T..."  },
  {"run": 2, "status": "PASS", "timestamp": "2026-01-05T..."  },
  {"run": 3, "status": "FAIL", "timestamp": "2026-01-05T..."  },
  {"run": 4, "status": "PASS", "timestamp": "2026-01-05T..."  },
  ...
]
```

Ana lizy:
- **Wszystkie PASS**: Problem może być niezaprodukowalny w tym środowisku
- **~25% FAIL**: Problemę złapać! To jest poszukiwana race condition
- **>50% FAIL**: Inny problem (np. VS nie zainstalowany prawidlowo)

## Test 3: Diagnostyka Zmiennych Środ owiskowych

Jeśli chcesz zobaczyć dokładnie które zmienne są niedostępne:

```powershell
# Dodaj do conanfile.py w build() metodzie:

def build(self):
    import json
    
    # Dump całego środowiska przed CMake
    env_before = dict(os.environ)
    
    # Zapisz do pliku
    with open('env_before_cmake.json', 'w') as f:
        json.dump(env_before, f, indent=2)
    
    self.output.info(f"Environment dumped to env_before_cmake.json")
    
    # Teraz uruchom cmake
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
```

Następnie w PowerShell:

```powershell
conan create .
cat build/env_before_cmake.json | ConvertFrom-Json | Select -ExpandProperty ProgramData
```

## Test 4: Obejście (Workaround)

Jeśli problem jest reprodukowalny, możesz go obejść eksplicite ustawiając zmienne:

```python
# W conanfile.py - build() metoda

def build(self):
    import os
    
    # Obejście: upewnij się że zmienne są ustawione
    os.environ.setdefault('ProgramData', 'C:\\ProgramData')
    os.environ.setdefault('SystemRoot', 'C:\\Windows')
    os.environ.setdefault('COMSPEC', 'C:\\Windows\\system32\\cmd.exe')
    os.environ.setdefault('PATH', 'C:\\Windows\\system32')
    
    # Teraz użyj CMake
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
```

## Test 5: GitLab Runner (CI/CD)

Jeśli testujesz w GitLab CI z Windows shell executor:

```yaml
test:windows:repro:
  stage: test
  tags:
    - windows
    - shell
  before_script:
    - pip install conan==2.24.0
    - conan --version
  script:
    - conan create . --build=missing
    - python test_runner.py --runs 10
  artifacts:
    paths:
      - test_results.json
    when: always
```

## Zbieranie Danych dla Raportu

Jeśli znaleźłeś problem, zbierz te dane do raportu:

1. **test_results.json** - wyniki z test_runner.py
2. **Logi całego uruchomienia**:
   ```powershell
   conan create . --build=missing -vv 2>&1 | Out-File -FilePath conan_verbose.log
   ```
3. **Wersje narzędzi**:
   ```powershell
   conan --version
   cmake --version
   vswhere -all
   python --version
   [Environment]::GetEnvironmentVariables() | Out-File env_dump.txt
   ```
4. **System info**:
   ```powershell
   systeminfo | Out-File system_info.txt
   ```

## Troubleshooting

### Problem: "Conan not found"
```powershell
# Sprawdź czy Python jest w PATH
python -m conan --version

# Jeśli pipx, użyj pełnej ścieżki
~/.local/bin/conan --version
```

### Problem: "Visual Studio not found"
```powershell
# Sprawdź VS instalację
vswhere -all

# Zainstaluj Visual Studio Community (free) jeśli nie ma Enterprise
choco install visualstudio2022community --package-parameters="--add Microsoft.VisualStudio.Workload.NativeDesktop"
```

### Problem: "CMake not found"
```powershell
choco install cmake
# Lub upewnij się że PATH zawiera: C:\Program Files\CMake\bin
```

### Problem: "Conan remove: not a valid Conan reference"
```powershell
# Jeśli conan remove nie działa
conan remove \"*\" -c
# Lub czyszczenie manualnie
rm -r ~/.conan2/p/
```

## Dodatkowe Informacje

- **Oryginalny issue:** https://github.com/conan-io/conan/issues/19433
- **Konan Docs:** https://docs.conan.io/
- **CMake Docs:** https://cmake.org/documentation/
- **Visual Studio:** https://visualstudio.microsoft.com/
