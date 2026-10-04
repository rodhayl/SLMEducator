"""Disposable public configuration defaults, typed access and failure recovery."""

import pytest

from src.core.services.settings_config_service import SettingsConfigService


def test_missing_config_creates_public_defaults_and_roundtrips(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    path = tmp_path / "synthetic.properties"
    settings = SettingsConfigService(str(path))
    assert path.is_file()
    defaults = settings.get_ai_config_defaults()
    assert defaults["default_provider"] == "ollama"
    assert defaults["default_max_tokens"] == 1000
    assert defaults["default_temperature"] == 0.7
    assert defaults["openai_endpoint"].endswith("/v1/chat/completions")
    assert settings.get_logging_defaults()["backup_count"] == 5
    assert settings.get_ui_defaults()["themes"] == ["light", "dark", "auto"]
    assert settings.get_export_defaults()["default_analytics"] is False
    settings.set("synthetic", "enabled", True)
    settings.set("synthetic", "limit", 123)
    settings.set("synthetic", "weight", 0.75)
    settings.save_config()
    reloaded = SettingsConfigService(str(path))
    assert reloaded.getboolean("synthetic", "enabled") is True
    assert reloaded.getint("synthetic", "limit") == 123
    assert reloaded.getfloat("synthetic", "weight") == 0.75


@pytest.mark.parametrize(
    "getter,raw,expected",
    [("getint", "invalid", 0), ("getfloat", "invalid", 0.0), ("getboolean", "invalid", False)],
)
def test_invalid_typed_values_use_explicit_fallback(tmp_path, getter, raw, expected):
    settings = SettingsConfigService(str(tmp_path / "synthetic.properties"))
    settings.set("synthetic", "value", raw)
    assert getattr(settings, getter)("synthetic", "value") == expected
    assert getattr(settings, getter)("missing", "value", fallback=7) == 7


def test_missing_text_and_lists_are_explicit(tmp_path):
    settings = SettingsConfigService(str(tmp_path / "synthetic.properties"))
    assert settings.get("missing", "value") == ""
    assert settings.get("missing", "value", "specified") == "specified"
    assert settings.get_list("missing", "value") == []
    assert settings.get_list("missing", "value", ["specified"]) == ["specified"]
    settings.set("synthetic", "list", "alpha, beta")
    assert settings.get_list("synthetic", "list") == ["alpha", "beta"]


@pytest.mark.parametrize(
    "provider,model", [("ollama", "gpt-oss"), ("openrouter", "synthetic-cloud")]
)
def test_provider_override_selects_its_saved_model(tmp_path, monkeypatch, provider, model):
    settings = SettingsConfigService(str(tmp_path / "synthetic.properties"))
    settings.set("ai", "openrouter.model", "synthetic-cloud")
    settings.set("ai", "ollama.model", "")
    monkeypatch.setenv("AI_PROVIDER", provider)
    result = settings.get_ai_config_defaults()
    assert result["default_provider"] == provider and result["default_model"] == model


def test_malformed_existing_config_is_preserved_during_fallback(tmp_path):
    path = tmp_path / "malformed.properties"
    original = "[ai]\ndefault_provider=ollama\nmalformed line\n"
    path.write_text(original)
    settings = SettingsConfigService(str(path))
    assert settings.get_ai_config_defaults()["default_provider"] == "ollama"
    assert path.read_text() == original
    settings.set("ai", "default_provider", "openrouter")
    settings.save_config()
    assert path.read_text() == original
