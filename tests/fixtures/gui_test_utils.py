"""
Headless GUI Testing Utilities
Provides mock classes and helpers for testing GUI components without actual GUI
"""

from unittest.mock import Mock
from typing import Any, Optional


class HeadlessGUIHelper:
    """Helper for headless GUI testing"""

    def __init__(self, **kwargs):
        """Initialize with any kwargs to make it compatible with all tests"""
        self.widgets = {}
        self.events = []
        # Store any kwargs as attributes for flexibility
        for key, value in kwargs.items():
            setattr(self, key, value)

    def create_widget(self, widget_type: str, **kwargs) -> Mock:
        """Create a mock widget"""
        widget = Mock()
        widget.configure = Mock()
        widget.pack = Mock()
        widget.grid = Mock()
        widget.place = Mock()
        for key, value in kwargs.items():
            setattr(widget, key, value)
        return widget

    def click(self, widget: Any) -> None:
        """Simulate a click event"""
        if hasattr(widget, "command") and callable(widget.command):
            widget.command()
        self.events.append(("click", widget))

    def set_text(self, widget: Any, text: str) -> None:
        """Set text in a widget"""
        if hasattr(widget, "set"):
            widget.set(text)
        elif hasattr(widget, "insert"):
            widget.insert(0, text)
        self.events.append(("set_text", widget, text))

    def get_text(self, widget: Any) -> str:
        """Get text from a widget"""
        if hasattr(widget, "get"):
            return widget.get()
        return ""

    def headless_root(self):
        """Context manager for headless root window"""
        return mock_gui_environment()


class MockApp:
    """Mock application for testing"""

    def __init__(self):
        self.db_service = Mock()
        self.auth_service = Mock()
        self.ai_service = Mock()
        self.logger = Mock()
        self.current_user = None
        self.windows = []

    def show_message(self, title: str, message: str) -> None:
        """Mock show message"""

    def show_error(self, title: str, message: str) -> None:
        """Mock show error"""


def mock_gui_environment():
    """Context manager for mocking GUI environment"""

    class MockGUIEnvironment:
        def __init__(self):
            self.tk_root = Mock()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    return MockGUIEnvironment()


def gui_helper() -> HeadlessGUIHelper:
    """Factory function for GUI helper"""
    return HeadlessGUIHelper()


class MockVar:
    """Mock variable that maintains state"""

    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def create_mock_settings_screen(app: Optional[MockApp] = None) -> tuple:
    """Create a mock settings screen"""
    if app is None:
        app = MockApp()
    screen = Mock()
    screen.app = app

    # Use MockVar for stateful variables
    screen.provider_var = MockVar("openrouter")
    screen.model_var = MockVar("gpt-4")
    screen.api_key_var = MockVar("sk-test")
    screen.endpoint_var = MockVar("https://api.test.com")

    # Mock combo box
    screen.model_combo = Mock()
    screen.model_combo.current_value = MockVar("gpt-4")
    screen.model_combo.set = lambda v: screen.model_combo.current_value.set(v)
    screen.model_combo.get_values = Mock(
        return_value=["gpt-3.5-turbo", "gpt-4", "claude-3-opus"]
    )

    screen.save = Mock()
    screen.load_settings = Mock()
    screen.test_connection = Mock()
    return screen, app
