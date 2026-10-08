#!/usr/bin/env python3
"""
SLMEducator - Launcher with GUI Control Window
Manages application lifecycle with a small native control window.
"""

from __future__ import annotations

import sys
import time
import locale
import queue
import threading
import webbrowser
import multiprocessing
import traceback
from pathlib import Path
from typing import Callable

# Setup frozen environment BEFORE importing other modules
if getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).parent
    internal_dir = exe_dir / "_internal"
    src_dir = internal_dir / "src"

    sys.path.insert(0, str(internal_dir))
    sys.path.insert(0, str(src_dir))

import uvicorn

# Shared startup utilities
from src.startup_utils import (
    setup_frozen_logging,
    setup_frozen_working_directory,
    find_free_port,
    check_port_available,
    LauncherLifecycle,
    OwnedProcess,
    check_server_ready,
    stop_owned_process,
    wait_for_server,
)

# GUI imports
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, font as tkfont

    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


def ensure_initial_admin(*, gui: bool = True, language: str = "es") -> bool:
    """Load bootstrap only after frozen runtime paths have been established."""
    from src.first_run_setup import ensure_initial_admin as setup
    return setup(gui=gui, language=language)


def log_message(msg: str) -> None:
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


def setup_frozen_modules() -> None:
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


def run_server(port: int) -> None:
    """Run Uvicorn server (target for subprocess)."""
    setup_frozen_working_directory()
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


# Native launcher strings live together and do not depend on a frontend build.
TEXT = {
    "en": {
        "title": "SLMEducator · Local application", "subtitle": "Your space to teach and learn",
        "language": "Language", "status": "LOCAL APPLICATION", "open": "Open SLMEducator",
        "start": "Start", "stop": "Stop", "exit": "Close", "copy": "Copy link",
        "address": "Local address", "logs": "Recent activity", "hide_logs": "Hide activity",
        "footer": "Keep this window open while using SLMEducator.",
        "keys": "Ctrl+O: open · Ctrl+L: select link · Ctrl+Q: close",
        "starting": "Starting your application", "slow": "Startup is taking longer",
        "ready": "Ready to open", "error": "Needs attention", "stopping": "Stopping…",
        "stopped": "Application stopped",
        "starting_detail": "Preparing the local server. This can take a moment.",
        "slow_detail": "Still waiting for the application to respond. You can stop it safely.",
        "ready_detail": "The local server is responding. Open SLMEducator in your browser.",
        "stopping_detail": "Waiting for this window's server to stop. Other applications are untouched.",
        "stopped_detail": "Choose Start to return. Your saved data remains on this computer.",
        "timeout_detail": "No valid response after 30 seconds. Stop the server, then try again. See api.log for details.",
        "start_failed_detail": "The server could not start. Check available ports and api.log, then try again.",
        "exited_detail": "The server process exited. Check api.log, then choose Start to try again.",
        "unavailable_detail": "The server is no longer responding correctly. Checking again; opening is disabled.",
        "stop_failed_detail": "The server has not stopped. Try Stop again. This window will stay open.",
        "confirm_stop": "Stop the local application? Save your work in the browser first. Open tabs will lose their connection.",
        "confirm_exit": "Stop the local application and close this window? Save your work in the browser first.",
        "browser_failed": "The browser could not be opened. Copy the local address and paste it into your browser.",
        "browser_opened": "The link was sent to your browser.", "copied": "Local address copied.",
        "copy_failed": "The clipboard is unavailable. Select the address and copy it with Ctrl+C.",
        "port_log": "Starting local server on port {port}.", "exit_log": "Child process exit code: {code}.",
        "console": "SLMEducator · Console mode", "waiting": "Waiting for a valid local API response…",
        "console_ready": "Local server ready: {url}", "ctrl_c": "Press Ctrl+C to stop.",
        "headless": "Running headless; no browser will be opened.",
    },
    "es": {
        "title": "SLMEducator · Aplicación local", "subtitle": "Tu espacio para enseñar y aprender",
        "language": "Idioma", "status": "APLICACIÓN LOCAL", "open": "Abrir SLMEducator",
        "start": "Iniciar", "stop": "Detener", "exit": "Cerrar", "copy": "Copiar enlace",
        "address": "Dirección local", "logs": "Actividad reciente", "hide_logs": "Ocultar actividad",
        "footer": "Mantén esta ventana abierta mientras usas SLMEducator.",
        "keys": "Ctrl+O: abrir · Ctrl+L: seleccionar enlace · Ctrl+Q: cerrar",
        "starting": "Iniciando tu aplicación", "slow": "El inicio está tardando más",
        "ready": "Lista para abrir", "error": "Requiere atención", "stopping": "Deteniendo…",
        "stopped": "Aplicación detenida",
        "starting_detail": "Preparando el servidor local. Puede tardar un momento.",
        "slow_detail": "Seguimos esperando la respuesta de la aplicación. Puedes detenerla de forma segura.",
        "ready_detail": "El servidor local responde. Abre SLMEducator en tu navegador.",
        "stopping_detail": "Esperando a que se detenga el servidor de esta ventana. No se alteran otras aplicaciones.",
        "stopped_detail": "Elige Iniciar para volver. Tus datos guardados permanecen en este equipo.",
        "timeout_detail": "Sin respuesta válida tras 30 segundos. Detén el servidor e inténtalo de nuevo. Consulta api.log.",
        "start_failed_detail": "No se pudo iniciar el servidor. Revisa los puertos disponibles y api.log e inténtalo de nuevo.",
        "exited_detail": "El proceso del servidor terminó. Consulta api.log y elige Iniciar para volver a intentarlo.",
        "unavailable_detail": "El servidor ya no responde correctamente. Seguimos comprobándolo; no se puede abrir todavía.",
        "stop_failed_detail": "El servidor no se ha detenido. Pulsa Detener otra vez. Esta ventana seguirá abierta.",
        "confirm_stop": ("¿Detener la aplicación local? Guarda primero tu trabajo en el navegador. "
                         "Las pestañas abiertas perderán la conexión."),
        "confirm_exit": "¿Detener la aplicación local y cerrar esta ventana? Guarda primero tu trabajo en el navegador.",
        "browser_failed": "No se pudo abrir el navegador. Copia la dirección local y pégala en tu navegador.",
        "browser_opened": "Se ha enviado el enlace a tu navegador.", "copied": "Dirección local copiada.",
        "copy_failed": "El portapapeles no está disponible. Selecciona la dirección y cópiala con Ctrl+C.",
        "port_log": "Iniciando el servidor local en el puerto {port}.", "exit_log": "Código de salida del proceso: {code}.",
        "console": "SLMEducator · Modo consola", "waiting": "Esperando una respuesta válida de la API local…",
        "console_ready": "Servidor local listo: {url}", "ctrl_c": "Pulsa Ctrl+C para detener.",
        "headless": "Modo sin interfaz; no se abrirá el navegador.",
    },
}


def default_language() -> str:
    """Use the OS language when available without writing application settings."""
    try:
        return "es" if (locale.getlocale()[0] or "").lower().startswith("es") else "en"
    except (ValueError, TypeError):
        return "en"


class ServerControlWindow:
    """Resizable native launcher with asynchronous readiness and truthful states."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.lifecycle = LauncherLifecycle()
        self.language = default_language()
        self.events: queue.Queue[tuple[str, int, bool]] = queue.Queue()
        self.probe_generation: int | None = None
        self.next_probe = 0.0
        self.browser_opening = False
        self.auto_opened_generation: int | None = None
        self.exit_when_stopped = False
        self.closed = False
        self.activity: list[tuple[str, str, dict[str, object]]] = []
        self.notice = ""
        self.previous_status: tuple[str, str] | None = None
        self._setup_ui()
        self._render()
        self.root.after(150, self.start_server)
        self.root.after(200, self._poll)

    def _text(self, key: str, **values: object) -> str:
        return TEXT[self.language][key].format(**values)

    def _setup_style(self) -> None:
        # Point-sized system fonts and Tk's native display scaling avoid fixed
        # pixel typography. Native 200% DPI still needs Windows acceptance.
        family = tkfont.nametofont("TkDefaultFont").actual("family")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f5ef")
        style.configure("TLabel", background="#f3f5ef", foreground="#193432", font=(family, 11))
        style.configure("Muted.TLabel", foreground="#50625d", font=(family, 10))
        style.configure("Title.TLabel", font=(family, 24, "bold"))
        style.configure("Status.TLabel", background="#fffef9", font=(family, 18, "bold"))
        style.configure("Card.TFrame", background="#fffef9", borderwidth=1, relief="solid")
        style.configure("Card.TLabel", background="#fffef9", foreground="#50625d")
        style.configure("TButton", font=(family, 11), padding=(14, 10), foreground="#193432",
                        background="#e7ede5", focusthickness=2, focuscolor="#17635f")
        style.map("TButton", background=[("active", "#d4dfd7")], foreground=[("disabled", "#50625d")])
        style.configure("Primary.TButton", background="#17635f", foreground="#ffffff",
                        padding=(18, 13), focuscolor="#ffffff")
        style.map("Primary.TButton", background=[("disabled", "#e7ede5"), ("active", "#124e4b")],
                  foreground=[("disabled", "#50625d"), ("!disabled", "#ffffff")])
        style.configure("TEntry", font=(family, 11), padding=9)
        style.map("TEntry", fieldbackground=[("readonly", "#fffef9")])
        style.configure("TCombobox", font=(family, 10), padding=5)
        self.root.configure(background="#f3f5ef")

    def _setup_ui(self) -> None:
        self._setup_style()
        self.root.resizable(True, True)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main = ttk.Frame(self.root, padding=24)
        self.main.grid(sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self._setup_heading()
        self._setup_status()
        self._setup_actions()
        self._setup_activity()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.bind("<Control-o>", self.open_browser)
        self.root.bind("<Control-l>", self.select_url)
        self.root.bind("<Control-q>", self.on_exit)
        self.root.bind("<Configure>", self._resize_text)
        self._render()
        self.root.update_idletasks()
        # Let requested font metrics determine minimum size rather than freezing
        # a 500x400 layout; the address and diagnostics grow with the window.
        self.root.minsize(self.root.winfo_reqwidth(), self.root.winfo_reqheight())

    def _setup_heading(self) -> None:
        heading = ttk.Frame(self.main)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="SLMEducator", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.subtitle = ttk.Label(heading, style="Muted.TLabel")
        self.subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.language_label = ttk.Label(heading, style="Muted.TLabel")
        self.language_label.grid(row=0, column=1, sticky="w", padx=(16, 0))
        self.language_var = tk.StringVar(value="Español" if self.language == "es" else "English")
        self.language_select = ttk.Combobox(heading, textvariable=self.language_var,
                                           values=("Español", "English"), state="readonly", width=9)
        self.language_select.grid(row=1, column=1, padx=(16, 0))
        self.language_select.bind("<<ComboboxSelected>>", self._change_language)

    def _setup_status(self) -> None:
        card = ttk.Frame(self.main, style="Card.TFrame", padding=20)
        card.grid(row=1, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)
        self.status_caption = ttk.Label(card, style="Card.TLabel")
        self.status_caption.grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(card, style="Status.TLabel")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(10, 8))
        self.detail_label = ttk.Label(card, style="Card.TLabel", wraplength=440, justify="left")
        self.detail_label.grid(row=2, column=0, sticky="ew")
        self.browser_btn = ttk.Button(card, style="Primary.TButton", command=self.open_browser)
        self.browser_btn.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        self.address_label = ttk.Label(self.main, style="Muted.TLabel")
        self.address_label.grid(row=2, column=0, sticky="w", pady=(18, 6))
        address = ttk.Frame(self.main)
        address.grid(row=3, column=0, sticky="ew")
        address.columnconfigure(0, weight=1)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(address, textvariable=self.url_var, state="readonly", width=30, takefocus=True)
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self.url_entry.bind("<Return>", self.open_browser)
        self.copy_btn = ttk.Button(address, command=self.copy_url)
        self.copy_btn.grid(row=0, column=1, padx=(8, 0))
        self.notice_label = ttk.Label(self.main, style="Muted.TLabel", wraplength=480, justify="left")
        self.notice_label.grid(row=4, column=0, sticky="ew", pady=(6, 0))

    def _setup_actions(self) -> None:
        actions = ttk.Frame(self.main)
        actions.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(2, weight=1)
        self.start_btn = ttk.Button(actions, command=self.start_server)
        self.start_btn.grid(row=0, column=0, padx=(0, 8))
        self.stop_btn = ttk.Button(actions, command=self.stop_server)
        self.stop_btn.grid(row=0, column=1)
        self.exit_btn = ttk.Button(actions, command=self.on_exit)
        self.exit_btn.grid(row=0, column=3, sticky="e")
        self.footer = ttk.Label(self.main, style="Muted.TLabel", wraplength=480)
        self.footer.grid(row=6, column=0, sticky="w", pady=(18, 4))
        self.keys_label = ttk.Label(self.main, style="Muted.TLabel", wraplength=480)
        self.keys_label.grid(row=7, column=0, sticky="w")

    def _setup_activity(self) -> None:
        self.logs_visible = False
        self.logs_btn = ttk.Button(self.main, command=self.toggle_activity)
        self.logs_btn.grid(row=8, column=0, sticky="w", pady=(18, 0))
        self.log_frame = ttk.Frame(self.main)
        self.log_frame.grid(row=9, column=0, sticky="nsew", pady=(8, 0))
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)
        self.main.rowconfigure(9, weight=1)
        self.log_text = tk.Text(self.log_frame, height=6, width=40, state="disabled", wrap=tk.WORD,
                                background="#fffef9", foreground="#193432", relief="flat", padx=10, pady=10)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text["yscrollcommand"] = scrollbar.set
        self.log_frame.grid_remove()

    def _resize_text(self, event: tk.Event) -> None:
        if event.widget is self.root:
            width = max(260, event.width - 100)
            self.detail_label.configure(wraplength=width)
            self.notice_label.configure(wraplength=width)
            self.footer.configure(wraplength=width)
            self.keys_label.configure(wraplength=width)

    def _change_language(self, event: tk.Event | None = None) -> None:
        self.language = "es" if self.language_var.get() == "Español" else "en"
        self._render()
        self._render_activity()

    def _render(self) -> None:
        model = self.lifecycle
        self.root.title(self._text("title"))
        for widget, key in ((self.subtitle, "subtitle"), (self.language_label, "language"),
                            (self.status_caption, "status"), (self.browser_btn, "open"),
                            (self.address_label, "address"), (self.copy_btn, "copy"),
                            (self.start_btn, "start"), (self.stop_btn, "stop"), (self.exit_btn, "exit"),
                            (self.footer, "footer"), (self.keys_label, "keys")):
            widget.configure(text=self._text(key))
        self.status_label.configure(text=self._text(model.state),
                                    foreground={"ready": "#27643e", "error": "#983c34", "slow": "#76500a"}.get(model.state, "#193432"))
        self.detail_label.configure(text=self._text(f"{model.reason}_detail"))
        if self.url_var.get() != model.url:
            self.url_var.set(model.url)
        self.browser_btn.configure(state="normal" if model.can_open and not self.browser_opening else "disabled")
        self.start_btn.configure(state="disabled" if model.alive or model.state == "stopping" else "normal")
        self.stop_btn.configure(state="normal" if model.alive and model.state != "stopping" else "disabled")
        self.copy_btn.configure(state="normal" if model.url else "disabled")
        self.notice_label.configure(text=self._text(self.notice) if self.notice else "")
        self.logs_btn.configure(text=self._text("hide_logs" if self.logs_visible else "logs"))
        status = (model.state, model.reason)
        if status != self.previous_status:
            self.previous_status = status
            self._add_log(f"{model.reason}_detail")
            if model.reason == "exited" and model.process is not None:
                self._add_log("exit_log", code=model.process.exitcode)

    def start_server(self) -> None:
        """Start one child only; retain existing frozen/bootstrap behavior."""
        if self.lifecycle.alive or self.lifecycle.state == "stopping" or self.closed:
            return
        self.notice = ""
        try:
            port = find_free_port(8000)
            process = multiprocessing.Process(target=run_server, args=(port,))
            process.start()
            self.lifecycle.attach(process, port)
            self._add_log("port_log", port=port)
            self.next_probe = 0.0
        except (OSError, RuntimeError, ValueError):
            self.lifecycle.fail_start()
        self._render()

    def _poll(self) -> None:
        if self.closed:
            return
        self.lifecycle.tick()
        self._consume_events()
        if self.exit_when_stopped:
            if self.lifecycle.state == "stopped":
                self._close()
                return
            if self.lifecycle.reason == "stop_failed":
                self.exit_when_stopped = False
        if (self.lifecycle.should_probe and self.probe_generation is None
                and time.monotonic() >= self.next_probe):
            self.probe_generation = self.lifecycle.generation
            threading.Thread(target=self._probe, args=(self.lifecycle.process, self.lifecycle.port,
                             self.probe_generation), daemon=True).start()
        self._render()
        self.root.after(200, self._poll)

    def _probe(self, process: OwnedProcess, port: int, generation: int) -> None:
        ready = check_server_ready(process, port)
        self.events.put(("probe", generation, ready))

    def _consume_events(self) -> None:
        while True:
            try:
                kind, generation, result = self.events.get_nowait()
            except queue.Empty:
                return
            if kind == "probe":
                self.probe_generation = None
                self.next_probe = time.monotonic() + 1.0
                self.lifecycle.apply_probe(generation, result)
                if (self.lifecycle.can_open and self.auto_opened_generation != self.lifecycle.generation
                        and "--no-browser" not in sys.argv):
                    self.auto_opened_generation = self.lifecycle.generation
                    self.open_browser()
            elif kind == "browser":
                self.browser_opening = False
                if generation == self.lifecycle.generation:
                    self.notice = "browser_opened" if result else "browser_failed"
                    self._add_log(self.notice)

    def stop_server(self) -> None:
        """Confirm browser-work impact and asynchronously stop only our child."""
        if self.lifecycle.state == "stopping" or not self.lifecycle.alive:
            return
        if messagebox.askyesno(self._text("stop"), self._text("confirm_stop"), parent=self.root):
            self.notice = ""
            self.lifecycle.begin_stop()
            self._render()

    def open_browser(self, event: tk.Event | None = None) -> str:
        """Open only after readiness; failed browser launch keeps a copyable URL."""
        if not self.lifecycle.can_open or self.browser_opening:
            return "break"
        self.browser_opening = True
        self.notice = ""
        threading.Thread(target=self._launch_browser,
                         args=(self.lifecycle.url, self.lifecycle.generation), daemon=True).start()
        self._render()
        return "break"

    def _launch_browser(self, url: str, generation: int) -> None:
        if generation != self.lifecycle.generation or not self.lifecycle.can_open:
            self.events.put(("browser", generation, False))
            return
        try:
            opened = bool(webbrowser.open(url))
        except Exception:
            opened = False
        self.events.put(("browser", generation, opened))

    def select_url(self, event: tk.Event | None = None) -> str:
        """Expose the local URL to normal keyboard selection and copy shortcuts."""
        self.url_entry.focus_set()
        self.url_entry.selection_range(0, tk.END)
        return "break"

    def copy_url(self) -> None:
        """Copy the address without making readiness claims."""
        if not self.lifecycle.url:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.lifecycle.url)
            self.notice = "copied"
        except tk.TclError:
            self.notice = "copy_failed"
        self._render()

    def toggle_activity(self) -> None:
        """Keep bounded diagnostics secondary and keyboard accessible."""
        self.logs_visible = not self.logs_visible
        if self.logs_visible:
            self.log_frame.grid()
        else:
            self.log_frame.grid_remove()
        self._render()

    def _add_log(self, key: str, **values: object) -> None:
        self.activity.append((time.strftime("%H:%M:%S"), key, values))
        self.activity = self.activity[-80:]
        self._render_activity()
        log_message(self._text(key, **values))

    def _render_activity(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        for stamp, key, values in self.activity:
            self.log_text.insert(tk.END, f"[{stamp}] {self._text(key, **values)}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def on_exit(self, event: tk.Event | None = None) -> str:
        """Keep the window open until its owned process is confirmed stopped."""
        if self.lifecycle.state == "stopping":
            return "break"
        if not self.lifecycle.alive:
            self._close()
        elif messagebox.askyesno(self._text("exit"), self._text("confirm_exit"), parent=self.root):
            self.exit_when_stopped = True
            self.notice = ""
            self.lifecycle.begin_stop()
            self._render()
        return "break"

    def _close(self) -> None:
        self.closed = True
        self.root.destroy()

    def run(self) -> None:
        """Run the GUI application."""
        self.root.mainloop()


def run_console(
    server_target: Callable[[int], None] = run_server, port: int | None = None, *, no_browser: bool = False
) -> int:
    """Run the same readiness/shutdown contract without a native window."""
    strings = TEXT[default_language()]
    print(strings["console"])
    try:
        if port is None:
            port = find_free_port(8000)
        elif not check_port_available(port):
            raise OSError("The requested local server port is occupied")
        process = multiprocessing.Process(target=server_target, args=(port,))
        process.start()
    except (OSError, RuntimeError, ValueError):
        print(strings["start_failed_detail"])
        return 1
    result = 0
    try:
        print(strings["waiting"])
        if not wait_for_server(process, port):
            print(strings["timeout_detail"] if process.is_alive() else strings["exited_detail"])
            return 1
        if not process.is_alive():
            print(strings["exited_detail"])
            return 1
        url = f"http://127.0.0.1:{port}"
        print(strings["console_ready"].format(url=url))
        if no_browser or "--no-browser" in sys.argv:
            print(strings["headless"])
        else:
            try:
                if not webbrowser.open(url):
                    print(strings["browser_failed"])
            except Exception:
                print(strings["browser_failed"])
        print(strings["ctrl_c"])
        while process.is_alive():
            time.sleep(0.5)
        print(strings["exited_detail"])
        result = 1
    except KeyboardInterrupt:
        print(strings["stopping"])
    finally:
        if stop_owned_process(process):
            print(strings["stopped"])
        else:
            print(strings["stop_failed_detail"])
            result = 1
    return result


def main() -> int:
    """Preserve recovery dispatch and frozen multiprocessing in every mode."""
    setup_frozen_working_directory()
    setup_frozen_logging()
    multiprocessing.freeze_support()
    if len(sys.argv) > 1 and sys.argv[1] == "--recovery":
        from scripts.recover_database import main as recover_database

        return recover_database(sys.argv[2:])
    log_message("=== SLM Educator Starting ===")
    if not ensure_initial_admin(gui=GUI_AVAILABLE, language=default_language()):
        return 1
    if not GUI_AVAILABLE:
        return run_console()
    try:
        app = ServerControlWindow()
    except tk.TclError:
        return run_console()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
