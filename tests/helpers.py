from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_bracketlapse(args: list[str], bin_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    env.setdefault("BRACKLAPSE_RUN_DATE", "2026-06-20")
    env.setdefault("BRACKLAPSE_RUN_START_AT", "08:00")
    env.setdefault("BRACKLAPSE_RUN_END_AT", "09:00")
    return subprocess.run(
        [sys.executable, "-m", "bracketlapse.cli", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def create_mock_tools(bin_dir: Path, *, include_deflicker: bool = True) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    write_executable(
        bin_dir / "enfuse",
        """#!/bin/sh
out=
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then
    shift
    out="$1"
  fi
  shift
done
mkdir -p "$(dirname "$out")"
printf "mock enfuse debug\\n"
printf "fused\\n" > "$out"
""",
    )
    write_executable(
        bin_dir / "ffmpeg",
        """#!/bin/sh
for last do true; done
mkdir -p "$(dirname "$last")"
printf "mock ffmpeg debug\\n"
printf "video\\n" > "$last"
""",
    )
    if include_deflicker:
        write_executable(
            bin_dir / "simple-deflicker",
            """#!/bin/sh
src=
dst=
while [ "$#" -gt 0 ]; do
  case "$1" in
    -source) shift; src="$1" ;;
    -destination) shift; dst="$1" ;;
  esac
  shift
done
mkdir -p "$dst"
printf "mock deflicker debug\\n"
cp "$src"/*.jpg "$dst"/
""",
        )


def create_input_frames(directory: Path, count: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for number in range(1, count + 1):
        (directory / f"{number:04d}.jpg").write_text(f"input {number}\n", encoding="utf-8")
