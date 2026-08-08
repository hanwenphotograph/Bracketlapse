from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

from .common import (
    BracketlapseError,
    format_fps,
    log,
    require_tool,
    resolve_inside,
    resolve_processing_directory,
)
from .events import emit_video_completed, emit_video_progress, emit_video_started
from .ffmpeg_progress import run_ffmpeg_with_progress
from .naming import build_video_name
from .images import find_images


def build_video(args: argparse.Namespace) -> None:
    directory = resolve_processing_directory(args.directory)
    output = resolve_inside(directory, args.output)
    if args.output == Path("timelapse.mp4"):
        output = resolve_inside(directory, Path(build_video_name()))
    build_video_from_directory(
        directory=directory,
        output=output,
        fps=args.fps,
        pattern=args.pattern,
        sort_mode=args.sort,
        crf=args.crf,
        preset=args.preset,
        overwrite=args.overwrite,
        skip_existing=False,
    )

    log.info("Done.")


def build_video_from_directory(
    directory: Path,
    output: Path,
    fps: float,
    pattern: str,
    sort_mode: str,
    crf: int,
    preset: str,
    overwrite: bool,
    skip_existing: bool,
    report_progress: bool = True,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists() and not overwrite:
        if skip_existing:
            log.info(f"Skip existing video: {output}")
            return
        raise BracketlapseError(
            f"Output already exists: {output}. Use --overwrite to replace it."
        )
    if fps <= 0:
        raise BracketlapseError("--fps must be greater than zero")

    ffmpeg = require_tool("ffmpeg")
    files = find_images(directory, pattern, sort_mode)
    if not files:
        raise BracketlapseError(f"No JPG files matched {pattern!r} in {directory}")

    log.info(f"Input directory: {directory}")
    log.info(f"Found {len(files)} JPG frames.")
    log.info(f"Output video: {output}")

    with tempfile.TemporaryDirectory(prefix="bracketlapse_ffmpeg_") as tmp:
        concat_file = Path(tmp) / "frames.ffconcat"
        write_ffconcat(concat_file, files, 1.0 / fps)
        render_video_file(
            ffmpeg=ffmpeg,
            concat_file=concat_file,
            output=output,
            fps=fps,
            crf=crf,
            preset=preset,
            overwrite=overwrite,
            total_frames=len(files),
            report_progress=report_progress,
        )


def render_video_file(
    ffmpeg: str,
    concat_file: Path,
    output: Path,
    fps: float,
    crf: int,
    preset: str,
    overwrite: bool,
    total_frames: int,
    report_progress: bool = True,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    log.info(f"Creating video: {output}")
    command = [
        ffmpeg,
        "-y" if overwrite else "-n",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-progress",
        "pipe:1",
        "-nostats",
        "-loglevel",
        "error",
        "-r",
        format_fps(fps),
        "-c:v",
        "libx265",
        "-crf",
        str(crf),
        "-preset",
        preset,
        "-tag:v",
        "hvc1",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]
    if report_progress:
        emit_video_started(output, total_frames)

    def report_frame(completed: int) -> None:
        emit_video_progress(output, completed, total_frames)

    run_ffmpeg_with_progress(
        command,
        total_frames,
        report_frame if report_progress else None,
    )
    if report_progress:
        emit_video_completed(output, total_frames)


def write_ffconcat(path: Path, files: list[Path], frame_duration: float) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("ffconcat version 1.0\n")
        for file in files:
            handle.write(f"file {quote_ffconcat_path(file)}\n")
            handle.write(f"duration {frame_duration:.16g}\n")
        handle.write(f"file {quote_ffconcat_path(files[-1])}\n")


def quote_ffconcat_path(path: Path) -> str:
    text = path.resolve().as_posix()
    return "'" + text.replace("'", r"'\''") + "'"
