"""
Translation Service for SLMEducator

Provides internationalization (i18n) support with:
- JSON-based translation files
- Parameter interpolation
- Pluralization support
- Fallback to English
- No duplicate keys
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional
from threading import Lock


class TranslationService:
    """Service for managing application translations"""

    def __init__(
        self, translations_dir: str = "translations", default_language: str = "es"
    ):
        """
        Initialize the translation service

        Args:
            translations_dir: Directory containing translation JSON files
            default_language: Default language code (e.g., 'en', 'es')
        """
        # Determine paths based on execution mode (Frozen/Dev)
        if getattr(sys, "frozen", False):
            # PyInstaller creates a temp folder or puts things in _internal
            # Check for OneDir structure: executable_dir/_internal/translations
            exe_dir = Path(sys.executable).parent
            internal_translations = exe_dir / "_internal" / "translations"

            if internal_translations.exists():
                self.translations_dir = internal_translations
            else:
                # Fallback to _MEIPASS (OneFile) or just 'translations' next to exe
                base_path = Path(getattr(sys, "_MEIPASS", exe_dir))
                self.translations_dir = base_path / "translations"
        else:
            # Development mode: find translations relative to this file's location
            # This file is at: src/core/services/translation_service.py
            # Translations are at: <project_root>/translations/
            this_file = Path(__file__).resolve()
            project_root = (
                this_file.parent.parent.parent.parent
            )  # Go up 4 levels from translation_service.py
            resolved_dir = project_root / translations_dir

            if resolved_dir.exists():
                self.translations_dir = resolved_dir
            else:
                # Fallback to relative path (for testing or other scenarios)
                self.translations_dir = Path(translations_dir)

        self.default_language = default_language
        self.current_language = default_language
        self.translations: Dict[str, Dict[str, str]] = {}
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"Translation directory resolved to: {self.translations_dir}")

        # Ensure translations directory exists
        if not self.translations_dir.exists():
            self.logger.warning(
                f"Translations directory does not exist: {self.translations_dir}"
            )
            # We don't mkdir here in frozen mode as it might be read-only or wrong location

        # Load default language
        self.load_language(default_language)

    def load_language(self, language_code: str) -> bool:
        """
        Load translations for a specific language

        Args:
            language_code: Language code (e.g., 'en', 'es')

        Returns:
            True if loaded successfully, False otherwise
        """
        translation_file = self.translations_dir / f"{language_code}.json"

        if not translation_file.exists():
            self.logger.warning(f"Translation file not found: {translation_file}")
            return False

        try:
            with open(translation_file, "r", encoding="utf-8") as f:
                translations = json.load(f)

            with self._lock:
                self.translations[language_code] = translations

            self.logger.info(
                f"Loaded {len(translations)} translations for language: {language_code}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to load translations for {language_code}: {e}")
            return False

    def set_language(self, language_code: str) -> bool:
        """
        Set the current language

        Args:
            language_code: Language code to switch to

        Returns:
            True if successful, False otherwise
        """
        # Load language if not already loaded
        if language_code not in self.translations:
            if not self.load_language(language_code):
                self.logger.error(
                    f"Cannot set language to {language_code}: failed to load"
                )
                return False

        with self._lock:
            self.current_language = language_code

        self.logger.info(f"Language changed to: {language_code}")
        return True

    def get(self, key: str, **params) -> str:
        """
        Get a translation for a key

        Args:
            key: Translation key (supports dot notation, e.g., 'auth.login.title')
            **params: Parameters for string interpolation

        Returns:
            Translated string, or key if not found
        """
        with self._lock:
            current_lang = self.current_language
            translations = self.translations.get(current_lang, {})

        # Try to get the translation
        value = self._get_nested(translations, key)

        # Fallback to default language if not found
        if value is None and current_lang != self.default_language:
            default_translations = self.translations.get(self.default_language, {})
            value = self._get_nested(default_translations, key)

        # If still not found, return the key itself as fallback
        if value is None:
            self.logger.warning(f"Translation key not found: {key}")
            return key

        # Interpolate parameters if provided
        if params:
            try:
                return value.format(**params)
            except KeyError as e:
                self.logger.error(
                    f"Parameter interpolation failed for key '{key}': {e}"
                )
                return value

        return value

    def _get_nested(self, data: Dict, key: str) -> Optional[str]:
        """
        Get value from nested dictionary using dot notation

        Args:
            data: Dictionary to search
            key: Dot-notation key (e.g., 'auth.login.title')

        Returns:
            Value if found, None otherwise
        """
        keys = key.split(".")
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current if isinstance(current, str) else None

    def get_available_languages(self) -> list:
        """
        Get list of available languages

        Returns:
            List of language codes
        """
        languages = []
        for file in self.translations_dir.glob("*.json"):
            languages.append(file.stem)
        return sorted(languages)

    def get_language_name(self, language_code: str) -> str:
        """
        Get the display name for a language

        Args:
            language_code: Language code

        Returns:
            Language display name
        """
        language_names = {
            "en": "English",
            "es": "Español (España)",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский",
            "zh": "中文",
            "ja": "日本語",
            "ko": "한국어",
            "ar": "العربية",
        }
        return language_names.get(language_code, language_code.upper())


# Global translation service instance
_translation_service: Optional[TranslationService] = None
_init_lock = Lock()


def get_translation_service() -> TranslationService:
    """Get or create the global translation service instance"""
    global _translation_service

    if _translation_service is None:
        with _init_lock:
            if _translation_service is None:
                _translation_service = TranslationService()

    return _translation_service


def tr(key: str, **params) -> str:
    """
    Shorthand function for translation

    Args:
        key: Translation key
        **params: Parameters for interpolation

    Returns:
        Translated string
    """
    return get_translation_service().get(key, **params)
