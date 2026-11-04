import json
import os
import sys

from conan import ConanFile
from conan.errors import ConanException

# Same knob as in repro.py: make the interpreter switch threads very often.
# This runs when Conan loads the recipe, i.e. before the parallel downloads.
sys.setswitchinterval(float(os.getenv("REPRO_SWITCH_INTERVAL", "1e-6")))

_HERE = os.path.dirname(os.path.abspath(__file__))


class Consumer(ConanFile):
    """Requires many packages so `conan install` downloads them in parallel,
    then verifies in generate() that the process environment is intact."""
    name = "consumer"
    version = "1.0"

    def requirements(self):
        count = int(os.getenv("REPRO_PKG_COUNT", "40"))
        for i in range(count):
            self.requires("pkg%02d/1.0" % i)

    def generate(self):
        # The expected environment is stored in a file: if it were passed through
        # environment variables, it could be lost as well.
        with open(os.path.join(_HERE, "expected_env.json")) as f:
            expected = json.load(f)
        env, checks = expected["env"], expected["checks"]
        missing = sorted(k for k in env if os.environ.get(k) is None)
        changed = sorted(k for k in env if k not in missing and os.environ[k] != env[k])
        lost_checks = [k for k in checks if k in missing or k in changed]
        self.output.info("env check: %d expected, %d missing, %d changed"
                         % (len(env), len(missing), len(changed)))
        if missing or changed:
            raise ConanException(
                "REPRO: environment variables lost/overwritten after parallel download: "
                "missing=%d changed=%d checked=[%s] first missing=[%s]"
                % (len(missing), len(changed), ", ".join(lost_checks), ", ".join(missing[:10])))
        self.output.success("REPRO: environment intact")
