from __future__ import annotations

from collections.abc import Callable
import subprocess
import tempfile

from .common import BracketlapseError, _emit_external_output


ProgressCallback = Callable[[int], None]


def run_ffmpeg_with_progress(
    command: list[str],
    total: int,
    on_progress: ProgressCallback | None,
) -> None:
    try:
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as error_output:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=error_output,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert process.stdout is not None
            block: dict[str, str] = {}
            try:
                for raw_line in process.stdout:
                    key, separator, value = raw_line.rstrip("\r\n").partition("=")
                    if not separator:
                        continue
                    block[key] = value
                    if key == "progress":
                        _report_frame(block, total, on_progress)
                        block.clear()
            finally:
                process.stdout.close()
            return_code = process.wait()
            error_output.seek(0)
            errors = error_output.read()
    except FileNotFoundError as exc:
        raise BracketlapseError(f"Executable not found: {command[0]}") from exc

    if return_code != 0:
        _emit_external_output(errors, error=True)
        raise BracketlapseError(
            f"Command failed with exit code {return_code}: {' '.join(command)}"
        )
    _emit_external_output(errors)


def _report_frame(
    block: dict[str, str],
    total: int,
    callback: ProgressCallback | None,
) -> None:
    if callback is None:
        return
    try:
        frame = int(block.get("frame", ""))
    except ValueError:
        return
    callback(min(total, max(0, frame)))
