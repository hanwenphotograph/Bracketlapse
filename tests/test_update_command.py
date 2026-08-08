from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import bracketlapse.cli
import bracketlapse.environment


def test_update_command_refreshes_dependencies(tmp_path: Path, monkeypatch) -> None:
    created = []
    updated_tools = []
    cloned = []

    monkeypatch.setattr(
        bracketlapse.environment,
        "update_system_tool",
        lambda name: updated_tools.append(name),
    )
    monkeypatch.setattr(
        bracketlapse.environment, "ensure_system_tool", lambda name: name
    )
    monkeypatch.setattr(
        bracketlapse.environment,
        "clone_or_update_simple_deflicker",
        lambda git: cloned.append(git),
    )

    def fake_build(go, output):
        created.append((go, output))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("simple-deflicker\n", encoding="utf-8")

    monkeypatch.setattr(bracketlapse.environment, "build_simple_deflicker", fake_build)
    monkeypatch.setattr(
        bracketlapse.environment,
        "simple_deflicker_bin_dir",
        lambda: tmp_path / ".cache" / "bracketlapse" / "tools" / "bin",
    )
    monkeypatch.setattr(
        bracketlapse.environment,
        "tool_cache_dir",
        lambda: tmp_path / ".cache" / "bracketlapse" / "tools",
    )

    result = bracketlapse.cli.main(["update"])

    assert result == 0
    assert updated_tools == ["enfuse", "ffmpeg", "git", "go"]
    assert cloned == ["git"]
    assert created
    assert (
        tmp_path / ".cache" / "bracketlapse" / "tools" / "bin" / "simple-deflicker"
    ).exists()


def test_update_command_can_target_simple_deflicker(
    tmp_path: Path, monkeypatch
) -> None:
    updated_tools = []
    rebuilt = []

    monkeypatch.setattr(
        bracketlapse.environment,
        "update_system_tool",
        lambda name: updated_tools.append(name),
    )
    monkeypatch.setattr(
        bracketlapse.environment, "ensure_system_tool", lambda name: name
    )

    def fake_update_simple_deflicker():
        rebuilt.append(True)
        return (
            tmp_path / ".cache" / "bracketlapse" / "tools" / "bin" / "simple-deflicker"
        )

    monkeypatch.setattr(
        bracketlapse.environment,
        "update_simple_deflicker",
        fake_update_simple_deflicker,
    )

    result = bracketlapse.cli.main(["update", "simple-deflicker"])

    assert result == 0
    assert updated_tools == []
    assert rebuilt == [True]


def test_update_command_rejects_unknown_dependency() -> None:
    result = bracketlapse.cli.main(["update", "unknown-tool"])

    assert result == 1
