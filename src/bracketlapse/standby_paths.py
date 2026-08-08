from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil

from .common import BracketlapseError, log, parse_float, resolve_processing_directory


def resolve_standby_watch_directory(value: Path | None) -> Path:
    return resolve_processing_directory(value)


def resolve_standby_target_directory(value: Path | None) -> Path:
    if value is None:
        raw = input("Target directory: ").strip().strip('"')
        if not raw:
            raise BracketlapseError("No target directory was provided.")
        value = Path(raw)

    directory = value.expanduser().resolve()
    if directory.exists() and not directory.is_dir():
        raise BracketlapseError(f"Target path is not a directory: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def resolve_standby_quiet_seconds(value: float | None) -> float:
    if value is None:
        raw = input("Quiet seconds: ").strip()
        if not raw:
            raise BracketlapseError("No quiet seconds were provided.")
        value = parse_float(raw, "quiet seconds")
    if value <= 0:
        raise BracketlapseError("Quiet seconds must be greater than zero.")
    return value


def count_directory_entries(directory: Path) -> int:
    total = 0
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                total += 1
                if entry.is_dir(follow_symlinks=False):
                    total += count_directory_entries(Path(entry.path))
    except OSError as exc:
        log.warn(f"skipping unreadable directory {directory}: {exc}")
    return total


def create_standby_batch_directory(target_directory: Path) -> Path:
    date_prefix = datetime.now().strftime("%Y%m%d")
    candidate = target_directory / date_prefix
    suffix = 1
    while candidate.exists():
        candidate = target_directory / f"{date_prefix}-{suffix}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def move_directory_contents(source: Path, destination: Path) -> None:
    for entry in list(source.iterdir()):
        if entry.resolve() == destination.resolve():
            continue
        shutil.move(str(entry), str(destination / entry.name))


def format_standby_scan_message(
    watch_directory: Path,
    current_count: int,
    baseline: int,
    armed: bool,
) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state = "监听中" if armed else "待机中"
    if not armed and current_count > baseline:
        result = (
            f"检测到增长，当前递归计数 {current_count}，"
            f"较启动基线增加 {current_count - baseline}，即将开始监听"
        )
    elif not armed:
        result = f"等待新文件，当前递归计数 {current_count}，基线 {baseline}"
    elif current_count > baseline:
        result = f"检测到新增，当前递归计数 {current_count}，较上次增加 {current_count - baseline}"
    elif current_count == baseline:
        result = f"未增加，当前递归计数 {current_count}，与上次相同"
    else:
        result = f"未增加，当前递归计数 {current_count}，较上次减少 {baseline - current_count}"
    return f"[{timestamp}] {state}：{watch_directory}，{result}"
