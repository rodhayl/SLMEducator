#!/usr/bin/env python3
"""SLMEducator headless launcher: the shared lifecycle, never a browser."""

import multiprocessing
from pathlib import Path
import sys

# Preserve source invocation and packaged working-directory behavior.
SRC_PATH = Path(__file__).parent
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(SRC_PATH.parent))

from src.starter import run_console, run_server
from src.startup_utils import setup_frozen_logging, setup_frozen_working_directory


def main() -> int:
    """Run on the existing headless-test port, touching only the launched child."""
    multiprocessing.freeze_support()
    setup_frozen_working_directory()
    setup_frozen_logging()
    return run_console(run_server, port=8000, no_browser=True)


if __name__ == "__main__":
    sys.exit(main())
