"""Shared tagged logger utility.

Also serves as the bootstrap module for SSL trust store injection. Because
every Python handler in this project imports `_logger` (directly or via
another private module), this is the single import-chain root that reliably
runs before any HTTPS connection is opened — including connections issued
by the EdgeOne `context.store` SDK (KV / object-store list/get).

`truststore.inject_into_ssl()` replaces Python's stdlib SSL context with one
backed by the OS trust store (macOS Keychain / Windows Cert Store / Linux
system CA bundle), fixing local-dev `CERTIFICATE_VERIFY_FAILED` errors that
`SSL_CERT_FILE` and `ssl._create_unverified_context` cannot solve.
"""

# ── Bootstrap: install OS-backed SSL trust store ────────────────────
# Must run before any module-level network client is created. Kept silent
# on failure so that environments without truststore (e.g. older Pythons,
# constrained sandboxes) still load the logger.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

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
