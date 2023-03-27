# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
Check the current repo against all previous supported versions of µsort

If any previous version triggers sorting/formatting changes, we consider that
worthy of a major version bump, and should be reverted or at least reconsidered.

See the Versioning Guide for details.

TODO: include other projects as part of testing, like black, libcst, etc
"""

import json
import platform
import subprocess
import sys
import venv
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional
from urllib.request import urlopen

from packaging.version import Version

REPO_ROOT = Path(__file__).parent.resolve()
MINIMUM_VERSION = Version("1.0.0")
PYPI_JSON_URL = "https://pypi.org/pypi/usort/json"


def get_current_version() -> Version:
    with TemporaryDirectory() as td:
        root = Path(td).resolve()
        usort = setup_virtualenv(root)
        proc = subprocess.run(
            (usort, "--version"), encoding="utf-8", capture_output=True, check=True
        )
        return Version(proc.stdout.rpartition(" ")[-1])


def get_public_versions(
    current_version: Version, minimum_version: Version
) -> List[Version]:
    """
    Find all non-yanked versions of usort.

    Limits results such that TARGET_VERSION <= CANDIDATE_VERSION <= CURRENT_VERSION
    """
    with urlopen(PYPI_JSON_URL) as request:
        data = json.loads(request.read())

    versions: List[Version] = []
    for version_str in data["releases"]:
        version = Version(version_str)
        if all(dist["yanked"] for dist in data["releases"][version_str]):
            continue
        if minimum_version <= version <= current_version:
            versions.append(version)

    return sorted(versions, reverse=True)


def setup_virtualenv(root: Path, version: Optional[Version] = None) -> Path:
    """
    Create venv, install usort, return path to `usort` binary
    """

    venv_path = root / f"venv-{version}" if version else root / "venv-local"
    venv.create(venv_path, clear=True, with_pip=True)

    bin_dir = (
        venv_path / "Scripts" if platform.system() == "Windows" else venv_path / "bin"
    )
    python = bin_dir / "python"

    subprocess.run((python, "-m", "pip", "-q", "install", "-U", "pip"), check=True)
    if version:
        subprocess.run(
            (python, "-m", "pip", "-q", "install", "-U", f"usort=={version}"),
            check=True,
        )
    else:
        subprocess.run(
            (python, "-m", "pip", "-q", "install", "-U", REPO_ROOT), check=True
        )
    return bin_dir / "usort"


def check_versions(versions: List[Version]) -> List[Version]:
    """
    Format with local version, then check all released versions for regressions
    """
    with TemporaryDirectory() as td:
        root = Path(td).resolve()

        try:
            print("sorting with local version ...")
            usort = setup_virtualenv(root)
            subprocess.run((usort, "--version"), check=True)
            subprocess.run((usort, "format", "usort"), check=True)
            print("done\n")
        except Exception as e:
            return [("local", e)]

        failures: List[Version] = []
        for version in versions:
            try:
                print(f"checking version {version} ...")
                usort = setup_virtualenv(root, version)
                subprocess.run((usort, "--version"), check=True)
                subprocess.run((usort, "check", "usort"), check=True)
                print("clean\n")
            except Exception as e:
                failures.append((version, e))

        return failures


def main() -> None:
    current_version = get_current_version()
    minimum_version = MINIMUM_VERSION
    print(f"{current_version = !s}\n{minimum_version = !s}\n")

    versions = get_public_versions(current_version, minimum_version)
    versions_str = ", ".join(str(v) for v in versions)
    print(f"discovered versions {versions_str}\n")

    failures = check_versions(versions)
    if failures:
        print("Sorting failed in versions:")
        for version, exc in failures:
            print(f"  {version}: {exc}")
        sys.exit(1)
    else:
        print("success!")


if __name__ == "__main__":
    main()
