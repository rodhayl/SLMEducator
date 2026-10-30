#!/usr/bin/env python3
"""
SLMEducator - Headless Launcher for Testing
Manages application lifecycle without launching a browser:
1. checks for zombie processes
2. starts the FastAPI backend
"""

import sys
import time
import socket
import uvicorn
import multiprocessing
from pathlib import Path

# Add src to path
SRC_PATH = Path(__file__).parent
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(SRC_PATH.parent))

# Shared startup utilities
from src.startup_utils import setup_frozen_logging


def check_previous_instances():
    """Check for and prompt to kill previous instances."""
    if not getattr(sys, "frozen", False):
        return
    pass


def run_server(port):
    """Run Uvicorn server (target for subprocess)."""
    setup_frozen_logging()

    import logging

    logging.basicConfig(level=logging.INFO, filename="api.log")

    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        reload=False,
        log_config=None,
    )


def main():
    setup_frozen_logging()
    print("SLM Educator - Headless Starting...")

    port = 8000  # Force 8000 for testing consistency
    print(f"Starting server on http://localhost:{port}")

    # Start Backend in separate process
    server_process = multiprocessing.Process(target=run_server, args=(port,))
    server_process.start()

    # Wait for server to be up
    print("Waiting for server...")
    max_retries = 30
    ready = False
    for _ in range(max_retries):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                ready = True
                break
        except (OSError, ConnectionRefusedError):
            time.sleep(0.5)

    if not ready:
        print("Server failed to start.")
        if server_process.is_alive():
            server_process.terminate()
        sys.exit(1)

    print("Server ready. Running headless (no browser).")

    print("\nPress Ctrl+C to stop.")
    try:
        # Keep main thread alive to monitor
        while server_process.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if server_process.is_alive():
            server_process.terminate()
            server_process.join()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
