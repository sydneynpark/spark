#!/usr/bin/env python3
"""
Packages one of this repo's Lambda projects as <project>/.build/lambda.zip:
the project's src/ plus its locked dependencies (src/requirements.txt),
installed for the Python version in <project>/.python-version. Terraform
(terraform/modules/python_lambda) deploys the zip, with a runtime read from
that same file.

Usage, from the repo root:
    uv run --no-project scripts/build_lambda.py backend
"""

import argparse
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

# All functions run on x86_64 Lambda runtimes, which are Amazon Linux 2023
# (glibc 2.34) for python3.12 and later. Without --python-platform, uv would
# install wheels for whatever machine runs this build -- fine for pure-Python
# deps, but silently wrong for compiled ones (pydantic-core, cryptography,
# ...), producing a package that fails to import on Lambda with an error like
# "No module named 'pydantic_core._pydantic_core'".
LAMBDA_PLATFORM = "x86_64-manylinux_2_34"


def write_zip(package_dir, zip_path):
    """Zip package_dir's contents reproducibly: the same files always make a
    byte-identical zip, whatever their timestamps or the OS building it, so
    Terraform only redeploys a function when its code actually changed."""
    files = sorted(
        (path.relative_to(package_dir).as_posix(), path)
        for path in package_dir.rglob("*")
        if path.is_file()
    )
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in files:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3  # Unix, so external_attr holds Unix permissions
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description="Package a Lambda project for deployment.")
    parser.add_argument("project_dir", type=Path, help="e.g. backend or ContentManagement/UpdateBookReview")
    project_dir = parser.parse_args().project_dir

    python_version = (project_dir / ".python-version").read_text(encoding="utf-8").strip()
    src_dir = project_dir / "src"
    build_dir = project_dir / ".build"
    package_dir = build_dir / "package"
    zip_path = build_dir / "lambda.zip"

    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(
        src_dir,
        package_dir,
        ignore=shutil.ignore_patterns("__pycache__", "requirements*.in", "requirements*.txt"),
    )

    # `uv run` exposes its own executable as $UV to the scripts it runs.
    uv = os.environ.get("UV", "uv")
    subprocess.run(
        [
            uv, "pip", "install",
            "--target", str(package_dir),
            "--python-platform", LAMBDA_PLATFORM,
            "--python-version", python_version,
            "--only-binary", ":all:",
            "--require-hashes",
            "-r", str(src_dir / "requirements.txt"),
        ],
        check=True,
    )

    # Console-script launchers for the deps (e.g. bin/flask). Lambda never
    # runs them, and they differ by build OS (.exe on Windows).
    if (package_dir / "bin").exists():
        shutil.rmtree(package_dir / "bin")

    write_zip(package_dir, zip_path)
    print(f"Built {zip_path} for Python {python_version}")


if __name__ == "__main__":
    main()
