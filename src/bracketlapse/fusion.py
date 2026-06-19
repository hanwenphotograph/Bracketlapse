from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

from .common import (
    BracketlapseError,
    format_paths,
    log,
    require_tool,
    resolve_inside,
    resolve_processing_directory,
    run_command,
)
from .deflicker import deflick_frames, ensure_deflick_supported_extension
from .enfuse import align_group, build_enfuse_command
from .grouping import build_fusion_groups, detect_sequence_gap_ranges
from .grouping import format_sequence_gap_ranges
from .images import find_images, find_images_in_directories, find_merge_candidates
from .images import resolve_source_directories
from .naming import build_frame_name, build_video_name
from .video import build_video_from_directory


def fuse_brackets(args: argparse.Namespace) -> None:
    directory = resolve_fuse_working_directory(args)
    output_dir = resolve_inside(directory, args.output)
    deflick_output_dir = resolve_inside(directory, args.deflick_output)

    if not args.no_deflick:
        ensure_deflick_supported_extension(args.ext)

    enfuse = require_tool("enfuse")
    align_image_stack = require_tool("align_image_stack") if args.align else None
    video_output = resolve_inside(directory, args.video_output)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_dirs = resolve_source_directories(
        directory=directory,
        output_dir=output_dir,
        deflick_output_dir=deflick_output_dir,
        video_output=video_output,
        pattern=args.pattern,
        sort_mode=args.sort,
        merge_subdirs=args.merge_subdirs,
        merge_dirs=args.merge_dirs,
        no_merge_subdirs=(
            args.no_merge_subdirs
            or (
                args.directory is not None
                and not is_current_directory_argument(args.directory)
                and not args.merge_subdirs
                and not args.merge_dirs
            )
        ),
    )
    files = prepare_fusion_files(source_dirs, args)
    groups = build_fusion_groups(files, args.group_size)
    if not groups:
        raise BracketlapseError("No complete HDR groups can be formed after sequence gap detection.")
    if args.limit is not None:
        groups = groups[: args.limit]

    log.info(f"Working directory: {directory}")
    log.info(f"Input directories: {format_paths(source_dirs)}")
    log.info(f"Found {len(files)} JPG files, {len(groups)} group(s) to process.")
    log.info(f"Output directory: {output_dir}")

    for offset, group in enumerate(groups):
        frame_number = args.start_number + offset
        output = output_dir / build_frame_name(frame_number, args.ext)
        if output.exists() and not args.overwrite:
            log.info(f"[{offset + 1}/{len(groups)}] Skip existing {output.name}")
            continue

        log.info(f"[{offset + 1}/{len(groups)}] Fusing {output.name}")
        if args.align:
            assert align_image_stack is not None
            with tempfile.TemporaryDirectory(prefix="bracketlapse_align_") as tmp:
                aligned = align_group(align_image_stack, group, Path(tmp), frame_number)
                run_command(build_enfuse_command(enfuse, output, aligned))
        else:
            run_command(build_enfuse_command(enfuse, output, group))

    video_source_dir = output_dir
    video_pattern = f"*.{args.ext}"
    default_video_output = resolve_inside(directory, Path("hdr_video") / "timelapse.mp4")
    if video_output == default_video_output:
        video_output = resolve_inside(directory, Path("hdr_video") / build_video_name())
    if args.debug and not args.no_deflick:
        log.info("Creating HDR debug video before deflicker.")
        build_video_from_directory(
            directory=output_dir,
            output=make_debug_video_output(video_output),
            fps=args.fps,
            pattern=video_pattern,
            sort_mode="name",
            crf=args.crf,
            preset=args.preset,
            overwrite=args.overwrite,
            skip_existing=True,
        )

    if not args.no_deflick:
        log.info("Deflickering fused frames.")
        deflick_frames(
            source_dir=output_dir,
            output_dir=deflick_output_dir,
            executable_name=args.deflick_bin,
            overwrite=args.overwrite,
            rolling_average=args.deflick_rolling_average,
            jpeg_compression=args.deflick_jpeg_compression,
            threads=args.deflick_threads,
        )
        video_source_dir = deflick_output_dir
        video_pattern = "*.jp*g"

    if not args.no_video:
        log.info(f"Creating video from {video_source_dir.name} frames.")
        build_video_from_directory(
            directory=video_source_dir,
            output=video_output,
            fps=args.fps,
            pattern=video_pattern,
            sort_mode="name",
            crf=args.crf,
            preset=args.preset,
            overwrite=args.overwrite,
            skip_existing=True,
        )

    log.info("Done.")


def prepare_fusion_files(source_dirs: list[Path], args: argparse.Namespace) -> list[Path]:
    files = find_images_in_directories(source_dirs, args.pattern, args.sort)
    if not files:
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
        log.warn(
            f"found {len(files) + remainder} files, which is not divisible by "
            f"group size {args.group_size}; dropping the last {remainder} file(s): "
            f"{format_paths(dropped_files)}"
        )
    if not files:
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


def make_debug_video_output(output: Path) -> Path:
    if output.suffix:
        return output.with_name(f"{output.stem}_hdr_debug{output.suffix}")
    return output.with_name(f"{output.name}_hdr_debug")
