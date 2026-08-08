from __future__ import annotations

import json
from pathlib import Path


EVENT_PREFIX = "BRACKETLAPSE_EVENT "


def emit_hdr_ready(path: Path, frame_number: int) -> None:
    _emit(
        {
            "event": "hdr_ready",
            "frame_number": frame_number,
            "path": str(path.resolve()),
        }
    )


def emit_video_started(path: Path, total: int) -> None:
    _emit_video_event("video_started", path, 0, total)


def emit_video_progress(path: Path, completed: int, total: int) -> None:
    _emit_video_event("video_progress", path, completed, total)


def emit_video_completed(path: Path, total: int) -> None:
    _emit_video_event("video_completed", path, total, total)


def _emit_video_event(
    event: str,
    path: Path,
    completed: int,
    total: int,
) -> None:
    _emit(
        {
            "event": event,
            "path": str(path.resolve()),
            "completed": completed,
            "total": total,
        }
    )


def _emit(payload: dict[str, object]) -> None:
    print(
        EVENT_PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        flush=True,
    )
