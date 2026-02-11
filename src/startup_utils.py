"""
Shared startup utilities for SLMEducator launchers.

Used by both starter.py (GUI) and starter_headless.py (headless)
to handle frozen-environment stdout/stderr redirection and port finding.
"""

import sys
import socket


class NullWriter:
    """Null writer for suppressing stdout/stderr in frozen environments."""

    def write(self, text):
        pass

    def flush(self):
        pass

    def isatty(self):
        return False


def setup_frozen_logging():
    """Handle missing stdout/stderr in frozen windowed apps."""
    if sys.stdout is None:
        sys.stdout = NullWriter()
    if sys.stderr is None:
        sys.stderr = NullWriter()


def find_free_port(start_port: int = 8000) -> int:
    """Find a free port starting from start_port using bind()."""
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            port += 1
    return start_port
