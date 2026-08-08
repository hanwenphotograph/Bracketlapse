from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys

from helpers import create_mock_tools, run_bracketlapse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import bracketlapse.cli


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


def test_version_does_not_prepare_runtime(tmp_path: Path) -> None:
    result = run_bracketlapse(["--version"], tmp_path / "bin")

    assert result.returncode == 0
    assert result.stdout.strip() == "bracketlapse 0.4.0"
    assert "Checking runtime environment" not in result.stdout


def test_build_info_is_machine_readable(tmp_path: Path) -> None:
    result = run_bracketlapse(["--build-info"], tmp_path / "bin")

    assert result.returncode == 0
    document = json.loads(result.stdout)
    assert document["version"] == "0.4.0"
    assert document["branch"]
    assert document["commit"]
    datetime.fromisoformat(document["build_time"].replace("Z", "+00:00"))


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

    result = bracketlapse.cli.main(["--standby", str(watch_dir), str(target_dir), "60"])
    output = capsys.readouterr()

    assert result == 0
    assert entered_standby
    assert "usage: bracketlapse" not in output.out
