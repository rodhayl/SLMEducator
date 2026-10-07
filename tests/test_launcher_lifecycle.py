"""Synthetic launcher contracts; these do not establish native Tk/Windows UX."""

from string import Formatter
from unittest.mock import MagicMock

import pytest

from src import starter, starter_headless, startup_utils as utils


@pytest.fixture(autouse=True)
def synthetic_fixed_ports(monkeypatch):
    """Console-controller tests never reserve a real port."""
    monkeypatch.setattr(starter, "check_port_available", lambda port: True)


class Child:
    """Synthetic owned child with controllable terminate/kill behavior."""

    def __init__(self, alive=True, terminate_stops=True, kill_stops=True):
        self.alive = alive
        self.exitcode = None if alive else 1
        self.terminate_stops = terminate_stops
        self.kill_stops = kill_stops
        self.calls = []

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.calls.append("terminate")
        if self.terminate_stops:
            self.alive = False

    def kill(self):
        self.calls.append("kill")
        if self.kill_stops:
            self.alive = False

    def join(self, timeout=None):
        self.calls.append(("join", timeout))
        assert timeout == 0, "Tk must never wait for a process"


class Response:
    def __init__(self, body=b'{"status":"online","version":"2.0.0"}', status=200, content_type="application/json"):
        self.body = body
        self.status = status
        self.content_type = content_type

    def getheader(self, name, default):
        assert name == "Content-Type"
        return self.content_type

    def read1(self, limit):
        chunk, self.body = self.body[:limit], self.body[limit:]
        return chunk

    def close(self):
        pass


@pytest.fixture
def connection(monkeypatch):
    connection = MagicMock()
    connection.getresponse.return_value = Response()
    factory = MagicMock(return_value=connection)
    monkeypatch.setattr(utils, "HTTPConnection", factory)
    timer_factory = MagicMock()
    monkeypatch.setattr(utils.threading, "Timer", timer_factory)
    connection.factory = factory
    connection.timer_factory = timer_factory
    return connection


@pytest.fixture
def model():
    now = [0.0]
    lifecycle = utils.LauncherLifecycle(clock=lambda: now[0])
    return lifecycle, now


def test_status_checks_api_contract_and_loopback_without_proxy_or_redirect(connection):
    assert utils.check_server_ready(Child(), 8001)
    connection.factory.assert_called_once_with("127.0.0.1", 8001, timeout=0.4)
    connection.request.assert_called_once_with("GET", "/api/status", headers={"Accept": "application/json"})
    connection.close.assert_called_once()
    connection.timer_factory.return_value.start.assert_called_once()
    connection.timer_factory.return_value.cancel.assert_called_once()


@pytest.mark.parametrize("response", [
    Response(body=b"<html>another app</html>"),
    Response(body=b"not JSON"),
    Response(body=b"[]"),
    Response(body=b"null"),
    Response(body=b'{"status":"online"}'),
    Response(body=b'{"status":"offline","version":"2.0.0"}'),
    Response(body=b'{"status":"online","version":2}'),
    Response(body=b'{"status":"online","version":"other"}'),
    Response(content_type="text/html"),
    Response(status=302),
    Response(status=503),
    Response(body=b" " * 4097),
    Response(body=b"\xff"),
])
def test_foreign_html_malformed_redirect_error_and_oversized_status_are_not_ready(connection, response):
    connection.getresponse.return_value = response
    assert not utils.check_server_ready(Child(), 8000)
    connection.close.assert_called_once()


def test_json_charset_parameter_is_supported(connection):
    connection.getresponse.return_value = Response(content_type="Application/JSON; charset=utf-8")
    assert utils.check_server_ready(Child(), 8000)


def test_dead_child_never_probes_a_preexisting_listener(connection):
    assert not utils.check_server_ready(Child(alive=False), 8000)
    connection.factory.assert_not_called()


def test_child_that_exits_during_probe_cannot_become_ready(connection):
    child = Child()
    child.is_alive = MagicMock(side_effect=[True, False])
    assert not utils.check_server_ready(child, 8000)


@pytest.mark.parametrize("error", [OSError("refused"), utils.HTTPException("incomplete")])
def test_probe_network_failures_fail_closed(connection, error):
    connection.getresponse.side_effect = error
    assert not utils.check_server_ready(Child(), 8000)
    connection.close.assert_called_once()


def test_absolute_probe_timer_interrupts_trickling_connection(connection):
    assert utils.check_server_ready(Child(), 8000)
    timeout, interrupt = connection.timer_factory.call_args.args
    assert timeout == utils.PROBE_TIMEOUT_SECONDS
    interrupt()
    connection.sock.shutdown.assert_called_once_with(utils.socket.SHUT_RDWR)


def test_probe_deadline_fails_even_if_body_keeps_arriving(connection, monkeypatch):
    monkeypatch.setattr(utils.time, "monotonic", MagicMock(side_effect=[0, 1]))
    assert not utils.check_server_ready(Child(), 8000)


def test_connect_failure_closes_without_leaving_timer(connection):
    connection.connect.side_effect = OSError("refused")
    assert not utils.check_server_ready(Child(), 8000)
    connection.close.assert_called_once()
    connection.timer_factory.assert_not_called()


def test_liveness_does_not_enable_browser_and_startup_has_slow_and_timeout_states(model):
    lifecycle, now = model
    lifecycle.attach(Child(), 8000)
    assert lifecycle.state == "starting" and not lifecycle.can_open
    lifecycle.apply_probe(lifecycle.generation, False)
    now[0] = 10
    lifecycle.tick()
    assert lifecycle.state == "slow" and not lifecycle.can_open
    now[0] = 30
    lifecycle.tick()
    assert lifecycle.state == "error" and lifecycle.reason == "timeout"
    assert not lifecycle.should_probe
    lifecycle.apply_probe(lifecycle.generation, True)
    assert not lifecycle.can_open


def test_ready_loses_access_when_health_fails_and_can_recover(model):
    lifecycle, _ = model
    lifecycle.attach(Child(), 8012)
    lifecycle.apply_probe(lifecycle.generation, True)
    assert lifecycle.can_open
    assert lifecycle.url == "http://127.0.0.1:8012"
    lifecycle.apply_probe(lifecycle.generation, False)
    assert not lifecycle.can_open and lifecycle.reason == "unavailable"
    assert lifecycle.should_probe
    lifecycle.apply_probe(lifecycle.generation, True)
    assert lifecycle.can_open


def test_exited_child_is_an_error_even_before_first_readiness(model):
    lifecycle, _ = model
    child = Child()
    lifecycle.attach(child, 8000)
    child.alive = False
    lifecycle.tick()
    assert lifecycle.reason == "exited"
    assert not lifecycle.can_open and not lifecycle.should_probe
    assert child.calls == [("join", 0)]


def test_double_start_cannot_replace_live_owned_process(model):
    lifecycle, _ = model
    child = Child()
    lifecycle.attach(child, 8000)
    with pytest.raises(RuntimeError, match="stop before restarting"):
        lifecycle.attach(Child(), 8001)
    assert lifecycle.process is child


def test_stop_ignores_late_readiness_and_reaps_without_waiting(model):
    lifecycle, _ = model
    child = Child()
    lifecycle.attach(child, 8000)
    old_generation = lifecycle.generation
    lifecycle.begin_stop()
    lifecycle.apply_probe(old_generation, True)
    assert lifecycle.state == "stopped" and not lifecycle.can_open
    assert child.calls == ["terminate", ("join", 0)]


def test_stop_escalates_only_own_child_at_bounded_deadlines(model):
    lifecycle, now = model
    child = Child(terminate_stops=False)
    lifecycle.attach(child, 8000)
    lifecycle.begin_stop()
    assert child.calls == ["terminate"] and lifecycle.state == "stopping"
    now[0] = 3.9
    lifecycle.tick()
    assert child.calls == ["terminate"]
    now[0] = 4
    lifecycle.tick()
    lifecycle.tick()
    assert lifecycle.state == "stopped"
    assert child.calls == ["terminate", "kill", ("join", 0)]


def test_stop_failure_never_claims_stopped_and_can_retry(model):
    lifecycle, now = model
    child = Child(terminate_stops=False, kill_stops=False)
    lifecycle.attach(child, 8000)
    lifecycle.begin_stop()
    now[0] = 4
    lifecycle.tick()
    now[0] = 6
    lifecycle.tick()
    assert lifecycle.state == "error" and lifecycle.reason == "stop_failed"
    assert lifecycle.alive and not lifecycle.can_open
    child.terminate_stops = True
    lifecycle.begin_stop()
    lifecycle.tick()
    assert lifecycle.state == "stopped"


@pytest.mark.parametrize("method", ["terminate", "kill"])
def test_shutdown_exception_remains_truthful(model, method):
    lifecycle, now = model
    child = Child(terminate_stops=False)
    setattr(child, method, MagicMock(side_effect=OSError("denied")))
    lifecycle.attach(child, 8000)
    lifecycle.begin_stop()
    now[0] = 4
    lifecycle.tick()
    assert lifecycle.reason == "stop_failed" and lifecycle.alive


def test_restart_discards_previous_process_readiness(model):
    lifecycle, _ = model
    first = Child()
    lifecycle.attach(first, 8000)
    old_generation = lifecycle.generation
    first.alive = False
    lifecycle.attach(Child(), 8001)
    lifecycle.apply_probe(old_generation, True)
    assert lifecycle.state == "starting" and not lifecycle.can_open


def test_exhausted_ports_raise_instead_of_returning_an_occupied_port(monkeypatch):
    sock = MagicMock()
    sock.__enter__.return_value.bind.side_effect = OSError("occupied")
    monkeypatch.setattr(utils.socket, "socket", MagicMock(return_value=sock))
    with pytest.raises(OSError, match="No available"):
        utils.find_free_port(65535)


def test_last_port_is_a_valid_candidate(monkeypatch):
    sock = MagicMock()
    monkeypatch.setattr(utils.socket, "socket", MagicMock(return_value=sock))
    assert utils.find_free_port(65535) == 65535
    sock.__enter__.return_value.bind.assert_called_once_with(("127.0.0.1", 65535))


def test_console_wait_uses_valid_status_and_child_liveness(monkeypatch):
    child = Child()
    probe = MagicMock(side_effect=[False, True])
    monkeypatch.setattr(utils, "check_server_ready", probe)
    monkeypatch.setattr(utils.time, "sleep", MagicMock())
    assert utils.wait_for_server(child, 8001)
    assert probe.call_count == 2


def test_console_dead_child_does_not_probe(monkeypatch):
    probe = MagicMock()
    monkeypatch.setattr(utils, "check_server_ready", probe)
    assert not utils.wait_for_server(Child(alive=False), 8000)
    probe.assert_not_called()


def test_console_stop_waits_boundedly(monkeypatch):
    monkeypatch.setattr(utils.time, "sleep", MagicMock())
    child = Child()
    assert utils.stop_owned_process(child)
    assert child.calls == ["terminate", ("join", 0)]


@pytest.fixture
def window(monkeypatch):
    """Exercise real GUI controller methods with no display or real processes."""
    monkeypatch.setattr(starter.tk, "Tk", MagicMock())
    monkeypatch.setattr(starter, "log_message", MagicMock())
    monkeypatch.setattr(starter, "default_language", lambda: "en")

    def fake_ui(self):
        for name in ("subtitle", "language_label", "status_caption", "browser_btn", "address_label",
                     "copy_btn", "start_btn", "stop_btn", "exit_btn", "footer", "keys_label",
                     "status_label", "detail_label", "url_var", "notice_label", "logs_btn", "log_text",
                     "url_entry", "language_var", "log_frame"):
            setattr(self, name, MagicMock())
        self.logs_visible = False

    monkeypatch.setattr(starter.ServerControlWindow, "_setup_ui", fake_ui)
    return starter.ServerControlWindow()


def test_gui_never_enables_open_from_liveness_alone(window):
    window.lifecycle.attach(Child(), 8000)
    window._render()
    assert window.browser_btn.configure.call_args.kwargs["state"] == "disabled"
    window.lifecycle.apply_probe(window.lifecycle.generation, True)
    window._render()
    assert window.browser_btn.configure.call_args.kwargs["state"] == "normal"


def test_double_click_start_launches_only_one_child(window, monkeypatch):
    process = Child()
    process.start = MagicMock()
    factory = MagicMock(return_value=process)
    monkeypatch.setattr(starter.multiprocessing, "Process", factory)
    monkeypatch.setattr(starter, "find_free_port", lambda port: 8004)
    window.start_server()
    window.start_server()
    factory.assert_called_once()
    process.start.assert_called_once()
    assert window.lifecycle.state == "starting"


def test_port_failure_has_visible_retriable_state(window, monkeypatch):
    monkeypatch.setattr(starter, "find_free_port", MagicMock(side_effect=OSError("occupied")))
    window.start_server()
    assert window.lifecycle.reason == "start_failed"
    assert window.start_btn.configure.call_args.kwargs["state"] == "normal"


def test_autoopen_waits_for_valid_probe_and_happens_once(window, monkeypatch):
    monkeypatch.setattr(starter.sys, "argv", ["starter"])
    window.open_browser = MagicMock()
    window.lifecycle.attach(Child(), 8000)
    generation = window.lifecycle.generation
    for ready in [False, True, True]:
        window.events.put(("probe", generation, ready))
        window._consume_events()
    window.open_browser.assert_called_once()


def test_no_browser_flag_suppresses_automatic_launch(window, monkeypatch):
    monkeypatch.setattr(starter.sys, "argv", ["starter", "--no-browser"])
    window.open_browser = MagicMock()
    window.lifecycle.attach(Child(), 8000)
    window.events.put(("probe", window.lifecycle.generation, True))
    window._consume_events()
    window.open_browser.assert_not_called()
    assert window.lifecycle.can_open


def test_open_double_click_is_single_flight_and_requires_ready(window, monkeypatch):
    thread = MagicMock()
    monkeypatch.setattr(starter.threading, "Thread", thread)
    window.lifecycle.attach(Child(), 8000)
    window.open_browser()
    thread.assert_not_called()
    window.lifecycle.apply_probe(window.lifecycle.generation, True)
    window.open_browser()
    window.open_browser()
    thread.assert_called_once()
    assert window.browser_opening


@pytest.mark.parametrize("error", [False, RuntimeError("no browser")])
def test_browser_false_or_exception_preserves_copyable_url_and_error(window, monkeypatch, error):
    browser = MagicMock(return_value=error if not isinstance(error, Exception) else None)
    if isinstance(error, Exception):
        browser.side_effect = error
    monkeypatch.setattr(starter.webbrowser, "open", browser)
    window.lifecycle.attach(Child(), 8000)
    window.lifecycle.apply_probe(window.lifecycle.generation, True)
    window.browser_opening = True
    window._launch_browser(window.lifecycle.url, window.lifecycle.generation)
    window._consume_events()
    assert window.notice == "browser_failed" and not window.browser_opening
    assert window.lifecycle.url == "http://127.0.0.1:8000" and window.lifecycle.can_open


def test_browser_response_after_stop_does_not_show_success(window):
    window.lifecycle.attach(Child(), 8000)
    old = window.lifecycle.generation
    window.lifecycle.begin_stop()
    window.events.put(("browser", old, True))
    window._consume_events()
    assert window.notice == ""


def test_stop_cancel_does_not_touch_child(window, monkeypatch):
    child = Child()
    window.lifecycle.attach(child, 8000)
    monkeypatch.setattr(starter.messagebox, "askyesno", lambda *a, **kw: False)
    window.stop_server()
    assert child.calls == []


def test_confirmed_stop_returns_without_joining_live_child(window, monkeypatch):
    child = Child(terminate_stops=False)
    window.lifecycle.attach(child, 8000)
    monkeypatch.setattr(starter.messagebox, "askyesno", lambda *a, **kw: True)
    window.stop_server()
    assert child.calls == ["terminate"] and window.lifecycle.state == "stopping"
    window.stop_server()
    assert child.calls == ["terminate"]


def test_x_closes_only_after_owned_child_has_stopped(window, monkeypatch):
    window.lifecycle.attach(Child(), 8000)
    monkeypatch.setattr(starter.messagebox, "askyesno", lambda *a, **kw: True)
    window.on_exit()
    window.root.destroy.assert_not_called()
    window._poll()
    window.root.destroy.assert_called_once()


def test_x_shutdown_failure_keeps_window_open(window, monkeypatch):
    now = [0.0]
    window.lifecycle = utils.LauncherLifecycle(clock=lambda: now[0])
    window.lifecycle.attach(Child(terminate_stops=False, kill_stops=False), 8000)
    monkeypatch.setattr(starter.messagebox, "askyesno", lambda *a, **kw: True)
    window.on_exit()
    now[0] = 4
    window._poll()
    now[0] = 6
    window._poll()
    window.root.destroy.assert_not_called()
    assert window.lifecycle.reason == "stop_failed"
    assert not window.exit_when_stopped


def test_copy_and_select_url_are_keyboard_accessible(window):
    window.lifecycle.attach(Child(), 8000)
    assert window.select_url() == "break"
    window.url_entry.focus_set.assert_called_once()
    window.url_entry.selection_range.assert_called_once_with(0, starter.tk.END)
    window.copy_url()
    window.root.clipboard_append.assert_called_once_with("http://127.0.0.1:8000")
    assert window.notice == "copied"


def test_clipboard_failure_has_manual_recovery(window):
    window.lifecycle.attach(Child(), 8000)
    window.root.clipboard_clear.side_effect = starter.tk.TclError("unavailable")
    window.copy_url()
    assert window.notice == "copy_failed"


def test_language_switch_updates_states_actions_and_existing_activity(window):
    window.language_var.get.return_value = "Español"
    window._change_language()
    assert window.language == "es"
    assert window.status_label.configure.call_args.kwargs["text"] == "Aplicación detenida"
    assert any(call.kwargs.get("text") == "Abrir SLMEducator" for call in window.browser_btn.configure.call_args_list)
    assert "Tus datos" in window.log_text.insert.call_args.args[1]


def test_recent_activity_is_bounded_and_secondary(window):
    for _ in range(100):
        window._add_log("copied")
    assert len(window.activity) == 80
    window.toggle_activity()
    window.log_frame.grid.assert_called_once()
    window.toggle_activity()
    window.log_frame.grid_remove.assert_called_once()


def test_localized_catalogues_have_equal_keys_and_placeholders():
    en, es = starter.TEXT["en"], starter.TEXT["es"]
    assert en.keys() == es.keys()
    for key in en:
        def fields(value):
            return {field for _, field, _, _ in Formatter().parse(value) if field is not None}
        assert fields(en[key]) == fields(es[key])
        assert en[key] and es[key]


@pytest.mark.parametrize("name,expected", [("es_ES", "es"), ("en_US", "en"), (None, "en")])
def test_default_language(name, expected, monkeypatch):
    monkeypatch.setattr(starter.locale, "getlocale", lambda: (name, None))
    assert starter.default_language() == expected


def test_console_no_browser_flag_and_bounded_cleanup(monkeypatch, capsys):
    child = Child()
    child.start = MagicMock()
    monkeypatch.setattr(starter.multiprocessing, "Process", MagicMock(return_value=child))
    monkeypatch.setattr(starter, "wait_for_server", lambda *a: True)
    monkeypatch.setattr(starter, "default_language", lambda: "en")
    monkeypatch.setattr(starter.sys, "argv", ["starter", "--no-browser"])
    monkeypatch.setattr(starter.time, "sleep", MagicMock(side_effect=KeyboardInterrupt()))
    browser = MagicMock()
    monkeypatch.setattr(starter.webbrowser, "open", browser)
    stop = MagicMock(return_value=True)
    monkeypatch.setattr(starter, "stop_owned_process", stop)
    assert starter.run_console(port=8000) == 0
    browser.assert_not_called()
    stop.assert_called_once_with(child)
    assert "Local server ready: http://127.0.0.1:8000" in capsys.readouterr().out


def test_console_invalid_status_never_opens_and_stops_child(monkeypatch, capsys):
    child = Child()
    child.start = MagicMock()
    monkeypatch.setattr(starter.multiprocessing, "Process", MagicMock(return_value=child))
    monkeypatch.setattr(starter, "wait_for_server", lambda *a: False)
    monkeypatch.setattr(starter, "default_language", lambda: "en")
    browser = MagicMock()
    monkeypatch.setattr(starter.webbrowser, "open", browser)
    stop = MagicMock(return_value=True)
    monkeypatch.setattr(starter, "stop_owned_process", stop)
    assert starter.run_console(port=8000) == 1
    browser.assert_not_called()
    stop.assert_called_once_with(child)
    assert "Local server ready:" not in capsys.readouterr().out


def test_headless_keeps_8000_and_never_opens_browser(monkeypatch):
    run = MagicMock(return_value=0)
    monkeypatch.setattr(starter_headless, "run_console", run)
    monkeypatch.setattr(starter_headless, "setup_frozen_working_directory", MagicMock())
    monkeypatch.setattr(starter_headless, "setup_frozen_logging", MagicMock())
    monkeypatch.setattr(starter_headless.multiprocessing, "freeze_support", MagicMock())
    assert starter_headless.main() == 0
    run.assert_called_once_with(starter_headless.run_server, port=8000, no_browser=True)


def test_main_recovery_is_preserved_before_gui_creation(monkeypatch):
    from scripts import recover_database

    recovery = MagicMock(return_value=4)
    monkeypatch.setattr(recover_database, "main", recovery)
    monkeypatch.setattr(starter.sys, "argv", ["starter", "--recovery", "--help"])
    monkeypatch.setattr(starter, "setup_frozen_working_directory", MagicMock())
    monkeypatch.setattr(starter, "setup_frozen_logging", MagicMock())
    monkeypatch.setattr(starter.multiprocessing, "freeze_support", MagicMock())
    gui = MagicMock()
    monkeypatch.setattr(starter, "ServerControlWindow", gui)
    assert starter.main() == 4
    recovery.assert_called_once_with(["--help"])
    gui.assert_not_called()


def test_unchanged_poll_does_not_clear_keyboard_url_selection(window):
    window.lifecycle.attach(Child(), 8000)
    window.url_var.get.return_value = window.lifecycle.url
    window.url_var.set.reset_mock()
    window._render()
    window.url_var.set.assert_not_called()


def test_deeply_nested_json_fails_closed(connection):
    connection.getresponse.return_value = Response(body=b"[" * 1500 + b"0" + b"]" * 1500)
    assert not utils.check_server_ready(Child(), 8000)


def test_native_layout_wires_resizing_keyboard_and_readonly_address(monkeypatch):
    """Mocked widget wiring only, not native screen-reader or visual acceptance."""
    root = MagicMock()
    monkeypatch.setattr(starter.tk, "Tk", MagicMock(return_value=root))
    monkeypatch.setattr(starter.tk, "StringVar", MagicMock())
    monkeypatch.setattr(starter.tk, "Text", MagicMock())
    monkeypatch.setattr(starter.tkfont, "nametofont", MagicMock())
    for name in ("Frame", "Label", "Button", "Entry", "Scrollbar", "Combobox", "Style"):
        monkeypatch.setattr(starter.ttk, name, MagicMock())
    monkeypatch.setattr(starter, "log_message", MagicMock())
    window = starter.ServerControlWindow()
    root.resizable.assert_called_once_with(True, True)
    assert {call.args[0] for call in root.bind.call_args_list} >= {
        "<Control-o>", "<Control-l>", "<Control-q>", "<Configure>"
    }
    assert starter.ttk.Entry.call_args.kwargs["state"] == "readonly"
    assert starter.ttk.Entry.call_args.kwargs["takefocus"] is True
    window.url_entry.bind.assert_called_once_with("<Return>", window.open_browser)
    root.protocol.assert_called_once_with("WM_DELETE_WINDOW", window.on_exit)


def test_launcher_text_color_pairs_meet_normal_text_contrast():
    """Measure declared normal-text tokens, not rendered/OS/high-contrast states."""
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in zip(linear, [0.2126, 0.7152, 0.0722]))

    for text, background in [("#193432", "#f3f5ef"), ("#50625d", "#f3f5ef"),
                             ("#50625d", "#fffef9"), ("#ffffff", "#17635f"),
                             ("#ffffff", "#124e4b"), ("#193432", "#e7ede5"),
                             ("#193432", "#d4dfd7"), ("#50625d", "#e7ede5"),
                             ("#27643e", "#fffef9"), ("#983c34", "#fffef9"),
                             ("#76500a", "#fffef9")]:
        light, dark = sorted([luminance(text), luminance(background)], reverse=True)
        assert (light + 0.05) / (dark + 0.05) >= 4.5


def test_unavailable_locale_defaults_to_english(monkeypatch):
    monkeypatch.setattr(starter.locale, "getlocale", MagicMock(side_effect=ValueError("locale")))
    assert starter.default_language() == "en"


def test_probe_worker_only_queues_results_and_poll_is_single_flight(window, monkeypatch):
    child = Child()
    window.lifecycle.attach(child, 8000)
    probe = MagicMock(return_value=True)
    monkeypatch.setattr(starter, "check_server_ready", probe)
    window._probe(child, 8000, window.lifecycle.generation)
    probe.assert_called_once_with(child, 8000)
    assert window.lifecycle.state == "starting"
    # Consuming on the UI thread is what changes readiness.
    monkeypatch.setattr(starter.sys, "argv", ["starter", "--no-browser"])
    window._consume_events()
    assert window.lifecycle.can_open
    thread = MagicMock()
    monkeypatch.setattr(starter.threading, "Thread", thread)
    window.next_probe = 0.0
    window._poll()
    window._poll()
    thread.assert_called_once()
    window.closed = True
    window._poll()
    thread.assert_called_once()


def test_resize_reflows_long_translated_text(window):
    event = MagicMock(widget=window.root, width=800)
    window._resize_text(event)
    window.detail_label.configure.assert_called_with(wraplength=700)
    window.footer.configure.assert_called_with(wraplength=700)


def test_x_without_child_closes_and_x_during_stop_does_not_prompt_again(window, monkeypatch):
    ask = MagicMock()
    monkeypatch.setattr(starter.messagebox, "askyesno", ask)
    window.lifecycle.attach(Child(terminate_stops=False), 8000)
    window.lifecycle.begin_stop()
    window.on_exit()
    ask.assert_not_called()
    window.lifecycle.process.alive = False
    window.lifecycle.tick()
    window.on_exit()
    window.root.destroy.assert_called_once()


def test_empty_address_does_not_touch_clipboard(window):
    window.copy_url()
    window.root.clipboard_clear.assert_not_called()


def test_stopped_lifecycle_has_no_probe_or_stop_side_effects(model):
    lifecycle, _ = model
    lifecycle.tick()
    lifecycle.begin_stop()
    assert lifecycle.state == "stopped" and not lifecycle.should_probe


def test_probe_deadline_shutdown_race_is_safe(connection):
    assert utils.check_server_ready(Child(), 8000)
    connection.sock.shutdown.side_effect = OSError("closed")
    connection.timer_factory.call_args.args[1]()


def test_null_writer_and_windowed_stream_setup(monkeypatch):
    writer = utils.NullWriter()
    assert writer.write("synthetic") is None
    assert writer.flush() is None
    assert not writer.isatty()
    monkeypatch.setattr(utils.sys, "stdout", None)
    monkeypatch.setattr(utils.sys, "stderr", None)
    utils.setup_frozen_logging()
    assert isinstance(utils.sys.stdout, utils.NullWriter)
    assert isinstance(utils.sys.stderr, utils.NullWriter)


def test_log_failure_does_not_break_lifecycle(monkeypatch):
    monkeypatch.setattr("builtins.open", MagicMock(side_effect=OSError("read only")))
    starter.log_message("synthetic")


def test_log_success_writes_only_requested_message(monkeypatch):
    stream = MagicMock()
    monkeypatch.setattr("builtins.open", MagicMock(return_value=stream))
    starter.log_message("synthetic status")
    assert "synthetic status" in stream.__enter__.return_value.write.call_args.args[0]


@pytest.mark.parametrize("gui_available,gui_failure", [(False, False), (True, True), (True, False)])
def test_main_native_and_console_dispatch(monkeypatch, gui_available, gui_failure):
    monkeypatch.setattr(starter, "setup_frozen_working_directory", MagicMock())
    monkeypatch.setattr(starter, "setup_frozen_logging", MagicMock())
    monkeypatch.setattr(starter, "log_message", MagicMock())
    monkeypatch.setattr(starter.multiprocessing, "freeze_support", MagicMock())
    monkeypatch.setattr(starter, "GUI_AVAILABLE", gui_available)
    monkeypatch.setattr(starter.sys, "argv", ["starter"])
    gui = MagicMock()
    if gui_failure:
        gui.side_effect = starter.tk.TclError("no display")
    monkeypatch.setattr(starter, "ServerControlWindow", gui)
    console = MagicMock(return_value=2)
    monkeypatch.setattr(starter, "run_console", console)
    assert starter.main() == (0 if gui_available and not gui_failure else 2)
    if gui_available and not gui_failure:
        gui.return_value.run.assert_called_once()
        console.assert_not_called()
    else:
        console.assert_called_once()


def test_console_start_error_returns_failure_without_opening(monkeypatch):
    monkeypatch.setattr(starter, "find_free_port", MagicMock(side_effect=OSError("busy")))
    assert starter.run_console() == 1


@pytest.mark.parametrize("browser_error", [False, OSError("no browser")])
def test_console_browser_failure_does_not_claim_success(monkeypatch, capsys, browser_error):
    child = Child()
    child.start = MagicMock()
    monkeypatch.setattr(starter.multiprocessing, "Process", MagicMock(return_value=child))
    monkeypatch.setattr(starter, "wait_for_server", lambda *a: True)
    monkeypatch.setattr(starter, "default_language", lambda: "en")
    monkeypatch.setattr(starter.sys, "argv", ["starter"])
    browser = MagicMock(return_value=False)
    if browser_error:
        browser.side_effect = browser_error
    monkeypatch.setattr(starter.webbrowser, "open", browser)
    monkeypatch.setattr(starter.time, "sleep", lambda _: setattr(child, "alive", False))
    monkeypatch.setattr(starter, "stop_owned_process", lambda _: False)
    assert starter.run_console(port=8000) == 1
    output = capsys.readouterr().out
    assert "browser could not be opened" in output
    assert "server has not stopped" in output


def test_console_occupied_fixed_port_does_not_spawn_or_accept_other_server(monkeypatch):
    monkeypatch.setattr(starter, "check_port_available", lambda _: False)
    process = MagicMock()
    monkeypatch.setattr(starter.multiprocessing, "Process", process)
    probe = MagicMock()
    monkeypatch.setattr(starter, "wait_for_server", probe)
    assert starter.run_console(port=8000, no_browser=True) == 1
    process.assert_not_called()
    probe.assert_not_called()


def test_poll_and_start_after_close_do_nothing(window):
    window.closed = True
    window.start_server()
    window._poll()
    assert window.lifecycle.process is None


def test_run_uses_native_event_loop(window):
    window.run()
    window.root.mainloop.assert_called_once()


def test_queued_browser_launch_after_stop_never_opens(window, monkeypatch):
    browser = MagicMock()
    monkeypatch.setattr(starter.webbrowser, "open", browser)
    window.lifecycle.attach(Child(), 8000)
    window.lifecycle.apply_probe(window.lifecycle.generation, True)
    old_generation = window.lifecycle.generation
    window.lifecycle.begin_stop()
    window._launch_browser(window.lifecycle.url, old_generation)
    browser.assert_not_called()


def test_console_rechecks_liveness_immediately_before_announcing_ready(monkeypatch, capsys):
    child = Child(alive=False)
    child.start = MagicMock()
    monkeypatch.setattr(starter.multiprocessing, "Process", MagicMock(return_value=child))
    monkeypatch.setattr(starter, "wait_for_server", lambda *a: True)
    monkeypatch.setattr(starter, "default_language", lambda: "en")
    browser = MagicMock()
    monkeypatch.setattr(starter.webbrowser, "open", browser)
    monkeypatch.setattr(starter, "stop_owned_process", lambda _: True)
    assert starter.run_console(port=8000) == 1
    browser.assert_not_called()
    assert "Local server ready:" not in capsys.readouterr().out
