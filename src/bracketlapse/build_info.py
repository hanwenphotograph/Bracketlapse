"""Public application build metadata."""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
import subprocess

from . import __version__
from ._build_metadata import BUILD_BRANCH, BUILD_COMMIT, BUILD_TIME


def build_info_document() -> dict[str, str | None]:
    repository = _repository_metadata()
    installed = _direct_url_metadata()
    return {
        "version": __version__,
        "branch": BUILD_BRANCH or repository.get("branch") or installed.get("branch"),
        "commit": BUILD_COMMIT or repository.get("commit") or installed.get("commit"),
        "build_time": BUILD_TIME or repository.get("build_time"),
    }


def write_build_info() -> None:
    print(json.dumps(build_info_document(), ensure_ascii=True, separators=(",", ":")))


def _repository_metadata() -> dict[str, str]:
    root = _repository_root()
    if root is None:
        return {}
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        branch = _normalize_branch(_git(root, "name-rev", "--name-only", "HEAD"))
    return {
        key: value
        for key, value in {
            "branch": branch,
            "commit": _git(root, "rev-parse", "HEAD"),
            "build_time": _git(root, "show", "-s", "--format=%cI", "HEAD"),
        }.items()
        if value
    }


def _repository_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    return None


def _git(root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _normalize_branch(value: str) -> str:
    for prefix in ("remotes/origin/", "origin/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def _direct_url_metadata() -> dict[str, str]:
    try:
        value = distribution("bracketlapse").read_text("direct_url.json")
        document = json.loads(value) if value else {}
    except (PackageNotFoundError, json.JSONDecodeError):
        return {}
    vcs = document.get("vcs_info")
    if not isinstance(vcs, dict):
        return {}
    branch = vcs.get("requested_revision")
    commit = vcs.get("commit_id")
    return {
        key: value
        for key, value in {"branch": branch, "commit": commit}.items()
        if isinstance(value, str) and value
    }
