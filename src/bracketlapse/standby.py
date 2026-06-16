from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shutil
import time

from .common import BracketlapseError, format_fps, log, parse_float
from .common import resolve_processing_directory
from .fusion import fuse_brackets


@dataclass
class StandbyConfig:
    watch_directory: Path | None
    target_directory: Path | None
    quiet_seconds: float | None
    loop: bool


def extract_standby_config(argv: list[str]) -> tuple[StandbyConfig | None, list[str]]:
    if "--standby" not in argv:
        return None, argv

    standby_index = argv.index("--standby")
    consumed = {standby_index}
    values: list[str] = []
    index = standby_index + 1

    while index < len(argv) and len(values) < 3:
        token = argv[index]
        if token.startswith("-"):
            break
        values.append(token)
        consumed.add(index)
        index += 1

    loop = False
    if index < len(argv) and argv[index] == "loop":
        loop = True
        consumed.add(index)

    standby_config = StandbyConfig(
        watch_directory=Path(values[0]) if len(values) > 0 else None,
        target_directory=Path(values[1]) if len(values) > 1 else None,
        quiet_seconds=parse_float(values[2], "quiet seconds") if len(values) > 2 else None,
        loop=loop,
    )
    remaining = [token for index, token in enumerate(argv) if index not in consumed]
    return standby_config, remaining


def run_standby(args: argparse.Namespace, standby_config: StandbyConfig) -> None:
    watch_directory = resolve_standby_watch_directory(standby_config.watch_directory)
    target_directory = resolve_standby_target_directory(standby_config.target_directory)
    quiet_seconds = resolve_standby_quiet_seconds(standby_config.quiet_seconds)
    watch_resolved = watch_directory.resolve()
    target_resolved = target_directory.resolve()
    if target_resolved != watch_resolved and target_resolved.is_relative_to(watch_resolved):
        raise BracketlapseError("Target directory cannot be nested inside the watch directory.")

    log.info(f"Standby watch directory: {watch_directory}")
    log.info(f"Standby target directory: {target_directory}")
    log.info(f"Standby quiet seconds: {format_fps(quiet_seconds)}")
    log.info(f"Standby loop: {'yes' if standby_config.loop else 'no'}")

    baseline = count_directory_entries(watch_directory)
    armed = False
    log.info(
        f"Standby initial recursive count: {baseline}. "
        "Waiting for growth before listening."
    )

    while True:
        time.sleep(quiet_seconds)
        current_count = count_directory_entries(watch_directory)
        log.info(format_standby_scan_message(watch_directory, current_count, baseline, armed))

        if armed and current_count <= baseline:
            standby_args = argparse.Namespace(**vars(args))
            standby_args.merge_subdirs = True
            standby_args.merge_dirs = None
            standby_args.no_merge_subdirs = False
            standby_args.no_video = False

            if target_resolved == watch_resolved:
                standby_args.directory = target_directory
                log.info("Standby processing in place (watch == target)")
            else:
                batch_directory = create_standby_batch_directory(target_directory)
                move_directory_contents(watch_directory, batch_directory)
                standby_args.directory = batch_directory
                log.info(f"Standby batch directory: {batch_directory}")

            fuse_brackets(standby_args)

            if not standby_config.loop:
                return

            baseline = count_directory_entries(watch_directory)
            armed = False
            continue

        if current_count > baseline:
            if not armed:
                log.info(
                    f"Standby detected growth: {baseline} -> {current_count}. "
                    "Listening for quiet interval."
                )
            baseline = current_count
            armed = True
        elif not armed:
            continue


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
