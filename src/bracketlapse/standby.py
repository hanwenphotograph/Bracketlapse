from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import time

from .common import BracketlapseError, format_fps, log, parse_float
from .fusion import fuse_brackets
from .standby_paths import (
    count_directory_entries,
    create_standby_batch_directory,
    move_directory_contents,
    resolve_standby_quiet_seconds,
    resolve_standby_target_directory,
    resolve_standby_watch_directory,
)


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
        quiet_seconds=parse_float(values[2], "quiet seconds")
        if len(values) > 2
        else None,
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
    if target_resolved != watch_resolved and target_resolved.is_relative_to(
        watch_resolved
    ):
        raise BracketlapseError(
            "Target directory cannot be nested inside the watch directory."
        )

    log.info(f"Standby watch directory: {watch_directory}")
    log.info(f"Standby target directory: {target_directory}")
    log.info(f"Standby quiet seconds: {format_fps(quiet_seconds)}")
    log.info(f"Standby loop: {'yes' if standby_config.loop else 'no'}")

    baseline = count_directory_entries(watch_directory)
    armed = False
    last_change_at = time.monotonic()
    processed_groups = 0
    poll_seconds = min(0.25, quiet_seconds)
    log.info(
        f"Standby initial recursive count: {baseline}. "
        "Waiting for growth before listening."
    )

    while True:
        time.sleep(poll_seconds)
        current_count = count_directory_entries(watch_directory)
        grew = current_count > baseline
        if grew:
            if not armed:
                log.info(
                    f"Standby detected growth: {baseline} -> {current_count}. "
                    "Listening for quiet interval."
                )
            armed = True
            last_change_at = time.monotonic()
        if current_count != baseline:
            baseline = current_count
        elif not armed:
            continue

        if armed and grew and target_resolved == watch_resolved:
            processed_groups = _fuse_available_groups(
                args, target_directory, processed_groups
            )

        if time.monotonic() - last_change_at < quiet_seconds:
            continue

        _finalize_standby(args, watch_directory, target_directory)
        if not standby_config.loop:
            return
        baseline = count_directory_entries(watch_directory)
        last_change_at = time.monotonic()
        processed_groups = 0
        armed = False


def _standby_args(args: argparse.Namespace, directory: Path) -> argparse.Namespace:
    standby_args = argparse.Namespace(**vars(args))
    standby_args.directory = directory
    standby_args.merge_subdirs = True
    standby_args.merge_dirs = None
    standby_args.no_merge_subdirs = False
    return standby_args


def _fuse_available_groups(
    args: argparse.Namespace, directory: Path, processed_groups: int
) -> int:
    stream_args = _standby_args(args, directory)
    stream_args.no_deflick = True
    stream_args.no_video = True
    stream_args.allow_empty = True
    stream_args.group_offset = processed_groups
    result = fuse_brackets(stream_args)
    return result.available_groups


def _finalize_standby(
    args: argparse.Namespace, watch_directory: Path, target_directory: Path
) -> None:
    if target_directory.resolve() == watch_directory.resolve():
        batch_directory = target_directory
        log.info("Standby processing in place (watch == target)")
    else:
        batch_directory = create_standby_batch_directory(target_directory)
        move_directory_contents(watch_directory, batch_directory)
        log.info(f"Standby batch directory: {batch_directory}")
    standby_args = _standby_args(args, batch_directory)
    standby_args.no_video = False
    fuse_brackets(standby_args)
