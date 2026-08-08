from __future__ import annotations

import json
from pathlib import Path


EVENT_PREFIX = "BRACKETLAPSE_EVENT "


def emit_hdr_ready(path: Path, frame_number: int) -> None:
    payload = {
        "event": "hdr_ready",
        "frame_number": frame_number,
        "path": str(path.resolve()),
    }
    print(
        EVENT_PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        flush=True,
    )
