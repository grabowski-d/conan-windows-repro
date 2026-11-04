"""
Reproduction: Conan 2.32.0 ``ConanRequester._call_method`` loses / overwrites
environment variables when ``core.net.http:clean_system_proxy=True`` and
several HTTP requests run concurrently (e.g. parallel downloads).

Offending code (conan/internal/rest/conan_requester.py, Conan 2.32.0)::

    def _call_method(self, method, url, **kwargs):
        popped = False
        if self._clean_system_proxy:
            old_env = dict(os.environ)                       # (1) snapshot
            for var_name in ("http_proxy", ..., "no_proxy"):
                popped = True if os.environ.pop(var_name, None) else popped
                popped = True if os.environ.pop(var_name.upper(), None) else popped
        ...
        try:
            ... request ...
        finally:
            if popped:
                os.environ.clear()                           # (2) wipe everything
                os.environ.update(old_env)                   # (3) re-add one by one

``os.environ.clear()`` and ``os.environ.update()`` are pure-Python loops that
call ``unsetenv``/``putenv`` for every variable, so they are not atomic. While
thread A is between (2) and (3), any other thread sees a partial (or empty)
environment. If thread B takes its snapshot (1) in that window, B later
"restores" that partial snapshot and the missing variables are gone for good.

This script uses the real ``ConanRequester`` from the installed Conan and real
HTTP requests to a local server. Exit code 1 means the problem was reproduced.
"""
import argparse
import http.server
import os
import platform
import random
import string
import sys
import threading
import time

import conan
from conan.internal.model.conf import ConfDefinition
from conan.internal.rest.conan_requester import ConanRequester

PROXY_VARS = ("http_proxy", "https_proxy", "ftp_proxy", "all_proxy", "no_proxy")

# Fixed variables with known values, used to verify the environment.
CHECK_VARS = {"REPRO_CHECK_%d" % i: "fixed-value-%d" % i for i in range(1, 6)}

# Real Windows variables whose loss breaks vswhere/CMake/MSVC detection.
WINDOWS_VARS = ("SystemRoot", "ProgramData", "ComSpec", "windir", "PATH", "TEMP")


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def start_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d/" % server.server_address[1]


def random_vars(count, rng):
    result = {}
    while len(result) < count:
        name = "RND_" + "".join(rng.choice(string.ascii_uppercase) for _ in range(10))
        value = "".join(rng.choice(string.ascii_letters + string.digits)
                        for _ in range(rng.randint(10, 120)))
        result[name] = value
    return result


def fixed_call_method(self, method, url, **kwargs):
    """Control: same request, but os.environ is never modified.

    Even restoring only the popped proxy variables is not safe: os.environ.pop()
    is not atomic and urllib's getproxies_environment() iterates os.environ in
    other threads. Here system proxies are ignored with requests' trust_env=False.
    """
    if self._clean_system_proxy:
        self._http_requester.trust_env = False
    all_kwargs = self._add_kwargs(url, kwargs)
    return getattr(self._http_requester, method)(url, **all_kwargs)


def run_round(requester, url, baseline, checks, threads, requests_per_thread):
    errors = []
    transient = {}          # var -> how many times the observer saw it missing/wrong
    stop = threading.Event()
    start = threading.Barrier(threads + 1)

    def worker():
        start.wait()
        for _ in range(requests_per_thread):
            try:
                requester.get(url)
            except Exception as e:  # e.g. KeyError raised by dict(os.environ)
                errors.append("%s: %s" % (type(e).__name__, e))

    def observer():
        # Simulates recipe / tool code reading the environment meanwhile.
        while not stop.is_set():
            for name, value in checks.items():
                if os.environ.get(name) != value:
                    transient[name] = transient.get(name, 0) + 1

    workers = [threading.Thread(target=worker) for _ in range(threads)]
    obs = threading.Thread(target=observer)
    for t in workers:
        t.start()
    obs.start()
    start.wait()
    for t in workers:
        t.join()
    stop.set()
    obs.join()

    final = dict(os.environ)
    missing = sorted(k for k in baseline if k not in final)
    changed = sorted(k for k in baseline if k in final and final[k] != baseline[k])
    return missing, changed, transient, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rounds", type=int, default=50)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--requests", type=int, default=25, help="requests per thread per round")
    parser.add_argument("--random-vars", type=int, default=250)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--switch-interval", type=float, default=1e-6)
    parser.add_argument("--keep-going", action="store_true",
                        help="run all rounds instead of stopping at the first reproduction")
    parser.add_argument("--fixed", action="store_true",
                        help="control run: patch _call_method so it restores only proxy vars")
    args = parser.parse_args()

    print("Python  :", sys.version.split()[0], platform.platform())
    print("Conan   :", conan.__version__)
    if sys.version_info[:2] != (3, 8):
        print("WARNING : reproduction targets Python 3.8")
    if conan.__version__ != "2.32.0":
        print("WARNING : reproduction targets Conan 2.32.0")
    if args.random_vars < 200:
        print("WARNING : use at least 200 random variables")

    sys.setswitchinterval(args.switch_interval)
    print("switch  :", sys.getswitchinterval())

    # NO_PROXY must be set, otherwise _call_method pops nothing and never restores.
    os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,.example.com")
    print("NO_PROXY:", os.environ["NO_PROXY"])

    rng = random.Random(args.seed)
    os.environ.update(random_vars(args.random_vars, rng))
    os.environ.update(CHECK_VARS)

    checks = dict(CHECK_VARS)
    for name in WINDOWS_VARS:
        if os.environ.get(name) is not None:
            checks[name] = os.environ[name]
    baseline = dict(os.environ)
    print("env vars: %d total, %d random, checked: %s"
          % (len(baseline), args.random_vars, ", ".join(checks)))

    conf = ConfDefinition()
    conf.loads("core.net.http:clean_system_proxy=True")
    if args.fixed:
        ConanRequester._call_method = fixed_call_method
        print("mode    : CONTROL (patched _call_method)")
    else:
        print("mode    : original Conan _call_method")
    requester = ConanRequester(conf)
    assert requester._clean_system_proxy is True

    server, url = start_server()
    reproduced = False
    try:
        for i in range(1, args.rounds + 1):
            t0 = time.time()
            missing, changed, transient, errors = run_round(
                requester, url, baseline, checks, args.threads, args.requests)
            bad = bool(missing or changed or transient or errors)
            reproduced = reproduced or bad
            print("round %3d/%d  %5.2fs  lost=%d changed=%d transient=%d errors=%d%s"
                  % (i, args.rounds, time.time() - t0, len(missing), len(changed),
                     sum(transient.values()), len(errors), "  <-- REPRODUCED" if bad else ""))
            if bad:
                lost_checks = [k for k in checks if k in missing]
                if lost_checks:
                    print("  permanently LOST checked vars:", ", ".join(lost_checks))
                if missing:
                    print("  permanently lost (first 10 of %d): %s"
                          % (len(missing), ", ".join(missing[:10])))
                if changed:
                    print("  changed values:", ", ".join(changed[:10]))
                if transient:
                    print("  observer saw missing/wrong:",
                          ", ".join("%s x%d" % kv for kv in sorted(transient.items())))
                if errors:
                    print("  exceptions from requester.get (first 3 of %d):" % len(errors))
                    for e in errors[:3]:
                        print("    ", e)
                if not args.keep_going:
                    break
            # Start every round from the same, complete environment.
            os.environ.clear()
            os.environ.update(baseline)
    finally:
        server.shutdown()

    print()
    if reproduced:
        print("RESULT: REPRODUCED - environment variables were lost/overwritten")
        return 1
    print("RESULT: not reproduced in %d rounds" % args.rounds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
