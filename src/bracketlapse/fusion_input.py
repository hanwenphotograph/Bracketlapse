from __future__ import annotations

import argparse
from pathlib import Path

from .common import BracketlapseError, format_paths, log
from .common import resolve_inside, resolve_processing_directory
from .grouping import detect_sequence_gap_ranges, format_sequence_gap_ranges
from .images import find_images_in_directories, find_merge_candidates


def prepare_fusion_files(
    source_dirs: list[Path],
    args: argparse.Namespace,
    *,
    allow_empty: bool = False,
) -> list[Path]:
    files = find_images_in_directories(source_dirs, args.pattern, args.sort)
    if not files:
        if allow_empty:
            return []
        raise BracketlapseError(
            f"No image files matched {args.pattern!r} in {format_paths(source_dirs)}"
        )
    if args.group_size < 2:
        raise BracketlapseError("--group-size must be at least 2")
    if args.fps <= 0:
        raise BracketlapseError("--fps must be greater than zero")

    remainder = len(files) % args.group_size
    if remainder:
        dropped_files = files[-remainder:]
        files = files[:-remainder]
        if not allow_empty:
            log.warn(
                f"found {len(files) + remainder} files, which is not divisible by "
                f"group size {args.group_size}; dropping the last {remainder} file(s): "
                f"{format_paths(dropped_files)}"
            )
    if not files:
        if allow_empty:
            return []
        raise BracketlapseError(
            f"No complete groups can be formed with group size {args.group_size}."
        )

    sequence_gap_ranges = detect_sequence_gap_ranges(files)
    if sequence_gap_ranges:
        log.warn(
            "sequence gaps detected before HDR fusion; "
            f"incomplete groups will be skipped: {format_sequence_gap_ranges(sequence_gap_ranges)}"
        )
    return files


def resolve_fuse_working_directory(args: argparse.Namespace) -> Path:
    if args.directory is not None:
        return resolve_processing_directory(args.directory)

    current_directory = Path.cwd().resolve()
    if args.merge_subdirs or args.merge_dirs or args.no_merge_subdirs:
        return current_directory

    output_dir = resolve_inside(current_directory, args.output)
    deflick_output_dir = resolve_inside(current_directory, args.deflick_output)
    video_output = resolve_inside(current_directory, args.video_output)
    candidates = find_merge_candidates(
        directory=current_directory,
        excluded_paths=[output_dir, deflick_output_dir, video_output.parent],
        pattern=args.pattern,
        sort_mode=args.sort,
    )
    if candidates:
        return current_directory
    return resolve_processing_directory(None)


def is_current_directory_argument(value: Path) -> bool:
    return value.expanduser().resolve() == Path.cwd().resolve()
