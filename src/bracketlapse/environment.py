from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess

from .common import BracketlapseError, log
from .deflicker import ensure_deflick_supported_extension
from .installers import emit_command_output, install_system_tool, update_system_tool
from .installers import known_binary_directories

SIMPLE_DEFLICKER_REPO = "https://github.com/SHthemW/simple-deflicker.git"
SIMPLE_DEFLICKER_BRANCH = "master"


def ensure_runtime_environment(args: argparse.Namespace, command: str) -> None:
    if command == "video":
        log.info("Checking runtime environment.")
        ensure_system_tool("ffmpeg")
        return

    if not args.no_deflick:
        ensure_deflick_supported_extension(args.ext)

    log.info("Checking runtime environment.")
    ensure_system_tool("enfuse")
    if args.align:
        ensure_system_tool("align_image_stack")
    if not args.no_video:
        ensure_system_tool("ffmpeg")
    if not args.no_deflick:
        args.deflick_bin = str(ensure_simple_deflicker(args.deflick_bin))


def update_runtime_environment(dependencies: list[str] | None = None) -> None:
    targets = normalize_update_dependencies(dependencies)
    log.info("Updating runtime dependencies.")
    if "enfuse" in targets:
        update_system_tool("enfuse")
    if "ffmpeg" in targets:
        update_system_tool("ffmpeg")
    if "git" in targets:
        update_system_tool("git")
    if "go" in targets:
        update_system_tool("go")
    if "simple-deflicker" in targets:
        update_simple_deflicker()


def ensure_system_tool(name: str) -> str:
    executable = find_executable(name)
    if executable is not None:
        log.info(f"Found {name}: {executable}")
        return executable

    log.warn(f"{name} was not found. Trying automatic installation.")
    install_system_tool(name)
    executable = find_executable(name)
    if executable is not None:
        log.info(f"Installed {name}: {executable}")
        return executable

    raise BracketlapseError(
        f"{name} is still unavailable after automatic installation attempt."
    )


def ensure_simple_deflicker(value: str) -> Path:
    existing = find_executable(value)
    if existing is not None:
        log.info(f"Found simple-deflicker: {existing}")
        return Path(existing)

    output = resolve_simple_deflicker_output(value)
    if output.exists():
        log.info(f"Found cached simple-deflicker: {output}")
        return output

    log.warn("simple-deflicker was not found. Downloading and building it.")
    git = ensure_system_tool("git")
    go = ensure_system_tool("go")
    clone_or_update_simple_deflicker(git)
    build_simple_deflicker(go, output)
    if not output.exists():
        raise BracketlapseError(f"simple-deflicker build did not produce {output}")
    return output


def update_simple_deflicker() -> Path:
    git = ensure_system_tool("git")
    go = ensure_system_tool("go")
    clone_or_update_simple_deflicker(git)
    output = simple_deflicker_bin_dir() / executable_name("simple-deflicker")
    build_simple_deflicker(go, output)
    if not output.exists():
        raise BracketlapseError(f"simple-deflicker build did not produce {output}")
    log.info(f"Updated simple-deflicker: {output}")
    return output


def normalize_update_dependencies(dependencies: list[str] | None) -> list[str]:
    if not dependencies:
        return ["enfuse", "ffmpeg", "git", "go", "simple-deflicker"]

    normalized = [dependency.strip().lower() for dependency in dependencies if dependency.strip()]
    if not normalized:
        raise BracketlapseError("No dependency names were provided.")

    aliases = {
        "deflicker": "simple-deflicker",
        "simple_deflicker": "simple-deflicker",
        "simpledeflicker": "simple-deflicker",
    }
    normalized = [aliases.get(dependency, dependency) for dependency in normalized]

    valid = {"enfuse", "ffmpeg", "git", "go", "simple-deflicker"}
    unknown = sorted(set(normalized) - valid)
    if unknown:
        raise BracketlapseError(f"Unknown dependency name(s): {', '.join(unknown)}")

    deduped: list[str] = []
    for dependency in normalized:
        if dependency not in deduped:
            deduped.append(dependency)
    return deduped


def find_executable(value: str) -> str | None:
    candidate = Path(value).expanduser()
    if candidate.parent != Path(".") or candidate.is_absolute():
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
        return None

    executable = shutil.which(value)
    if executable is not None:
        return executable
    for directory in known_binary_directories():
        path = directory / executable_name(value)
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    return None


def clone_or_update_simple_deflicker(git: str) -> None:
    source_dir = simple_deflicker_source_dir()
    source_dir.parent.mkdir(parents=True, exist_ok=True)
    if not source_dir.exists():
        run_setup_command([
            git,
            "clone",
            "-b",
            SIMPLE_DEFLICKER_BRANCH,
            SIMPLE_DEFLICKER_REPO,
            str(source_dir),
        ])
        return

    run_setup_command([git, "fetch", "origin", SIMPLE_DEFLICKER_BRANCH], cwd=source_dir)
    run_setup_command([git, "checkout", SIMPLE_DEFLICKER_BRANCH], cwd=source_dir)
    run_setup_command([git, "pull", "--ff-only", "origin", SIMPLE_DEFLICKER_BRANCH], cwd=source_dir)


def build_simple_deflicker(go: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run_setup_command([
        go,
        "build",
        "-tags",
        "cli",
        "-o",
        str(output),
    ], cwd=simple_deflicker_source_dir())


def run_setup_command(command: list[str], cwd: Path | None = None) -> None:
    log.info(f"Running setup command: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    emit_command_output(result)
    if result.returncode != 0:
        raise BracketlapseError(
            f"Setup command failed with exit code {result.returncode}: {' '.join(command)}"
        )


def resolve_simple_deflicker_output(value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.parent != Path(".") or candidate.is_absolute():
        return candidate.resolve()
    return simple_deflicker_bin_dir() / executable_name(value)


def simple_deflicker_source_dir() -> Path:
    return tool_cache_dir() / "src" / "simple-deflicker"


def simple_deflicker_bin_dir() -> Path:
    return tool_cache_dir() / "bin"


def tool_cache_dir() -> Path:
    return Path.home() / ".cache" / "bracketlapse" / "tools"


def executable_name(name: str) -> str:
    if os.name == "nt" and not name.lower().endswith(".exe"):
        return f"{name}.exe"
    return name
