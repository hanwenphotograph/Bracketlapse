from __future__ import annotations

from pathlib import Path
import sys

from helpers import create_input_frames, create_mock_tools, run_bracketlapse
from helpers import write_executable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import bracketlapse.cli
import bracketlapse.environment


def test_no_arguments_prints_main_help(tmp_path: Path) -> None:
    result = run_bracketlapse([], tmp_path / "bin")

    assert result.returncode == 0
    assert "usage: bracketlapse" in result.stdout
    assert "--deflick-output" in result.stdout
    assert "--debug" in result.stdout
    assert "Checking runtime environment" not in result.stdout


def test_video_without_arguments_prints_video_help(tmp_path: Path) -> None:
    result = run_bracketlapse(["video"], tmp_path / "bin")

    assert result.returncode == 0
    assert "usage: bracketlapse video" in result.stdout
    assert "--output" in result.stdout
    assert "--debug" in result.stdout
    assert "Checking runtime environment" not in result.stdout


def test_standby_with_only_standby_arguments_does_not_print_help(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    bin_dir = tmp_path / "bin"
    watch_dir = tmp_path / "watch"
    target_dir = tmp_path / "target"
    create_mock_tools(bin_dir)
    watch_dir.mkdir()
    target_dir.mkdir()
    entered_standby = False

    def fake_run_standby(args, standby_config) -> None:
        nonlocal entered_standby
        entered_standby = True
        assert args.directory is None
        assert standby_config.watch_directory == watch_dir
        assert standby_config.target_directory == target_dir
        assert standby_config.quiet_seconds == 60

    monkeypatch.setattr(bracketlapse.cli, "run_standby", fake_run_standby)

    result = bracketlapse.cli.main(
        ["--standby", str(watch_dir), str(target_dir), "60"]
    )
    output = capsys.readouterr()

    assert result == 0
    assert entered_standby
    assert "usage: bracketlapse" not in output.out


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
    assert (work_dir / "hdr_video" / "timelapse_260620_08-09.mp4").read_text(encoding="utf-8") == "video\n"
    assert "mock enfuse debug" not in result.stdout


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

    result = run_bracketlapse([str(work_dir), "--no-merge-subdirs", "--no-video"], bin_dir)

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


def test_update_command_refreshes_dependencies(tmp_path: Path, monkeypatch) -> None:
    created = []
    updated_tools = []
    cloned = []

    monkeypatch.setattr(bracketlapse.environment, "update_system_tool", lambda name: updated_tools.append(name))
    monkeypatch.setattr(bracketlapse.environment, "ensure_system_tool", lambda name: name)
    monkeypatch.setattr(bracketlapse.environment, "clone_or_update_simple_deflicker", lambda git: cloned.append(git))

    def fake_build(go, output):
        created.append((go, output))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("simple-deflicker\n", encoding="utf-8")

    monkeypatch.setattr(bracketlapse.environment, "build_simple_deflicker", fake_build)
    monkeypatch.setattr(bracketlapse.environment, "simple_deflicker_bin_dir", lambda: tmp_path / ".cache" / "bracketlapse" / "tools" / "bin")
    monkeypatch.setattr(bracketlapse.environment, "tool_cache_dir", lambda: tmp_path / ".cache" / "bracketlapse" / "tools")

    result = bracketlapse.cli.main(["update"])

    assert result == 0
    assert updated_tools == ["enfuse", "ffmpeg", "git", "go"]
    assert cloned == ["git"]
    assert created
    assert (tmp_path / ".cache" / "bracketlapse" / "tools" / "bin" / "simple-deflicker").exists()


def test_update_command_can_target_simple_deflicker(tmp_path: Path, monkeypatch) -> None:
    updated_tools = []
    rebuilt = []

    monkeypatch.setattr(bracketlapse.environment, "update_system_tool", lambda name: updated_tools.append(name))
    monkeypatch.setattr(bracketlapse.environment, "ensure_system_tool", lambda name: name)

    def fake_update_simple_deflicker():
        rebuilt.append(True)
        return tmp_path / ".cache" / "bracketlapse" / "tools" / "bin" / "simple-deflicker"

    monkeypatch.setattr(bracketlapse.environment, "update_simple_deflicker", fake_update_simple_deflicker)

    result = bracketlapse.cli.main(["update", "simple-deflicker"])

    assert result == 0
    assert updated_tools == []
    assert rebuilt == [True]


def test_update_command_rejects_unknown_dependency() -> None:
    result = bracketlapse.cli.main(["update", "unknown-tool"])

    assert result == 1


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

    result = run_bracketlapse([str(work_dir), "--no-merge-subdirs", "--no-video"], bin_dir)

    assert result.returncode == 1
    assert "enfuse" in result.stderr
    assert not (work_dir / "hdr_enfuse" / "hdrimg_260620_08-09_00001.jpg").exists()
