from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess

from setuptools import setup
from setuptools.command.build_py import build_py


ROOT = Path(__file__).resolve().parent


def _git(*arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _branch() -> str:
    for name in ("BRACKETLAPSE_BUILD_BRANCH", "GITHUB_REF_NAME", "CI_COMMIT_REF_NAME"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    value = _git("rev-parse", "--abbrev-ref", "HEAD")
    if value and value != "HEAD":
        return value
    value = _git("name-rev", "--name-only", "HEAD")
    for prefix in ("remotes/origin/", "origin/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return "" if value == "undefined" else value


def _build_time() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    try:
        timestamp = datetime.fromtimestamp(int(epoch), timezone.utc) if epoch else None
    except ValueError:
        timestamp = None
    return (timestamp or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")


class BuildPy(build_py):
    def run(self) -> None:
        super().run()
        target = Path(self.build_lib) / "bracketlapse" / "_build_metadata.py"
        target.write_text(
            "\n".join(
                (
                    '"""Generated application build metadata."""',
                    "",
                    f"BUILD_BRANCH = {_branch()!r}",
                    f"BUILD_COMMIT = {_git('rev-parse', 'HEAD')!r}",
                    f"BUILD_TIME = {_build_time()!r}",
                    "",
                )
            ),
            encoding="utf-8",
        )


setup(cmdclass={"build_py": BuildPy})
