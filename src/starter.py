#!/usr/bin/env python3
"""
SLMEducator - Launcher with GUI Control Window
Manages application lifecycle with a system tray style control window.
"""

import sys
import time
import socket
import webbrowser
import multiprocessing
import traceback
from pathlib import Path

# Setup frozen environment BEFORE importing other modules
if getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).parent
    internal_dir = exe_dir / "_internal"
    src_dir = internal_dir / "src"

    sys.path.insert(0, str(internal_dir))
    sys.path.insert(0, str(src_dir))

import uvicorn

# Shared startup utilities
from src.startup_utils import setup_frozen_logging, find_free_port

# GUI imports
try:
    import tkinter as tk
    from tkinter import ttk, messagebox

    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


def log_message(msg):
    """Log to file for debugging."""
    try:
        exe_dir = (
            Path(sys.executable).parent
            if getattr(sys, "frozen", False)
            else Path(__file__).parent.parent.parent
        )
        log_file = exe_dir / "starter_debug.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
            f.flush()
    except Exception:
        pass


def setup_frozen_modules():
    """Setup module namespace for frozen environment."""
    if getattr(sys, "frozen", False):
        import types
        import importlib
        import importlib.util

        exe_dir = Path(sys.executable).parent
        internal_dir = exe_dir / "_internal"
        src_dir = internal_dir / "src"

        # Add paths
        if str(internal_dir) not in sys.path:
            sys.path.insert(0, str(internal_dir))
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        # Create src package if not exists
        if "src" not in sys.modules:
            src_init = src_dir / "__init__.py"
            if src_init.exists():
                spec = importlib.util.spec_from_file_location(
                    "src", str(src_init), submodule_search_locations=[str(src_dir)]
                )
                if spec and spec.loader:
                    src_module = importlib.util.module_from_spec(spec)
                    sys.modules["src"] = src_module
                    spec.loader.exec_module(src_module)
            else:
                src_module = types.ModuleType("src")
                src_module.__path__ = [str(src_dir)]
                sys.modules["src"] = src_module

        # Create api package
        api_dir = src_dir / "api"
        if "src.api" not in sys.modules:
            api_init = api_dir / "__init__.py"
            if api_init.exists():
                spec = importlib.util.spec_from_file_location(
                    "src.api", str(api_init), submodule_search_locations=[str(api_dir)]
                )
                if spec and spec.loader:
                    api_module = importlib.util.module_from_spec(spec)
                    sys.modules["src.api"] = api_module
                    spec.loader.exec_module(api_module)
            else:
                api_module = types.ModuleType("src.api")
                api_module.__path__ = [str(api_dir)]
                sys.modules["src.api"] = api_module

        # Load api.dependencies module (it's a file, not a package)
        deps_file = api_dir / "dependencies.py"
        if deps_file.exists() and "src.api.dependencies" not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                "src.api.dependencies", str(deps_file)
            )
            if spec and spec.loader:
                deps_module = importlib.util.module_from_spec(spec)
                sys.modules["src.api.dependencies"] = deps_module
                spec.loader.exec_module(deps_module)

        # Create core package
        core_dir = src_dir / "core"
        if "src.core" not in sys.modules:
            core_init = core_dir / "__init__.py"
            if core_init.exists():
                spec = importlib.util.spec_from_file_location(
                    "src.core",
                    str(core_init),
                    submodule_search_locations=[str(core_dir)],
                )
                if spec and spec.loader:
                    core_module = importlib.util.module_from_spec(spec)
                    sys.modules["src.core"] = core_module
                    spec.loader.exec_module(core_module)
            else:
                core_module = types.ModuleType("src.core")
                core_module.__path__ = [str(core_dir)]
                sys.modules["src.core"] = core_module

        # Create submodules
        for subdir in ["models", "services"]:
            sub_path = core_dir / subdir
            if sub_path.exists() and f"src.core.{subdir}" not in sys.modules:
                sub_init = sub_path / "__init__.py"
                if sub_init.exists():
                    spec = importlib.util.spec_from_file_location(
                        f"src.core.{subdir}",
                        str(sub_init),
                        submodule_search_locations=[str(sub_path)],
                    )
                    if spec and spec.loader:
                        sub_module = importlib.util.module_from_spec(spec)
                        sys.modules[f"src.core.{subdir}"] = sub_module
                        spec.loader.exec_module(sub_module)
                else:
                    sub_module = types.ModuleType(f"src.core.{subdir}")
                    sub_module.__path__ = [str(sub_path)]
                    sys.modules[f"src.core.{subdir}"] = sub_module


def run_server(port):
    """Run Uvicorn server (target for subprocess)."""
    setup_frozen_logging()
    setup_frozen_modules()

    try:
        import logging

        exe_dir = (
            Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(".")
        )
        log_path = exe_dir / "api.log"

        logging.basicConfig(
            level=logging.INFO,
            filename=str(log_path),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        from src.api.main import app

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="info",
            reload=False,
            log_config=None,
        )
    except Exception as e:
        log_message(f"ERROR in run_server: {str(e)}\n{traceback.format_exc()}")
        raise


class ServerControlWindow:
    """GUI window for controlling the SLM Educator server."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SLM Educator - Server Control")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Server process
        self.server_process = None
        self.port = None
        self.server_running = False

        # Setup UI
        self._setup_ui()

        # Start server automatically
        self.root.after(1000, self.start_server)

        # Update status periodically
        self._schedule_status_update()

    def _setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(
            main_frame, text="SLM Educator Server", font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Server Status", padding="10")
        status_frame.grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10)
        )

        self.status_var = tk.StringVar(value="Starting...")
        status_label = ttk.Label(
            status_frame, textvariable=self.status_var, font=("Arial", 11)
        )
        status_label.grid(row=0, column=0, sticky=tk.W)

        self.port_var = tk.StringVar(value="Port: -")
        port_label = ttk.Label(
            status_frame, textvariable=self.port_var, font=("Arial", 10)
        )
        port_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # URL section
        url_frame = ttk.LabelFrame(main_frame, text="Access URL", padding="10")
        url_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.url_var = tk.StringVar(value="Not started")
        url_label = ttk.Label(
            url_frame,
            textvariable=self.url_var,
            font=("Arial", 10, "underline"),
            foreground="blue",
            cursor="hand2",
        )
        url_label.grid(row=0, column=0, sticky=tk.W)
        url_label.bind("<Button-1>", self._on_url_click)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        self.start_btn = ttk.Button(
            button_frame, text="Start Server", command=self.start_server
        )
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(
            button_frame, text="Stop Server", command=self.stop_server, state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, padx=5)

        self.browser_btn = ttk.Button(
            button_frame,
            text="Open Browser",
            command=self.open_browser,
            state="disabled",
        )
        self.browser_btn.grid(row=0, column=2, padx=5)

        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Recent Log", padding="10")
        log_frame.grid(
            row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0)
        )

        self.log_text = tk.Text(
            log_frame, height=8, width=50, state="disabled", wrap=tk.WORD
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text["yscrollcommand"] = scrollbar.set

        # Exit button
        exit_btn = ttk.Button(main_frame, text="Exit Application", command=self.on_exit)
        exit_btn.grid(row=5, column=0, columnspan=2, pady=(20, 0))

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # Protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _schedule_status_update(self):
        """Schedule periodic status updates."""
        self.update_status()
        self.root.after(2000, self._schedule_status_update)

    def update_status(self):
        """Update server status display."""
        if self.server_process and self.server_process.is_alive():
            self.server_running = True
            self.status_var.set("Running ✓")
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.browser_btn.config(state="normal")
            if self.port:
                self.port_var.set(f"Port: {self.port}")
                self.url_var.set(f"http://localhost:{self.port}")
        else:
            if self.server_running:
                self.server_running = False
                self.status_var.set("Stopped ✗")
                self.start_btn.config(state="normal")
                self.stop_btn.config(state="disabled")
                self.browser_btn.config(state="disabled")
                self.port_var.set("Port: -")
                self.url_var.set("Not started")
                self._add_log("Server stopped")

    def start_server(self):
        """Start the server."""
        if self.server_process and self.server_process.is_alive():
            return

        try:
            # Find free port
            self.port = self._find_free_port(8000)

            self._add_log(f"Starting server on port {self.port}...")

            # Start server in subprocess
            self.server_process = multiprocessing.Process(
                target=run_server, args=(self.port,)
            )
            self.server_process.start()

            # Wait for server to be ready
            self.root.after(1000, self._check_server_ready)

        except Exception as e:
            self._add_log(f"Error starting server: {e}")
            messagebox.showerror("Error", f"Failed to start server:\n{e}")

    def _check_server_ready(self):
        """Check if server is ready."""
        if not self.server_process or not self.server_process.is_alive():
            self._add_log("Server failed to start")
            return

        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                self._add_log(f"Server ready at http://localhost:{self.port}")
                self.update_status()
                # Auto-open browser
                self.open_browser()
        except OSError:
            # Try again in 1 second
            self.root.after(1000, self._check_server_ready)

    def stop_server(self):
        """Stop the server."""
        if self.server_process and self.server_process.is_alive():
            self._add_log("Stopping server...")
            self.server_process.terminate()
            self.server_process.join(timeout=5)
            if self.server_process.is_alive():
                self.server_process.kill()
                self.server_process.join()
            self._add_log("Server stopped")
            self.update_status()

    def open_browser(self):
        """Open browser to the application."""
        if self.port:
            url = f"http://localhost:{self.port}"
            try:
                webbrowser.open(url)
                self._add_log(f"Opened browser: {url}")
            except Exception as e:
                self._add_log(f"Failed to open browser: {e}")
                messagebox.showerror(
                    "Error",
                    f"Could not open browser.\nPlease manually navigate to:\n{url}",
                )

    def on_exit(self):
        """Handle application exit."""
        if messagebox.askyesno("Exit", "Stop the server and exit?"):
            self.stop_server()
            self.root.destroy()
            sys.exit(0)

    def _find_free_port(self, start_port):
        """Find a free port (delegates to shared utility)."""
        return find_free_port(start_port)

    def _add_log(self, message):
        """Add a message to the log display."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        log_message(message)

    def _on_url_click(self, event):
        """Handle URL click."""
        self.open_browser()

    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    log_message("=== SLM Educator Starting ===")

    if not GUI_AVAILABLE:
        # Fallback to console mode if GUI not available
        log_message("GUI not available, running in console mode")
        print("SLM Educator - Starting in console mode...")
        print("(Install tkinter for GUI control window)")

        # Find port
        port = 8000
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    break
            except OSError:
                port += 1

        print(f"Starting server on port {port}...")

        # Start server
        server_process = multiprocessing.Process(target=run_server, args=(port,))
        server_process.start()

        # Wait for ready
        print("Waiting for server...")
        for _ in range(30):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    print(f"Server ready at http://localhost:{port}")
                    webbrowser.open(f"http://localhost:{port}")
                    break
            except OSError:
                time.sleep(0.5)

        print("\nPress Ctrl+C to stop")
        try:
            while server_process.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server_process.terminate()
            server_process.join()
        return

    # Start GUI
    multiprocessing.freeze_support()
    app = ServerControlWindow()
    app.run()


if __name__ == "__main__":
    main()
