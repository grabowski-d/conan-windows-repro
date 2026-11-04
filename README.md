# Conan: environment variables lost with `clean_system_proxy=True`

[![Repro](https://github.com/grabowski-d/conan-windows-repro/actions/workflows/repro.yml/badge.svg)](https://github.com/grabowski-d/conan-windows-repro/actions/workflows/repro.yml)

Related issue: [conan-io/conan#19433](https://github.com/conan-io/conan/issues/19433)

On Windows, system variables such as `SystemRoot`, `ProgramData` or `ComSpec`
intermittently disappear during Conan runs, which then breaks vswhere / CMake /
MSVC detection. This repository reproduces the root cause in isolation.

## Root cause

`ConanRequester._call_method` in Conan **2.32.0**
(`conan/internal/rest/conan_requester.py`):

```python
def _call_method(self, method, url, **kwargs):
    popped = False
    if self._clean_system_proxy:
        old_env = dict(os.environ)                      # (1) snapshot
        for var_name in ("http_proxy", "https_proxy", "ftp_proxy", "all_proxy", "no_proxy"):
            popped = True if os.environ.pop(var_name, None) else popped
            popped = True if os.environ.pop(var_name.upper(), None) else popped
    ...
    try:
        ...                                             # HTTP request
    finally:
        if popped:
            os.environ.clear()                          # (2) remove every variable
            os.environ.update(old_env)                  # (3) put them back one by one
```

`os.environ.clear()` and `os.environ.update()` are pure-Python loops calling
`unsetenv` / `putenv` per variable, so they are not atomic. When several requests
run in threads (e.g. parallel downloads):

* between (2) and (3) every other thread sees a partial or empty environment;
* if another thread takes its snapshot (1) in that window, it later "restores"
  the partial snapshot and the missing variables are **lost permanently**;
* `dict(os.environ)` and `urllib`'s proxy lookup iterate `os.environ` and raise
  `KeyError` when a key vanishes mid-iteration.

The code only runs when `core.net.http:clean_system_proxy=True` **and** at least
one proxy variable is set (`NO_PROXY` is enough), otherwise `popped` stays `False`.

## Reproduction

`repro.py` uses the real `ConanRequester` from the installed Conan and real HTTP
requests to a local server. It sets up:

| Factor | Value |
| --- | --- |
| Conan | 2.32.0 |
| Python | 3.8 |
| Config | `core.net.http:clean_system_proxy=True` |
| Proxy variable | `NO_PROXY` set |
| Thread switching | `sys.setswitchinterval(1e-6)` |
| Random variables | 250 `RND_*` (at least 200; more variables = longer `clear()`/`update()` window) |
| Verification variables | `REPRO_CHECK_1..5` with fixed values, plus `SystemRoot`, `ProgramData`, `ComSpec`, `windir`, `PATH`, `TEMP` when present |

8 threads each send 25 requests per round. Meanwhile an observer thread reads the
verification variables (like recipe code would). After each round the environment
is compared with the starting one.

```bat
py -3.8 -m venv venv
venv\Scripts\activate
pip install conan==2.32.0
set NO_PROXY=localhost,127.0.0.1
python repro.py
```

Exit code `1` means the problem was reproduced. Useful options:

```
--rounds N         number of rounds (default 50)
--threads N        concurrent requesters (default 8)
--requests N       requests per thread per round (default 25)
--random-vars N    random variables (default 250)
--keep-going       do not stop at the first reproduction
--fixed            control run: _call_method patched to never modify os.environ
```

Example output (original code, Python 3.8, run with an otherwise empty environment):

```
Conan   : 2.32.0
switch  : 1e-06
NO_PROXY: localhost,127.0.0.1
env vars: 259 total, 250 random, checked: REPRO_CHECK_1, ..., REPRO_CHECK_5, PATH
mode    : original Conan _call_method
round   1/50   1.17s  lost=245 changed=0 transient=393311 errors=20  <-- REPRODUCED
  permanently LOST checked vars: REPRO_CHECK_1, REPRO_CHECK_2, REPRO_CHECK_3, REPRO_CHECK_4, REPRO_CHECK_5
  permanently lost (first 10 of 245): NO_PROXY, REPRO_CHECK_1, ..., RND_AAWJIZHHFH, ...
  observer saw missing/wrong: PATH x3309, REPRO_CHECK_1 x78001, ...
  exceptions from requester.get (first 3 of 20):
     KeyError: 'NO_PROXY'
     KeyError: 'PATH'
     KeyError: 'RND_KKMZJEMSTB'

RESULT: REPRODUCED - environment variables were lost/overwritten
```

* `lost` – variables missing after all requests finished (permanent loss)
* `changed` – variables with a different value afterwards
* `transient` – how often the observer saw a verification variable missing
* `errors` – exceptions raised from `ConanRequester.get` (`KeyError`)

The `--fixed` control run passes, which shows the problem is the modification of
`os.environ` in `_call_method`.

## CI

`.github/workflows/repro.yml` runs on `windows-2022` with Python 3.8:

* `original` – Conan 2.32.0 as released, expected to **fail** (reproduced);
* `control` – `repro.py --fixed --rounds 10`, expected to pass (one round takes
  ~30 s on the hosted Windows runner, the original code fails in round 1).

## Notes

* With the default switch interval (5 ms) the race is rarely hit in a short run;
  `sys.setswitchinterval(1e-6)` makes it show up within the first round.
* The race is not Windows-specific Python code; it also reproduces on Linux.
  It hurts on Windows because losing `SystemRoot` / `ProgramData` / `ComSpec`
  breaks COM, vswhere and Visual Studio detection.
* Restoring only the popped proxy variables is not enough: `os.environ.pop()`
  itself is not atomic and other threads iterate `os.environ`. A fix should not
  mutate the process environment at all. The control run uses
  `requests.Session.trust_env = False`; note that this also makes `requests`
  ignore `.netrc` and `REQUESTS_CA_BUNDLE`, so a real fix may prefer passing
  explicit `proxies` per request.
