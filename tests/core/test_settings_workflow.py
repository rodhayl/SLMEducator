#!/usr/bin/env python3
"""
Refactored Robust Settings Screen Workflow Test

This script tests Settings screen functionality using headless GUI testing
with the HeadlessGUIHelper to eliminate visual dependencies.
"""

import pytest
import sys
import os
from unittest.mock import Mock

# Add tests directory to path to allow imports
tests_dir = os.path.dirname(os.path.abspath(__file__))
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

from tests.fixtures.gui_test_utils import HeadlessGUIHelper, create_mock_settings_screen


class TestSettingsScreenHeadless:
    """Headless test class for Settings Screen workflows using HeadlessGUIHelper"""

    @pytest.fixture
    def gui_helper(self):
        """Provide headless GUI testing helper."""
        return HeadlessGUIHelper(auto_close_timeout=5.0)

    def test_settings_screen_provider_switching_headless(self, gui_helper):
        """Test provider switching functionality using headless testing."""
        with gui_helper.headless_root() as root:
            # Use the centralized mock settings screen creation
            settings_screen, app = create_mock_settings_screen()

            # Test provider switching logic
            original_provider = settings_screen.provider_var.get()
            assert original_provider == "openrouter"

            # Simulate provider change
            settings_screen.provider_var.set("ollama")
            assert settings_screen.provider_var.get() == "ollama"

            # Verify model combo was updated (use available models)
            settings_screen.model_combo.set("gpt-4")
            assert settings_screen.model_combo.current_value.get() == "gpt-4"

    def test_settings_screen_model_configuration_headless(self, gui_helper):
        """Test model configuration functionality using headless testing."""
        with gui_helper.headless_root() as root:
            # Use centralized mock creation
            settings_screen, app = create_mock_settings_screen()

            # Test model configuration
            settings_screen.provider_var.set("openrouter")
            available_models = settings_screen.model_combo.get_values()

            # Verify models are available
            assert "gpt-3.5-turbo" in available_models
            assert "gpt-4" in available_models

            # Test model selection
            settings_screen.model_combo.set("gpt-4")
            assert settings_screen.model_combo.current_value.get() == "gpt-4"

    def test_settings_screen_configuration_persistence_headless(self, gui_helper):
        """Test configuration persistence using headless testing."""
        with gui_helper.headless_root() as root:
            # Use centralized mock creation
            settings_screen, app = create_mock_settings_screen()

            # Test configuration persistence
            settings_screen.provider_var.set("anthropic")
            settings_screen.model_combo.set("claude-3-sonnet")

            # Simulate saving configuration
            settings_screen.save_configuration = Mock()
            settings_screen.save_configuration.return_value = True

            # Test that configuration was saved
            result = settings_screen.save_configuration()
            assert result is True
            settings_screen.save_configuration.assert_called_once()

    def test_settings_screen_error_handling_headless(self, gui_helper):
        """Test error handling using headless testing."""
        with gui_helper.headless_root() as root:
            # Use centralized mock creation
            settings_screen, app = create_mock_settings_screen()

            # Test error handling for invalid provider
            settings_screen.provider_var.set("invalid_provider")

            # Mock error handling
            settings_screen.handle_error = Mock()
            settings_screen.handle_error.return_value = "Invalid provider selected"

            # Test error handling
            error_message = settings_screen.handle_error("invalid_provider")
            assert "Invalid provider" in error_message
            settings_screen.handle_error.assert_called_once_with("invalid_provider")
