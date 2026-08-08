from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from helpers import create_input_frames, create_mock_tools, run_bracketlapse
from helpers import write_executable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import bracketlapse.standby


def test_in_place_standby_fuses_growth_before_finalization(
    tmp_path: Path, monkeypatch
) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    clock = [0.0]
    counts = [0, 3, 3, 3, 3, 3]
    calls = []

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    def count(_directory: Path) -> int:
        return counts.pop(0) if counts else 3

    def fuse(args):
        calls.append(argparse.Namespace(**vars(args)))
        return SimpleNamespace(available_groups=1)

    monkeypatch.setattr(bracketlapse.standby.time, "sleep", sleep)
    monkeypatch.setattr(bracketlapse.standby.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(bracketlapse.standby, "count_directory_entries", count)
    monkeypatch.setattr(bracketlapse.standby, "fuse_brackets", fuse)

    bracketlapse.standby.run_standby(
        argparse.Namespace(no_deflick=False, no_video=False),
        bracketlapse.standby.StandbyConfig(work_dir, work_dir, 1.0, False),
    )

    assert len(calls) == 2
    assert calls[0].allow_empty is True
    assert calls[0].no_deflick is True
    assert calls[0].no_video is True
    assert calls[0].group_offset == 0
    assert not hasattr(calls[1], "allow_empty")
    assert calls[1].no_video is False


def test_fuse_pipeline_deflickers_before_video(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    work_dir = tmp_path / "work"
    create_mock_tools(bin_dir)
    create_input_frames(work_dir, 6)

    result = run_bracketlapse(
        [str(work_dir), "--no-merge-subdirs", "--overwrite", "--fps", "24"],
        bin_dir,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert sorted(path.name for path in (work_dir / "hdr_enfuse").glob("*.jpg")) == [
        "hdrimg_260620_08-09_00001.jpg",
        "hdrimg_260620_08-09_00002.jpg",
    ]
    assert sorted(path.name for path in (work_dir / "hdr_deflick").glob("*.jpg")) == [
        "hdrimg_260620_08-09_00001.jpg",
        "hdrimg_260620_08-09_00002.jpg",
    ]
    assert (work_dir / "hdr_video" / "timelapse_260620_08-09.mp4").read_text(
        encoding="utf-8"
    ) == "video\n"
    assert "mock enfuse debug" not in result.stdout
    event_lines = [
        line.removeprefix("BRACKETLAPSE_EVENT ")
        for line in result.stdout.splitlines()
        if line.startswith("BRACKETLAPSE_EVENT ")
    ]
    assert len(event_lines) == 2
    assert [json.loads(line)["frame_number"] for line in event_lines] == [1, 2]


def test_debug_creates_hdr_video_and_prints_debug_logs(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    work_dir = tmp_path / "work"
    create_mock_tools(bin_dir)
    create_input_frames(work_dir, 3)

    result = run_bracketlapse(
        [str(work_dir), "--no-merge-subdirs", "--overwrite", "--debug"],
        bin_dir,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "mock enfuse debug" in result.stdout
    assert "mock deflicker debug" in result.stdout
    assert (work_dir / "hdr_video" / "timelapse_260620_08-09_hdr_debug.mp4").exists()
    assert (work_dir / "hdr_video" / "timelapse_260620_08-09.mp4").exists()


def test_no_video_still_deflickers_by_default(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    work_dir = tmp_path / "work"
    create_mock_tools(bin_dir)
    create_input_frames(work_dir, 3)

    result = run_bracketlapse(
        [str(work_dir), "--no-merge-subdirs", "--no-video"], bin_dir
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert (work_dir / "hdr_enfuse" / "hdrimg_260620_08-09_00001.jpg").exists()
    assert (work_dir / "hdr_deflick" / "hdrimg_260620_08-09_00001.jpg").exists()
    assert not (work_dir / "hdr_video").exists()


def test_no_deflick_uses_fused_frames_for_video(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    work_dir = tmp_path / "work"
    create_mock_tools(bin_dir, include_deflicker=False)
    create_input_frames(work_dir, 3)

    result = run_bracketlapse(
        [str(work_dir), "--no-merge-subdirs", "--no-deflick", "--overwrite"],
        bin_dir,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert (work_dir / "hdr_enfuse" / "hdrimg_260620_08-09_00001.jpg").exists()
    assert not (work_dir / "hdr_deflick").exists()
    assert (work_dir / "hdr_video" / "timelapse_260620_08-09.mp4").exists()


def test_video_command_only_requires_ffmpeg(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    frames_dir = tmp_path / "frames"
    create_mock_tools(bin_dir, include_deflicker=False)
    (bin_dir / "enfuse").unlink()
    create_input_frames(frames_dir, 2)

    result = run_bracketlapse(
        ["video", str(frames_dir), "--output", "out.mp4", "--overwrite"],
        bin_dir,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert (frames_dir / "out.mp4").read_text(encoding="utf-8") == "video\n"


def test_fuse_failure_does_not_create_output_frame(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    work_dir = tmp_path / "work"
    bin_dir.mkdir()
    write_executable(
        bin_dir / "enfuse",
        """#!/bin/sh
printf "enfuse failed\\n" >&2
exit 1
""",
    )
    create_input_frames(work_dir, 3)

    result = run_bracketlapse(
        [str(work_dir), "--no-merge-subdirs", "--no-video"], bin_dir
    )

    assert result.returncode == 1
    assert "enfuse" in result.stderr
    assert not (work_dir / "hdr_enfuse" / "hdrimg_260620_08-09_00001.jpg").exists()
