"""
Reproduction through the regular Conan CLI (no calls into Conan internals).

1. start a local ``conan_server`` and a clean ``CONAN_HOME`` with
   ``core.net.http:clean_system_proxy=True`` and ``core.download:parallel=8``
2. create and upload ``--packages`` small binary packages
3. repeatedly: ``conan remove "*:*" -c`` + ``conan install consumer``
   with NO_PROXY, 250 random variables and fixed REPRO_CHECK_* variables
   in the environment; the consumer recipe verifies the environment in
   ``generate()`` (after Conan downloaded all packages in parallel threads)

The consumer recipe calls ``sys.setswitchinterval(1e-6)`` when it is loaded.
Exit code 1 means the problem was reproduced, either as

* variables missing in the consumer's ``generate()`` (permanent loss), or
* a download failing with ``KeyError('<env var>')`` raised from ``os.environ``.

Exit code 2 means an unexpected failure.
"""
import argparse
import json
import os
import random
import re
import shutil
import socket
import string
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK_VARS = {"REPRO_CHECK_%d" % i: "fixed-value-%d" % i for i in range(1, 6)}
WINDOWS_VARS = ("SystemRoot", "ProgramData", "ComSpec", "windir", "PATH", "TEMP")

SERVER_CONF = """[server]
jwt_secret: repro-jwt-secret
jwt_expire_minutes: 120
ssl_enabled: False
port: {port}
public_port:
host_name: 127.0.0.1
authorize_timeout: 1800
disk_storage_path: {storage}
disk_authorize_timeout: 1800
updown_secret: repro-updown-secret

[write_permissions]
*/*@*/*: demo

[read_permissions]
*/*@*/*: *

[users]
demo: demo
"""


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(port, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("conan_server did not start on port %d" % port)


def conan(args, env, check=True):
    cmd = [sys.executable, "-m", "conans.conan"] + args
    proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError("command failed: conan %s" % " ".join(args))
    return proc


def random_vars(count, rng):
    result = {}
    while len(result) < count:
        name = "RND_" + "".join(rng.choice(string.ascii_uppercase) for _ in range(10))
        result[name] = "".join(rng.choice(string.ascii_letters + string.digits)
                               for _ in range(rng.randint(10, 120)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=20, help="conan install runs")
    parser.add_argument("--packages", type=int, default=40)
    parser.add_argument("--parallel", type=int, default=2, help="core.download:parallel")
    parser.add_argument("--random-vars", type=int, default=250)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--switch-interval", default="1e-6")
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--control", action="store_true",
                        help="control run: core.net.http:clean_system_proxy=False")
    args = parser.parse_args()

    work = tempfile.mkdtemp(prefix="conan-repro-")
    print("work dir:", work)
    port = free_port()

    # --- conan_server -------------------------------------------------------
    server_home = os.path.join(work, "server")
    os.makedirs(server_home)
    with open(os.path.join(server_home, "server.conf"), "w") as f:
        f.write(SERVER_CONF.format(port=port, storage=os.path.join(server_home, "data")))
    server_env = dict(os.environ, CONAN_SERVER_HOME=server_home)
    server_log = open(os.path.join(work, "server.log"), "w")
    server = subprocess.Popen([sys.executable, "-m", "conans.server.server_launcher"],
                              env=server_env, stdout=server_log, stderr=subprocess.STDOUT)
    reproduced = False
    try:
        wait_for_port(port)

        # --- client home ----------------------------------------------------
        env = dict(os.environ, CONAN_HOME=os.path.join(work, "conan_home"))
        conan(["profile", "detect", "--force"], env)
        clean = "False" if args.control else "True"
        with open(os.path.join(env["CONAN_HOME"], "global.conf"), "w") as f:
            f.write("core.net.http:clean_system_proxy=%s\n" % clean)
            f.write("core.download:parallel=%d\n" % args.parallel)
        conan(["remote", "remove", "*"], env)
        conan(["remote", "add", "local", "http://127.0.0.1:%d" % port], env)
        conan(["remote", "login", "local", "demo", "-p", "demo"], env)

        # --- packages -------------------------------------------------------
        t0 = time.time()
        pkg = os.path.join(HERE, "pkg")
        for i in range(args.packages):
            conan(["export-pkg", pkg, "--name=pkg%02d" % i], env)
        conan(["upload", "*", "-r", "local", "-c"], env)
        print("created and uploaded %d packages in %.1fs" % (args.packages, time.time() - t0))

        # --- environment for the reproduction ---------------------------------
        consumer = os.path.join(work, "consumer")
        os.makedirs(consumer)
        shutil.copy(os.path.join(HERE, "consumer", "conanfile.py"), consumer)

        run_env = dict(env)
        run_env.setdefault("NO_PROXY", "localhost,127.0.0.1,.example.com")
        run_env.update(random_vars(args.random_vars, random.Random(args.seed)))
        run_env.update(CHECK_VARS)
        run_env["REPRO_PKG_COUNT"] = str(args.packages)
        run_env["REPRO_SWITCH_INTERVAL"] = args.switch_interval
        # os.environ keys are upper-case on Windows (SYSTEMROOT), so match case-insensitively.
        windows = {w.upper() for w in WINDOWS_VARS}
        checks = list(CHECK_VARS) + [k for k in run_env if k.upper() in windows]
        with open(os.path.join(consumer, "expected_env.json"), "w") as f:
            json.dump({"env": run_env, "checks": checks}, f)

        print("Python  :", sys.version.split()[0])
        print("Conan   :", conan(["--version"], env).stdout.strip())
        print("conf    : clean_system_proxy=%s, download:parallel=%d" % (clean, args.parallel))
        print("NO_PROXY:", run_env["NO_PROXY"])
        print("switch  :", args.switch_interval, "(set by consumer recipe)")
        print("env vars: %d total, %d random, checked: %s"
              % (len(run_env), args.random_vars, ", ".join(checks)))
        print("mode    :", "CONTROL (clean_system_proxy=False)" if args.control else "original")

        env_names = {k.upper() for k in run_env} | {"NO_PROXY"}
        counts = {"ok": 0, "env_lost": 0, "keyerror": 0, "other": 0}
        for i in range(1, args.runs + 1):
            # Recipes stay in the cache, binaries are removed -> every install downloads
            # all packages again, in core.download:parallel threads.
            conan(["remove", "*:*", "-c"], env)
            t0 = time.time()
            proc = conan(["install", consumer, "-r", "local"], run_env, check=False)
            out = proc.stdout
            # KeyError('<env var name>') from os.environ, reported by Conan as a
            # download error, e.g.: Error downloading file http://...: ''NO_PROXY''
            keyerrors = sorted({m for m in re.findall(r"'([A-Za-z_][A-Za-z0-9_]*)'", out)
                                if m.upper() in env_names})
            if proc.returncode == 0 and "REPRO: environment intact" in out:
                kind, detail = "ok", ""
            elif "REPRO: environment variables lost" in out:
                kind = "env_lost"
                detail = next(l for l in out.splitlines() if "REPRO: environment" in l).strip()
            elif keyerrors:
                kind = "keyerror"
                detail = "download failed with KeyError for env vars: %s" % ", ".join(keyerrors[:8])
            else:
                kind, detail = "other", "\n".join(out.splitlines()[-30:])
            counts[kind] += 1
            label = {"ok": "OK", "env_lost": "REPRODUCED (env lost in recipe)",
                     "keyerror": "REPRODUCED (KeyError in download)",
                     "other": "UNEXPECTED FAILURE rc=%d" % proc.returncode}[kind]
            print("run %3d/%d  %5.1fs  %s" % (i, args.runs, time.time() - t0, label))
            if detail:
                for line in detail.splitlines():
                    print("    " + line[:400])
            if kind == "other":
                break
            if kind != "ok" and not args.keep_going:
                break
    finally:
        server.terminate()
        server.wait()
        server_log.close()
        shutil.rmtree(work, ignore_errors=True)

    print()
    print("summary : %s" % ", ".join("%s=%d" % kv for kv in counts.items()))
    if counts["other"]:
        print("RESULT: UNEXPECTED FAILURE (see output above)")
        return 2
    if counts["env_lost"] or counts["keyerror"]:
        print("RESULT: REPRODUCED with the Conan CLI")
        return 1
    print("RESULT: not reproduced in %d runs" % sum(counts.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
