from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bracketlapse.common import BracketlapseError, log
from bracketlapse.video import render_video_file


class _FakeProcess:
    def __init__(self, progress: str, return_code: int) -> None:
        self.stdout = io.StringIO(progress)
        self._return_code = return_code

    def wait(self) -> int:
        return self._return_code


def _fake_popen(progress: str, return_code: int, errors: str):
    def popen(_command, **kwargs):
        kwargs["stderr"].write(errors)
        kwargs["stderr"].flush()
        return _FakeProcess(progress, return_code)

    return popen


def _render(tmp_path: Path, *, report_progress: bool = True) -> None:
    render_video_file(
        ffmpeg="ffmpeg",
        concat_file=tmp_path / "frames.ffconcat",
        output=tmp_path / "video.mp4",
        fps=24.0,
        crf=20,
        preset="medium",
        overwrite=True,
        total_frames=3,
        report_progress=report_progress,
    )


def _run_render(
    tmp_path: Path,
    *,
    progress: str,
    return_code: int = 0,
    errors: str = "",
    report_progress: bool = True,
) -> tuple[str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()

    with patch(
        "bracketlapse.ffmpeg_progress.subprocess.Popen",
        side_effect=_fake_popen(progress, return_code, errors),
    ):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            _render(tmp_path, report_progress=report_progress)
    return stdout.getvalue(), stderr.getvalue()


def test_video_events_follow_progress_blocks_and_clamp_frames(tmp_path: Path) -> None:
    output, _errors = _run_render(
        tmp_path,
        progress=(
            "frame=1\nprogress=continue\n"
            "frame=-2\nprogress=continue\n"
            "frame=99\nprogress=end\n"
        ),
    )

    event_lines = [
        line for line in output.splitlines() if line.startswith("BRACKETLAPSE_EVENT ")
    ]
    import json

    events = [
        json.loads(line.removeprefix("BRACKETLAPSE_EVENT ")) for line in event_lines
    ]
    assert [event["event"] for event in events] == [
        "video_started",
        "video_progress",
        "video_progress",
        "video_progress",
        "video_completed",
    ]
    assert [event["completed"] for event in events] == [0, 1, 0, 3, 3]
    assert all(event["total"] == 3 for event in events)
    assert all(
        event["path"] == str((tmp_path / "video.mp4").resolve()) for event in events
    )
    assert "Creating video:" in output


def test_failed_ffmpeg_has_no_completed_event_and_keeps_error_output(
    tmp_path: Path,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch(
        "bracketlapse.ffmpeg_progress.subprocess.Popen",
        side_effect=_fake_popen(
            "frame=2\nprogress=end\n",
            9,
            "encoding failed\n",
        ),
    ):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            with pytest.raises(BracketlapseError, match="exit code 9"):
                _render(tmp_path)

    assert '"event":"video_completed"' not in stdout.getvalue()
    assert "encoding failed" in stderr.getvalue()


def test_debug_video_does_not_emit_video_events(tmp_path: Path) -> None:
    log.set_debug(True)
    try:
        output, _errors = _run_render(
            tmp_path,
            progress="frame=3\nprogress=end\n",
            errors="ffmpeg diagnostic\n",
            report_progress=False,
        )
    finally:
        log.set_debug(False)

    assert "BRACKETLAPSE_EVENT " not in output
    assert "ffmpeg diagnostic" in output
