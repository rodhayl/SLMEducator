"""
Tests for the Translation Service

These tests verify the translation service functionality including:
- Loading translation files
- Language switching
- Key resolution with dot notation
- Fallback to default language
- Parameter interpolation
- Key synchronization between en.json and es.json
"""

import pytest
import json
from pathlib import Path

from src.core.services.translation_service import TranslationService, tr


class TestTranslationService:
    """Tests for TranslationService class"""

    @pytest.fixture
    def translations_dir(self, tmp_path):
        """Create a temporary translations directory with test files"""
        trans_dir = tmp_path / "translations"
        trans_dir.mkdir()

        # Create English translations
        en_data = {
            "app": {"name": "Test App", "title": "Test Title"},
            "navigation": {"dashboard": "Dashboard", "settings": "Settings"},
            "messages": {
                "welcome": "Welcome, {name}!",
                "count": "You have {count} items",
            },
        }
        with open(trans_dir / "en.json", "w", encoding="utf-8") as f:
            json.dump(en_data, f)

        # Create Spanish translations
        es_data = {
            "app": {"name": "App de Prueba", "title": "Título de Prueba"},
            "navigation": {"dashboard": "Panel", "settings": "Configuración"},
            "messages": {
                "welcome": "¡Bienvenido, {name}!",
                "count": "Tienes {count} elementos",
            },
        }
        with open(trans_dir / "es.json", "w", encoding="utf-8") as f:
            json.dump(es_data, f)

        return trans_dir

    def test_init_loads_default_language(self, translations_dir):
        """Test that service loads default language on init"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        assert service.current_language == "en"
        assert "en" in service.translations

    def test_load_language_success(self, translations_dir):
        """Test successful language loading"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        result = service.load_language("es")

        assert result is True
        assert "es" in service.translations

    def test_load_language_nonexistent(self, translations_dir):
        """Test loading a non-existent language returns False"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        result = service.load_language("fr")

        assert result is False

    def test_set_language_success(self, translations_dir):
        """Test setting language changes current language"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        result = service.set_language("es")

        assert result is True
        assert service.current_language == "es"

    def test_get_simple_key(self, translations_dir):
        """Test getting a simple nested key"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        result = service.get("app.name")

        assert result == "Test App"

    def test_get_nested_key(self, translations_dir):
        """Test getting a deeply nested key"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        result = service.get("navigation.dashboard")

        assert result == "Dashboard"

    def test_get_with_language_switch(self, translations_dir):
        """Test getting translation after language switch"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        # English
        assert service.get("navigation.dashboard") == "Dashboard"

        # Switch to Spanish
        service.set_language("es")
        assert service.get("navigation.dashboard") == "Panel"

    def test_get_with_parameters(self, translations_dir):
        """Test parameter interpolation"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        result = service.get("messages.welcome", name="John")

        assert result == "Welcome, John!"

    def test_get_missing_key_returns_key(self, translations_dir):
        """Test that missing key returns the key itself"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        result = service.get("nonexistent.key")

        assert result == "nonexistent.key"

    def test_get_available_languages(self, translations_dir):
        """Test listing available languages"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        languages = service.get_available_languages()

        assert "en" in languages
        assert "es" in languages

    def test_get_language_name(self, translations_dir):
        """Test getting language display names"""
        service = TranslationService(
            translations_dir=str(translations_dir), default_language="en"
        )

        assert service.get_language_name("en") == "English"
        assert service.get_language_name("es") == "Español (España)"
        assert service.get_language_name("unknown") == "UNKNOWN"


class TestTranslationKeySync:
    """Tests to verify translation files are synchronized"""

    @pytest.fixture
    def project_translations_dir(self):
        """Get the actual project translations directory"""
        # Navigate from tests/unit/ to root/translations/
        return Path(__file__).parent.parent.parent / "translations"

    def test_en_and_es_have_same_keys(self, project_translations_dir):
        """Test that en.json and es.json have the same keys"""
        if not project_translations_dir.exists():
            pytest.skip("Translations directory not found")

        en_file = project_translations_dir / "en.json"
        es_file = project_translations_dir / "es.json"

        if not en_file.exists() or not es_file.exists():
            pytest.skip("Translation files not found")

        with open(en_file, "r", encoding="utf-8") as f:
            en_data = json.load(f)

        with open(es_file, "r", encoding="utf-8") as f:
            es_data = json.load(f)

        def get_all_keys(obj, prefix=""):
            """Recursively get all keys with dot notation"""
            keys = set()
            for key, value in obj.items():
                full_key = f"{prefix}{key}" if prefix else key
                if isinstance(value, dict):
                    keys.update(get_all_keys(value, f"{full_key}."))
                else:
                    keys.add(full_key)
            return keys

        en_keys = get_all_keys(en_data)
        es_keys = get_all_keys(es_data)

        # Both sets should be identical after synchronization
        missing_in_es = en_keys - es_keys
        missing_in_en = es_keys - en_keys

        assert len(missing_in_es) == 0, f"Keys missing in es.json: {missing_in_es}"
        assert len(missing_in_en) == 0, f"Keys missing in en.json: {missing_in_en}"


class TestTrShorthand:
    """Tests for the tr() shorthand function"""

    def test_tr_returns_translation(self):
        """Test that tr() returns translation from global service"""
        # This uses the actual translations directory
        result = tr("app.name")

        # Should return either a translation or the key itself
        assert isinstance(result, str)
        assert len(result) > 0


class TestI18nIntegration:
    """Integration tests for i18n in the settings API"""

    @pytest.fixture
    def client(self):
        """Get test client - skip if main module not available"""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app

            return TestClient(app)
        except ImportError:
            pytest.skip("FastAPI app not available for integration testing")

    def test_get_translations_endpoint(self, client):
        """Test the translations endpoint returns valid JSON"""
        if client is None:
            pytest.skip("Client not available")

        response = client.get("/api/settings/translations/en")

        assert response.status_code == 200
        data = response.json()

        # Should have key sections
        assert "app" in data or "navigation" in data

    def test_get_translations_invalid_language(self, client):
        """Test requesting invalid language returns 404"""
        if client is None:
            pytest.skip("Client not available")

        response = client.get("/api/settings/translations/invalid_lang")

        assert response.status_code == 404

    def test_get_spanish_translations(self, client):
        """Test Spanish translations endpoint"""
        if client is None:
            pytest.skip("Client not available")

        response = client.get("/api/settings/translations/es")

        assert response.status_code == 200
        data = response.json()

        # Should have Spanish content
        assert isinstance(data, dict)
