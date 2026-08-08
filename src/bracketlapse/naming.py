from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .common import BracketlapseError


@dataclass(frozen=True)
class RunNamingContext:
    date_token: str
    time_token: str


def build_run_naming_context() -> RunNamingContext:
    date_token = resolve_date_token()
    time_token = resolve_time_token()
    return RunNamingContext(date_token=date_token, time_token=time_token)


def build_frame_name(frame_number: int, ext: str) -> str:
    context = build_run_naming_context()
    return f"hdrimg_{context.date_token}_{context.time_token}_{frame_number:05d}.{ext}"


def build_video_name(ext: str = "mp4") -> str:
    context = build_run_naming_context()
    return f"timelapse_{context.date_token}_{context.time_token}.{ext}"


def resolve_date_token() -> str:
    raw = os.getenv("BRACKLAPSE_RUN_DATE")
    if not raw:
        raise BracketlapseError("BRACKLAPSE_RUN_DATE is required for run naming.")

    match = re.fullmatch(r"(?P<year>\d{4})[-_](?P<month>\d{2})[-_](?P<day>\d{2})", raw)
    if match is not None:
        return f"{match.group('year')[2:]}{match.group('month')}{match.group('day')}"

    match = re.fullmatch(r"\d{6}", raw)
    if match is not None:
        return raw

    raise BracketlapseError(f"Invalid BRACKLAPSE_RUN_DATE value: {raw!r}")


def resolve_time_token() -> str:
    raw_start = os.getenv("BRACKLAPSE_RUN_START_AT")
    raw_end = os.getenv("BRACKLAPSE_RUN_END_AT")
    if not raw_start or not raw_end:
        raise BracketlapseError("BRACKLAPSE_RUN_START_AT and BRACKLAPSE_RUN_END_AT are required.")

    start_hour = _extract_hour(raw_start)
    end_hour = _extract_hour(raw_end)
    if start_hour is None or end_hour is None:
        raise BracketlapseError(f"Invalid run time values: {raw_start!r}, {raw_end!r}")
    return f"{start_hour}-{end_hour}"


def _extract_hour(raw: str) -> str | None:
    match = re.fullmatch(r"(?P<hour>\d{2})(?::\d{2})?", raw)
    if match is None:
        return None
    return match.group("hour")
