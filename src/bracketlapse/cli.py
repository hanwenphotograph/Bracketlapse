from __future__ import annotations

import sys

from .arguments import build_parser
from .common import BracketlapseError, log
from .environment import ensure_runtime_environment, update_runtime_environment
from .fusion import fuse_brackets
from .standby import extract_standby_config, run_standby
from .video import build_video


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        standby_config, normalized_argv = extract_standby_config(argv)
        parser = build_parser(normalized_argv)
        if should_print_help(normalized_argv, standby=standby_config is not None):
            parser.print_help()
            return 0
        mode = normalized_argv[:1]
        args = parser.parse_args(normalized_argv[1:] if mode in (["video"], ["update"]) else normalized_argv)
        log.set_debug(args.debug)
        command = "video" if mode == ["video"] else "update" if mode == ["update"] else "fuse"
        if not any(token in {"-h", "--help"} for token in normalized_argv):
            if command == "update":
                update_runtime_environment(getattr(args, "dependencies", None))
            else:
                ensure_runtime_environment(args, command)

        if standby_config is not None:
            if argv[:1] == ["video"]:
                raise BracketlapseError("Standby mode cannot be combined with the video command.")
            run_standby(args, standby_config)
        elif argv[:1] == ["update"]:
            return 0
        elif argv[:1] == ["video"]:
            build_video(args)
        else:
            fuse_brackets(args)
    except BracketlapseError as exc:
        log.error(str(exc))
        return 1
    except KeyboardInterrupt:
        log.error("Interrupted.")
        return 130

    return 0


def should_print_help(argv: list[str], *, standby: bool = False) -> bool:
    if any(token in {"-h", "--help"} for token in argv):
        return False
    if standby:
        return False
    return not argv or argv == ["video"]


if __name__ == "__main__":
    raise SystemExit(main())
