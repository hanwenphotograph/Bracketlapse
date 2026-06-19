from __future__ import annotations

import os
import platform
from pathlib import Path
import shutil
import subprocess

from .common import BracketlapseError, log


def install_system_tool(name: str) -> None:
    commands = install_commands_for_tool(name)
    if not commands:
        raise BracketlapseError(
            f"Automatic installation for {name} is not supported on this system."
        )

    for command in commands:
        manager = command[1] if command[0] == "sudo" else command[0]
        if shutil.which(manager) is None:
            continue
        log.info(f"Running installer: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        emit_command_output(result)
        if result.returncode == 0:
            return

    raise BracketlapseError(
        f"Automatic installation failed for {name}. Install it manually and rerun."
    )


def update_system_tool(name: str) -> None:
    commands = update_commands_for_tool(name)
    if not commands:
        raise BracketlapseError(
            f"Automatic update for {name} is not supported on this system."
        )

    for command in commands:
        manager = command[1] if command[0] == "sudo" else command[0]
        if shutil.which(manager) is None:
            continue
        log.info(f"Running updater: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        emit_command_output(result)
        if result.returncode == 0:
            return

    raise BracketlapseError(
        f"Automatic update failed for {name}. Update it manually and rerun."
    )


def install_commands_for_tool(name: str) -> list[list[str]]:
    system = platform.system().lower()
    package = package_name(name)
    if system == "darwin":
        return [["brew", "install", package]]
    if system == "windows":
        return windows_install_commands(name)
    if system == "linux":
        return linux_install_commands(package)
    return []


def update_commands_for_tool(name: str) -> list[list[str]]:
    system = platform.system().lower()
    package = package_name(name)
    if system == "darwin":
        if name in {"enfuse", "align_image_stack"}:
            return [["brew", "upgrade", "hugin"]]
        return [["brew", "upgrade", package]]
    if system == "windows":
        return windows_update_commands(name, package)
    if system == "linux":
        return linux_update_commands(package)
    return []


def package_name(name: str) -> str:
    if name in {"enfuse", "align_image_stack"}:
        return "hugin"
    if name == "go":
        return "go"
    return name


def windows_install_commands(name: str) -> list[list[str]]:
    winget_ids = {
        "ffmpeg": "Gyan.FFmpeg",
        "go": "GoLang.Go",
        "git": "Git.Git",
        "enfuse": "Hugin.Hugin",
        "align_image_stack": "Hugin.Hugin",
    }
    package = package_name(name)
    commands = []
    winget_id = winget_ids.get(name)
    if winget_id:
        commands.append([
            "winget",
            "install",
            "--id",
            winget_id,
            "-e",
            "--accept-package-agreements",
        ])
    commands.append(["choco", "install", package, "-y"])
    return commands


def windows_update_commands(name: str, package: str) -> list[list[str]]:
    winget_ids = {
        "ffmpeg": "Gyan.FFmpeg",
        "go": "GoLang.Go",
        "git": "Git.Git",
        "enfuse": "Hugin.Hugin",
        "align_image_stack": "Hugin.Hugin",
    }
    commands = []
    winget_id = winget_ids.get(name)
    if winget_id:
        commands.append([
            "winget",
            "upgrade",
            "--id",
            winget_id,
            "-e",
            "--accept-package-agreements",
        ])
    commands.append(["choco", "upgrade", package, "-y"])
    return commands


def linux_install_commands(package: str) -> list[list[str]]:
    commands = [
        ["apt-get", "update"],
        ["apt-get", "install", "-y", package],
        ["dnf", "install", "-y", package],
        ["pacman", "-S", "--noconfirm", package],
    ]
    if hasattr(os, "geteuid") and os.geteuid() != 0 and shutil.which("sudo"):
        return [["sudo", "-n", *command] for command in commands]
    return commands


def linux_update_commands(package: str) -> list[list[str]]:
    commands = [
        ["apt-get", "update"],
        ["apt-get", "install", "-y", "--only-upgrade", package],
        ["dnf", "upgrade", "-y", package],
        ["pacman", "-Syu", "--noconfirm", package],
    ]
    if hasattr(os, "geteuid") and os.geteuid() != 0 and shutil.which("sudo"):
        return [["sudo", "-n", *command] for command in commands]
    return commands


def emit_command_output(result: subprocess.CompletedProcess[str]) -> None:
    for text in (result.stdout, result.stderr):
        if not text:
            continue
        for line in text.strip().split("\n"):
            if line.strip():
                log.debug(line.strip())


def known_binary_directories() -> list[Path]:
    return [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
