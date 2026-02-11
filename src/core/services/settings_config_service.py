"""
Settings Configuration Service for SLMEducator

This module provides centralized configuration management using properties files.
It handles loading, parsing, and providing access to application settings.

Configuration files:
- env.properties: Production configuration (default)
- env-test.properties: Test configuration (used when SLM_TEST_MODE=1)
- settings.properties: Legacy fallback (deprecated)
"""

import os
import configparser
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union


def get_config_file_path() -> str:
    """
    Determine the appropriate configuration file based on environment.

    Priority:
    1. SLM_CONFIG_FILE environment variable (explicit override)
    2. env-test.properties (when SLM_TEST_MODE=1)
    3. env.properties (production default)
    4. settings.properties (legacy fallback)
    """
    # Check for explicit override
    explicit_config = os.environ.get("SLM_CONFIG_FILE")
    if explicit_config and os.path.exists(explicit_config):
        return explicit_config

    # Find project root (where env.properties should be)
    # Try current directory first, then look for common project markers
    search_paths = [
        Path.cwd(),
        Path(
            __file__
        ).parent.parent.parent.parent,  # From src/core/services/ to project root
    ]

    for base_path in search_paths:
        # Check for test mode
        if os.environ.get("SLM_TEST_MODE") == "1":
            test_config = base_path / "env-test.properties"
            if test_config.exists():
                return str(test_config)

        # Check for production config
        prod_config = base_path / "env.properties"
        if prod_config.exists():
            return str(prod_config)

        # Legacy fallback
        legacy_config = base_path / "settings.properties"
        if legacy_config.exists():
            return str(legacy_config)

    # Default to env.properties in current directory
    return "env.properties"


class SettingsConfigService:
    """Service for managing application settings from properties files."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the settings configuration service.

        Args:
            config_file: Optional path to config file. If None, auto-detects based on environment.
        """
        self.config_file = config_file or get_config_file_path()
        self.config = configparser.ConfigParser()
        self.logger = logging.getLogger(__name__)
        self._load_config()

    def _load_config(self):
        """Load configuration from properties file."""
        try:
            # Check if config file exists
            if not os.path.exists(self.config_file):
                self.logger.warning(
                    f"Config file {self.config_file} not found, using defaults"
                )
                self._create_default_config()
                return

            # Read the properties file
            self.config.read(self.config_file, encoding="utf-8")
            self.logger.info(f"Configuration loaded from {self.config_file}")

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration if file doesn't exist."""
        # Create default configuration
        self.config.add_section("ai")

        # Ollama configuration (default provider)
        self.config.set("ai", "ollama.url", "http://localhost:11434")
        self.config.set("ai", "ollama.api_key", "")
        self.config.set("ai", "ollama.model", "gpt-oss")
        self.config.set("ai", "default_provider", "ollama")
        self.config.set("ai", "default_model", "gpt-oss")

        # OpenRouter configuration (backup)
        self.config.set(
            "ai", "openrouter.url", "https://openrouter.ai/api/v1/chat/completions"
        )
        self.config.set("ai", "openrouter.api_key", "")
        self.config.set("ai", "openrouter.model", "x-ai/grok-4.1-fast")

        # Other AI providers
        self.config.set("ai", "lm_studio.url", "http://localhost:1234")
        self.config.set("ai", "openai.url", "https://api.openai.com")
        self.config.set("ai", "anthropic.url", "https://api.anthropic.com")
        self.config.set("ai", "openai.endpoint", "https://api.openai.com/v1")
        self.config.set("ai", "default_temperature", "0.7")
        self.config.set("ai", "default_max_tokens", "1000")
        self.config.set("ai", "temperature.min", "0.0")
        self.config.set("ai", "temperature.max", "1.0")
        self.config.set("ai", "max_tokens.min", "100")
        self.config.set("ai", "max_tokens.max", "4000")

        self.config.add_section("logging")
        self.config.set("logging", "default_level", "INFO")
        self.config.set("logging", "max_file_size_mb", "10")
        self.config.set("logging", "backup_count", "5")
        self.config.set("logging", "levels", "DEBUG,INFO,WARNING,ERROR,CRITICAL")

        self.config.add_section("ui")
        self.config.set("ui", "default_theme", "auto")
        self.config.set("ui", "themes", "light,dark,auto")
        self.config.set("ui", "default_font_size", "medium")
        self.config.set("ui", "font_sizes", "small,medium,large")
        self.config.set("ui", "auto_save", "true")
        self.config.set("ui", "cache_size_mb", "100")

        self.config.add_section("export")
        self.config.set("export", "default_format", "json")
        self.config.set("export", "formats", "json,zip")
        self.config.set("export", "default_study_plans", "true")
        self.config.set("export", "default_assessments", "true")
        self.config.set("export", "default_content", "true")
        self.config.set("export", "default_analytics", "false")

        self.config.add_section("cleanup")
        self.config.set("cleanup", "old_sessions.enabled", "true")
        self.config.set("cleanup", "old_logs.enabled", "false")
        self.config.set("cleanup", "unused_content.enabled", "false")
        self.config.set("cleanup", "old_sessions.age_days", "365")
        self.config.set("cleanup", "old_logs.age_days", "180")

        self.config.add_section("database")
        self.config.set("database", "url", "sqlite:///slm_educator.db")
        self.config.set("database", "echo", "false")

        self.config.add_section("security")
        self.config.set("security", "password_min_length", "8")
        self.config.set("security", "max_login_attempts", "5")
        self.config.set("security", "account_lockout_duration_minutes", "30")

        self.config.add_section("paths")
        self.config.set("paths", "logs", "logs")
        self.config.set("paths", "data", "data")
        self.config.set("paths", "exports", "exports")
        self.config.set("paths", "imports", "imports")

        self.config.add_section("performance")
        self.config.set("performance", "cache_enabled", "true")
        self.config.set("performance", "cache_size_mb", "100")
        self.config.set("performance", "cache_ttl_seconds", "3600")

        # Save the default configuration
        self.save_config()

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.config.write(f)
            self.logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")

    def get(self, section: str, key: str, fallback: Optional[str] = None) -> str:
        """Get a configuration value."""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            self.logger.warning(f"Configuration not found: {section}.{key}")
            return ""

    def getint(self, section: str, key: str, fallback: Optional[int] = None) -> int:
        """Get an integer configuration value."""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            if fallback is not None:
                return fallback
            self.logger.warning(f"Integer configuration not found: {section}.{key}")
            return 0

    def getfloat(
        self, section: str, key: str, fallback: Optional[float] = None
    ) -> float:
        """Get a float configuration value."""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            if fallback is not None:
                return fallback
            self.logger.warning(f"Float configuration not found: {section}.{key}")
            return 0.0

    def getboolean(
        self, section: str, key: str, fallback: Optional[bool] = None
    ) -> bool:
        """Get a boolean configuration value."""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            if fallback is not None:
                return fallback
            self.logger.warning(f"Boolean configuration not found: {section}.{key}")
            return False

    def get_list(self, section: str, key: str, fallback: Optional[list] = None) -> list:
        """Get a list configuration value (comma-separated)."""
        value = self.get(section, key)
        if value:
            return [item.strip() for item in value.split(",")]
        return fallback or []

    def set(self, section: str, key: str, value: Union[str, int, float, bool]):
        """Set a configuration value."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))

    def get_ai_config_defaults(self) -> Dict[str, Any]:
        """Get AI configuration defaults with environment variable override."""
        # Check for environment variable override
        ai_provider = os.environ.get("AI_PROVIDER", self.get("ai", "default_provider"))

        # Get base configuration
        config = {
            "ollama_url": self.get("ai", "ollama.url"),
            "lm_studio_url": self.get("ai", "lm_studio.url"),
            "openai_url": self.get("ai", "openai.url"),
            "anthropic_url": self.get("ai", "anthropic.url"),
            "openrouter_url": self.get("ai", "openrouter.url"),
            "openrouter_api_key": self.get("ai", "openrouter.api_key"),
            "openrouter_model": self.get("ai", "openrouter.model"),
            "openai_endpoint": self.get("ai", "openai.endpoint"),
            "default_provider": ai_provider,
            "default_model": self.get("ai", "default_model"),
            "default_temperature": self.getfloat("ai", "default_temperature"),
            "default_max_tokens": self.getint("ai", "default_max_tokens"),
            "temperature_min": self.getfloat("ai", "temperature.min"),
            "temperature_max": self.getfloat("ai", "temperature.max"),
            "max_tokens_min": self.getint("ai", "max_tokens.min"),
            "max_tokens_max": self.getint("ai", "max_tokens.max"),
            "preprocessing_model": self.get("ai", "preprocessing_model"),
            "enable_preprocessing": self.getboolean(
                "ai", "enable_preprocessing", False
            ),
        }

        # Override model based on provider if using environment variable
        if ai_provider == "openrouter":
            config["default_model"] = self.get("ai", "openrouter.model")
        elif ai_provider == "ollama":
            # Prefer explicit ollama.model setting; fall back to 'gpt-oss' if not set
            ollama_model = self.get("ai", "ollama.model")
            config["default_model"] = ollama_model if ollama_model else "gpt-oss"

        return config

    def get_logging_defaults(self) -> Dict[str, Any]:
        """Get logging configuration defaults."""
        return {
            "default_level": self.get("logging", "default_level"),
            "max_file_size_mb": self.getint("logging", "max_file_size_mb"),
            "backup_count": self.getint("logging", "backup_count"),
            "levels": self.get_list("logging", "levels"),
        }

    def get_ui_defaults(self) -> Dict[str, Any]:
        """Get UI configuration defaults."""
        return {
            "default_theme": self.get("ui", "default_theme"),
            "themes": self.get_list("ui", "themes"),
            "default_font_size": self.get("ui", "default_font_size"),
            "font_sizes": self.get_list("ui", "font_sizes"),
            "auto_save": self.getboolean("ui", "auto_save"),
            "cache_size_mb": self.getint("ui", "cache_size_mb"),
        }

    def get_export_defaults(self) -> Dict[str, Any]:
        """Get export configuration defaults."""
        return {
            "default_format": self.get("export", "default_format"),
            "formats": self.get_list("export", "formats"),
            "default_study_plans": self.getboolean("export", "default_study_plans"),
            "default_assessments": self.getboolean("export", "default_assessments"),
            "default_content": self.getboolean("export", "default_content"),
            "default_analytics": self.getboolean("export", "default_analytics"),
        }


# Global instance
_settings_service = None


def get_settings_service(config_file: Optional[str] = None) -> SettingsConfigService:
    """
    Get the global settings service instance.

    Args:
        config_file: Optional path to config file. If None, auto-detects:
                    - env-test.properties when SLM_TEST_MODE=1
                    - env.properties for production
                    - settings.properties as legacy fallback

    Returns:
        SettingsConfigService instance
    """
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsConfigService(config_file)
    return _settings_service


def reset_settings_service():
    """Reset the global settings service instance. Useful for testing."""
    global _settings_service
    _settings_service = None
