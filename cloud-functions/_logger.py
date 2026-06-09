"""Shared tagged logger utility for cloud-functions."""

import sys
from datetime import datetime, timezone


class Logger:
    """Tagged logger with ISO timestamps."""

    def __init__(self, tag: str):
        self._tag = tag

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    def log(self, *args):
        print(f"[{self._tag}][{self._ts()}]", *args, file=sys.stdout, flush=True)

    def error(self, *args):
        print(f"[{self._tag}][{self._ts()}]", *args, file=sys.stderr, flush=True)

    def warn(self, *args):
        print(f"[{self._tag}][{self._ts()}] WARN:", *args, file=sys.stderr, flush=True)


def create_logger(tag: str) -> Logger:
    return Logger(tag)
