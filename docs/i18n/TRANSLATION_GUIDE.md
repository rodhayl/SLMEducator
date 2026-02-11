# Translation System Guide

## Overview

SLMEducator uses a JSON-based translation system for internationalization (i18n). This guide explains how to use translations in your code and how to add new languages.

## Architecture

### Components

1. **TranslationService** (`src/core/services/translation_service.py`)
   - Core service that loads and manages translations
   - Supports multiple languages with fallback to English
   - Handles parameter interpolation
   - Thread-safe singleton pattern

2. **UI Helper** (`src/ui/i18n.py`)
   - Convenient `tr()` function for UI components
   - Easy import: `from src.ui.i18n import tr`

3. **Translation Files** (`translations/`)
   - JSON files for each language (`en.json`, `es.json`, etc.)
   - Hierarchical structure using dot notation
   - No duplicates - centralized key-value pairs

## Directory Structure

```
translations/
├── en.json          # English (source language)
├── es.json          # Spanish
├── fr.json          # French (add as needed)
└── ...
```

## Translation File Format

Translation files use JSON with hierarchical keys:

```json
{
  "common": {
    "buttons": {
      "save": "Save",
      "cancel": "Cancel"
    }
  },
  "auth": {
    "login": {
      "title": "Welcome Back",
      "button_signin": "Sign In"
    }
  }
}
```

## Usage

### Basic Translation

```python
from src.ui.i18n import tr

# Simple translation
label = QLabel(tr("common.buttons.save"))  # "Save"

# Another example
title = tr("auth.login.title")  # "Welcome Back"
```

### Translation with Parameters

```python
from src.ui.i18n import tr

# Single parameter
error_msg = tr("common.messages.generic_error", error_msg="Connection failed")
# Result: "An error occurred: Connection failed\n\nPlease try again..."

# Multiple parameters
progress = tr("dashboard.student.sections.progress_template",
              completion=75, completed=15, total=20)
# Result: "Progress: 75% • 15/20 lessons"
```

### Conditional Translations

```python
from src.ui.i18n import tr

# Use conditional logic with translation keys
mode = "create" if is_new else "edit"
title = tr(f"content.editor.title_{mode}")
```

### Changing Language

```python
from src.ui.i18n import set_language, get_current_language

# Change to Spanish
set_language('es')

# Get current language
current = get_current_language()  # Returns 'es'

# Get available languages
from src.ui.i18n import get_available_languages
languages = get_available_languages()  # Returns ['en', 'es', ...]
```

## Translation Key Structure

The English translation file (`translations/en.json`) is organized hierarchically:

### Top-Level Categories

- **`app`** - Application-level strings (name, title)
- **`common`** - Shared across the app (buttons, labels, messages)
- **`auth`** - Authentication screens (login, register)
- **`navigation`** - Navigation menu items
- **`dashboard`** - Dashboard screens (teacher, student)
- **`ai_tutor`** - AI Tutor screen
- **`settings`** - Settings screen
- **`content`** - Content-related screens (library, editor, selection)
- **`study_plans`** - Study plan screens (list, wizard, viewer)
- **`student`** - Student-specific screens (practice, lesson)
- **`dialogs`** - Dialog components
- **`main_app`** - Main application messages

### Example Hierarchy

```
settings
├── title                    # "Settings"
├── tabs
│   ├── general             # "General"
│   ├── ai_config           # "AI Configuration"
│   └── advanced            # "Advanced"
├── general
│   ├── theme_label         # "Theme:"
│   ├── theme_light         # "Light"
│   └── ...
└── save
    ├── button              # "Save Changes"
    ├── success_theme       # Success message with theme
    └── error               # Error message
```

## Adding a New Language

1. **Create a new JSON file** in `translations/` directory:
   ```bash
   cp translations/en.json translations/fr.json
   ```

2. **Translate all values** (keep keys in English):
   ```json
   {
     "common": {
       "buttons": {
         "save": "Enregistrer",    # Translated
         "cancel": "Annuler"        # Translated
       }
     }
   }
   ```

3. **Test the translation**:
   ```python
   from src.ui.i18n import set_language
   set_language('fr')
   ```

4. **The translation file will be automatically detected** by `get_available_languages()`

## Best Practices

### 1. Use Descriptive Keys

❌ **Bad:**
```json
{
  "text1": "Save",
  "msg": "Error occurred"
}
```

✅ **Good:**
```json
{
  "common": {
    "buttons": {
      "save": "Save"
    },
    "messages": {
      "generic_error": "Error occurred"
    }
  }
}
```

### 2. Group Related Strings

✅ **Good organization:**
```json
{
  "auth": {
    "login": {
      "title": "Welcome Back",
      "subtitle": "Sign in to continue",
      "button_signin": "Sign In"
    },
    "register": {
      "title": "Create Account",
      "button_signup": "Sign Up"
    }
  }
}
```

### 3. Use Parameters for Dynamic Content

❌ **Bad:**
```python
message = "Hello, " + username + "!"  # Hard to translate
```

✅ **Good:**
```json
{
  "greetings": {
    "hello_user": "Hello, {username}!"
  }
}
```

```python
message = tr("greetings.hello_user", username=user.name)
```

### 4. Avoid Duplication

If the same text appears in multiple places, create a `common` key:

```json
{
  "common": {
    "buttons": {
      "cancel": "Cancel"  # Reuse everywhere
    }
  }
}
```

Then use: `tr("common.buttons.cancel")` everywhere.

### 5. Keep Placeholders Consistent

Use the same placeholder names across languages:

```json
// en.json
{
  "welcome": "Welcome, {name}!"
}

// es.json
{
  "welcome": "¡Bienvenido, {name}!"
}
```

## Converting Existing Code

### Before (Hardcoded String):
```python
button = QPushButton("Save Changes")
label = QLabel("Username")
message = QMessageBox.information(self, "Success", "Settings saved!")
```

### After (Translated):
```python
from src.ui.i18n import tr

button = QPushButton(tr("common.buttons.save_changes"))
label = QLabel(tr("common.labels.username"))
message = QMessageBox.information(
    self,
    tr("common.labels.success"),
    tr("settings.save.success_basic",
       provider="OpenRouter",
       api_key_status="Set",
       model="gpt-4")
)
```

## Example: Translating a Complete Screen

### Original Code (login_screen.py):
```python
class LoginScreen(QWidget):
    def setup_ui(self):
        title = QLabel("Welcome Back")
        subtitle = QLabel("Sign in to continue to SLM Educator")
        username_input = QLineEdit()
        username_input.setPlaceholderText("Username")
        password_input = QLineEdit()
        password_input.setPlaceholderText("Password")
        signin_btn = QPushButton("Sign In")
```

### Translated Code:
```python
from src.ui.i18n import tr

class LoginScreen(QWidget):
    def setup_ui(self):
        title = QLabel(tr("auth.login.title"))
        subtitle = QLabel(tr("auth.login.subtitle"))
        username_input = QLineEdit()
        username_input.setPlaceholderText(tr("auth.login.username_placeholder"))
        password_input = QLineEdit()
        password_input.setPlaceholderText(tr("auth.login.password_placeholder"))
        signin_btn = QPushButton(tr("auth.login.button_signin"))
```

## Testing Translations

### Test Script Example:
```python
from src.ui.i18n import tr, set_language, get_available_languages

# Test English (default)
print(tr("common.buttons.save"))  # "Save"

# Test Spanish
set_language('es')
print(tr("common.buttons.save"))  # "Guardar"

# Test fallback (missing key in es.json falls back to en.json)
print(tr("some.missing.key"))  # Returns English version or key itself

# Test parameter interpolation
message = tr("common.messages.generic_error", error_msg="Test error")
print(message)

# List available languages
print(get_available_languages())  # ['en', 'es']
```

## Integration with Settings

The settings screen should include a language selector:

```python
# In settings_screen.py
from src.ui.i18n import (tr, set_language, get_current_language,
                         get_available_languages, get_language_name)

# Create language selector
language_combo = QComboBox()
for lang_code in get_available_languages():
    language_combo.addItem(get_language_name(lang_code), lang_code)

# Set current language
current_lang = get_current_language()
index = language_combo.findData(current_lang)
language_combo.setCurrentIndex(index)

# Handle language change
def on_language_changed(index):
    lang_code = language_combo.itemData(index)
    set_language(lang_code)
    # Note: You may need to restart the app or reload UI for full effect
```

## Troubleshooting

### Translation Not Found
**Problem:** `tr("some.key")` returns `"some.key"` instead of translated text.

**Solutions:**
1. Check if the key exists in `translations/en.json`
2. Verify the key path (dot notation must match JSON structure)
3. Check for typos in the key name

### Parameters Not Working
**Problem:** `tr("message", param="value")` doesn't substitute `{param}`.

**Solutions:**
1. Ensure the translation string contains `{param}` placeholder
2. Check parameter names match exactly
3. Verify you're passing parameters as keyword arguments

### Language Not Changing
**Problem:** `set_language('es')` doesn't change translations.

**Solutions:**
1. Verify `translations/es.json` exists
2. Check if the JSON file is valid (no syntax errors)
3. Some UI components may need to be recreated to reflect changes

## Future Enhancements

Potential improvements to the translation system:

1. **Auto-reload UI on language change**
2. **Plural forms support** (e.g., "1 item" vs "2 items")
3. **RTL (Right-to-Left) language support** for Arabic, Hebrew, etc.
4. **Translation validation tool** to find missing keys
5. **Translation extraction tool** to scan code for `tr()` calls

## Contributing Translations

To contribute a new language translation:

1. Fork the repository
2. Copy `translations/en.json` to `translations/[language_code].json`
3. Translate all values (keep keys in English)
4. Test your translation
5. Submit a pull request

## Summary

- **Easy to use:** Just `tr("key")` in your code
- **Maintainable:** Centralized JSON files
- **No duplicates:** Reuse common strings
- **Extensible:** Easy to add new languages
- **Type-safe:** Falls back to English if translation missing
- **Parameter support:** Dynamic content with `{placeholders}`

For questions or issues, check the documentation or create an issue on GitHub.
