import os

from conan import ConanFile
from conan.tools.files import save


class Pkg(ConanFile):
    """Trivial binary package, created many times under different names."""
    version = "1.0"
    package_type = "header-library"

    def package(self):
        # Some payload so every package download is a real file transfer.
        save(self, os.path.join(self.package_folder, "include", self.name + ".h"),
             "// %s\n" % self.name + "x" * 64 * 1024)
