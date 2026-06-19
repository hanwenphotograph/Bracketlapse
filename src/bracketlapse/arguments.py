from __future__ import annotations

import argparse
from pathlib import Path


def build_parser(argv: list[str]) -> argparse.ArgumentParser:
    if argv[:1] == ["video"]:
        parser = argparse.ArgumentParser(
            prog="bracketlapse video",
            description="Create a video from JPG frames with ffmpeg.",
        )
        add_video_arguments(parser)
        return parser

    parser = argparse.ArgumentParser(
        prog="bracketlapse",
        description=(
            "Fuse three-shot bracketed JPG groups. Use 'bracketlapse video' "
            "to create a timelapse video."
        ),
    )
    add_fuse_arguments(parser)
    return parser


def add_fuse_arguments(parser: argparse.ArgumentParser) -> None:
    add_common_arguments(parser)
    parser.add_argument(
        "--standby",
        action="store_true",
        help="Enter standby mode. Provide WATCH_DIR TARGET_DIR QUIET_SECONDS [loop].",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        help="Directory containing bracketed JPG files. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("hdr_enfuse"),
        help="Fused frame output directory. Default: hdr_enfuse",
    )
    parser.add_argument(
        "--deflick-output",
        type=Path,
        default=Path("hdr_deflick"),
        help="Deflickered frame output directory. Default: hdr_deflick",
    )
    parser.add_argument("--pattern", default="*.jp*g", help="Input glob pattern. Default: *.jp*g")
    add_merge_arguments(parser)
    add_fusion_arguments(parser)
    add_video_encoding_arguments(parser, automatic=True)
    add_deflick_arguments(parser)


def add_merge_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--merge-subdirs", action="store_true", help="Merge image subdirectories.")
    parser.add_argument(
        "--merge-dirs",
        nargs="+",
        type=Path,
        help="Subdirectories to merge. Relative paths are resolved inside the processing directory.",
    )
    parser.add_argument(
        "--no-merge-subdirs",
        action="store_true",
        help="Do not ask about merging subdirectories; process only the chosen directory.",
    )


def add_fusion_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--group-size", type=int, default=3, help="Bracket group size. Default: 3")
    parser.add_argument(
        "--sort",
        choices=("name", "time"),
        default="name",
        help="Sort input files by filename or modified time. Default: name",
    )
    parser.add_argument("--align", action="store_true", help="Align groups before fusing.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    parser.add_argument("--start-number", type=int, default=1, help="Starting output number.")
    parser.add_argument("--limit", type=int, help="Process at most this many groups.")
    parser.add_argument("--ext", choices=("jpg", "tif"), default="jpg", help="HDR extension.")
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Skip automatic video creation after fusion and deflicker.",
    )
    parser.add_argument(
        "--no-deflick",
        action="store_true",
        help="Skip simple-deflicker processing and use fused frames directly.",
    )


def add_deflick_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--deflick-bin",
        default="simple-deflicker",
        help="simple-deflicker executable name or path. Default: simple-deflicker",
    )
    parser.add_argument(
        "--deflick-rolling-average",
        type=int,
        default=15,
        help="simple-deflicker rolling average. Default: 15",
    )
    parser.add_argument(
        "--deflick-jpeg-compression",
        type=int,
        default=95,
        help="simple-deflicker JPEG quality. Default: 95",
    )
    parser.add_argument(
        "--deflick-threads",
        type=int,
        help="simple-deflicker worker thread count. Default: detected by simple-deflicker.",
    )


def add_video_arguments(parser: argparse.ArgumentParser) -> None:
    add_common_arguments(parser)
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        help="Directory containing JPG frames. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output_30fps.mp4"),
        help="Output video path. Relative paths are resolved inside the processing directory.",
    )
    parser.add_argument("--pattern", default="*.jp*g", help="Input glob pattern. Default: *.jp*g")
    parser.add_argument(
        "--sort",
        choices=("name", "time"),
        default="name",
        help="Sort input files by filename or modified time. Default: name",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the output video.")
    add_video_encoding_arguments(parser, automatic=False)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug logs and create extra debug outputs when available.",
    )


def add_video_encoding_arguments(parser: argparse.ArgumentParser, *, automatic: bool) -> None:
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help=f"Frames per second{' for the automatic video' if automatic else ''}. Default: 30",
    )
    if automatic:
        parser.add_argument(
            "--video-output",
            type=Path,
            default=Path("hdr_video") / "timelapse.mp4",
            help="Automatic video output path. Default: date/time-based name inside hdr_video",
        )
    parser.add_argument("--crf", type=int, default=18, help="x265 CRF quality. Default: 18")
    parser.add_argument("--preset", default="slow", help="x265 preset. Default: slow")
