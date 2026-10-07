"""Shared, dependency-free lifecycle and readiness helpers for the launchers."""

from http.client import HTTPConnection, HTTPException
import json
import os
from pathlib import Path
import socket
import sys
import time
import threading
from typing import Callable, Literal, Protocol


class NullWriter:
    """Suppress missing stdout/stderr in frozen windowed environments."""

    def write(self, text: str) -> None:
        pass

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False


def setup_frozen_logging() -> None:
    """Handle missing stdout/stderr in frozen windowed apps."""
    if sys.stdout is None:
        sys.stdout = NullWriter()  # type: ignore[assignment]
    if sys.stderr is None:
        sys.stderr = NullWriter()  # type: ignore[assignment]


def setup_frozen_working_directory() -> None:
    """Keep packaged database/config paths beside the executable, not the caller."""
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)


def find_free_port(start_port: int = 8000) -> int:
    """Find a candidate loopback port; fail clearly if none can be reserved."""
    for port in range(start_port, 65536):
        if check_port_available(port):
            return port
    raise OSError("No available local server port")


def check_port_available(port: int) -> bool:
    """Reject an occupied fixed port without interacting with its listener.

    This is a preflight, not a reservation or process-identity guarantee. The
    child still owns binding its server socket, as in the existing launchers.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


class OwnedProcess(Protocol):
    """Only the child process created by this launcher may be controlled."""

    @property
    def exitcode(self) -> int | None: ...

    def is_alive(self) -> bool: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def join(self, timeout: float | None = None) -> None: ...


LaunchState = Literal["stopped", "starting", "slow", "ready", "error", "stopping"]
STARTUP_SLOW_SECONDS = 10.0
STARTUP_TIMEOUT_SECONDS = 30.0
PROBE_TIMEOUT_SECONDS = 0.4
STATUS_BODY_LIMIT = 4096


def check_server_ready(process: OwnedProcess, port: int) -> bool:
    """Check the existing local API contract and the launched child's liveness.

    Use a direct loopback connection, never a proxy or redirect. Limit both IO
    waiting and response bytes. This checks readiness, not process authentication
    or frontend-build integrity; the existing endpoint exposes neither identity.
    """
    if not process.is_alive():
        return False
    connection = HTTPConnection("127.0.0.1", port, timeout=PROBE_TIMEOUT_SECONDS)
    deadline_timer: threading.Timer | None = None
    response = None
    try:
        connection.connect()
        transport = connection.sock

        def interrupt_read() -> None:
            # A socket timeout alone is an inactivity timeout. Interrupt even
            # slowly trickling headers/body at an absolute per-probe deadline.
            if transport is not None:
                try:
                    transport.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        deadline_timer = threading.Timer(PROBE_TIMEOUT_SECONDS, interrupt_read)
        deadline_timer.daemon = True
        deadline_timer.start()
        connection.request("GET", "/api/status", headers={"Accept": "application/json"})
        response = connection.getresponse()
        media_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        if response.status != 200 or media_type != "application/json":
            return False
        # read1 avoids an indefinitely trickling peer extending each socket timeout.
        deadline = time.monotonic() + PROBE_TIMEOUT_SECONDS
        body = bytearray()
        while len(body) <= STATUS_BODY_LIMIT:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(STATUS_BODY_LIMIT + 1 - len(body))
            if not chunk:
                break
            body.extend(chunk)
        if len(body) > STATUS_BODY_LIMIT:
            return False
        payload = json.loads(body)
        return (
            isinstance(payload, dict)
            and payload.get("status") == "online"
            and payload.get("version") == "2.0.0"
            and process.is_alive()
        )
    except (OSError, HTTPException, ValueError, UnicodeError, RecursionError):
        return False
    finally:
        if deadline_timer is not None:
            deadline_timer.cancel()
        if response is not None:
            response.close()
        connection.close()


class LauncherLifecycle:
    """Small Tk-independent state machine; tick never waits for a live child."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.process: OwnedProcess | None = None
        self.port: int | None = None
        self.state: LaunchState = "stopped"
        self.reason = "stopped"
        self.started_at = 0.0
        self.stop_deadline = 0.0
        self.kill_sent = False
        self.generation = 0

    @property
    def alive(self) -> bool:
        """Return the owned child's current liveness, never a PID/port scan."""
        return self.process is not None and self.process.is_alive()

    @property
    def url(self) -> str:
        """Return the exact browser origin used by the loopback server."""
        return f"http://127.0.0.1:{self.port}" if self.port is not None else ""

    @property
    def can_open(self) -> bool:
        """A live child alone never enables the browser action."""
        return self.state == "ready" and self.alive

    @property
    def should_probe(self) -> bool:
        """Only initial/recoverable health states are polled."""
        return self.alive and (
            self.state in ("starting", "slow", "ready")
            or (self.state == "error" and self.reason == "unavailable")
        )

    def attach(self, process: OwnedProcess, port: int) -> None:
        """Attach a newly launched child; callers must never replace a live one."""
        if self.alive:
            raise RuntimeError("The launched server must stop before restarting")
        self.process = process
        self.port = port
        self.generation += 1
        self.started_at = self.clock()
        self.state = "starting"
        self.reason = "starting"
        self.kill_sent = False

    def fail_start(self) -> None:
        """Expose process creation/port failure without claiming a running server."""
        self.state, self.reason = "error", "start_failed"

    def apply_probe(self, generation: int, ready: bool) -> None:
        """Ignore old results after Stop/restart and recheck liveness on delivery."""
        self.tick()
        if generation != self.generation or not self.should_probe:
            return
        if ready:
            self.state, self.reason = "ready", "ready"
        elif self.state == "ready":
            self.state, self.reason = "error", "unavailable"

    def begin_stop(self) -> None:
        """Request bounded termination of this launcher's child without waiting."""
        self.generation += 1
        if not self.alive:
            self._mark_stopped()
            return
        self.state, self.reason = "stopping", "stopping"
        self.kill_sent = False
        self.stop_deadline = self.clock() + 4.0
        try:
            assert self.process is not None
            self.process.terminate()
        except (OSError, ValueError):
            self.state, self.reason = "error", "stop_failed"

    def tick(self) -> None:
        """Advance deadlines and detect exit, without an unbounded join."""
        if self.process is None:
            return
        if not self.alive:
            if self.state == "stopping" or self.reason == "stop_failed":
                self._mark_stopped()
            elif self.state != "stopped":
                self.process.join(timeout=0)
                self.state, self.reason = "error", "exited"
            return
        if self.state == "stopping":
            self._tick_stopping()
        elif self.state in ("starting", "slow"):
            elapsed = self.clock() - self.started_at
            if elapsed >= STARTUP_TIMEOUT_SECONDS:
                self.state, self.reason = "error", "timeout"
            elif elapsed >= STARTUP_SLOW_SECONDS:
                self.state, self.reason = "slow", "slow"

    def _tick_stopping(self) -> None:
        if self.clock() < self.stop_deadline:
            return
        if self.kill_sent:
            self.state, self.reason = "error", "stop_failed"
            return
        self.kill_sent = True
        self.stop_deadline = self.clock() + 2.0
        try:
            assert self.process is not None
            self.process.kill()
        except (OSError, ValueError):
            self.state, self.reason = "error", "stop_failed"

    def _mark_stopped(self) -> None:
        if self.process is not None:
            self.process.join(timeout=0)
        self.state, self.reason = "stopped", "stopped"


def stop_owned_process(process: OwnedProcess) -> bool:
    """Console-only bounded shutdown; return false if the child remains alive."""
    lifecycle = LauncherLifecycle()
    lifecycle.process = process
    lifecycle.begin_stop()
    while lifecycle.state == "stopping":
        time.sleep(0.1)
        lifecycle.tick()
    return not lifecycle.alive


def wait_for_server(process: OwnedProcess, port: int) -> bool:
    """Bound console startup using the same status contract as the GUI."""
    lifecycle = LauncherLifecycle()
    lifecycle.attach(process, port)
    while lifecycle.should_probe:
        lifecycle.apply_probe(lifecycle.generation, check_server_ready(process, port))
        if lifecycle.can_open:
            return True
        time.sleep(0.25)
        lifecycle.tick()
    return False
