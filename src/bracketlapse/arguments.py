from __future__ import annotations

import argparse

from .argument_groups import (
    add_common_arguments,
    add_fuse_arguments,
    add_video_arguments,
)


def build_parser(argv: list[str]) -> argparse.ArgumentParser:
    if argv[:1] == ["video"]:
        parser = argparse.ArgumentParser(
            prog="bracketlapse video",
            description="Create a video from JPG frames with ffmpeg.",
        )
        add_video_arguments(parser)
        return parser
    if argv[:1] == ["update"]:
        parser = argparse.ArgumentParser(
            prog="bracketlapse update",
            description="Update runtime dependencies. Provide names to update only selected ones.",
        )
        add_common_arguments(parser)
        parser.add_argument(
            "dependencies",
            nargs="*",
            help=(
                "Optional dependency names to update, such as simple-deflicker, "
                "ffmpeg, git, go, or enfuse."
            ),
        )
        return parser

    parser = argparse.ArgumentParser(
        prog="bracketlapse",
        description=(
            "Fuse three-shot bracketed JPG groups. Use 'bracketlapse video' "
            "to create a timelapse video. Use 'bracketlapse update' to refresh "
            "runtime dependencies."
        ),
    )
    add_fuse_arguments(parser)
    return parser
