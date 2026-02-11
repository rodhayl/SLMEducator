# ThemeManager API Documentation

## Class: `ThemeManager`

**Module**: `ui.styles.theme`  
**Type**: Static utility class

A centralized theme management system for the SLMEducator application. Provides dual-theme support (dark/light) with dynamic switching capabilities.

---

## Class Attributes

### Color Constants

#### Brand Colors (Constant Across Themes)
```python
PRIMARY: str = "#6366F1"           # Indigo - Primary brand color
PRIMARY_LIGHT: str = "#818CF8"     # Lighter indigo - Hover states
PRIMARY_DARK: str = "#4F46E5"      # Darker indigo - Pressed states
SECONDARY: str = "#64748B"         # Slate - Secondary actions (deprecated)
ACCENT: str = "#3B82F6"            # Blue - Accent color (deprecated)
```

#### Semantic Colors (Constant Across Themes)
```python
SUCCESS: str = "#10B981"           # Emerald - Success states
WARNING: str = "#F59E0B"           # Amber - Warning states
DANGER: str = "#EF4444"            # Red - Error/danger states
INFO: str = "#3B82F6"              # Blue - Informational states
```

#### Dynamic Colors (Change With Theme)

**Background Colors**
```python
BACKGROUND: str                    # Main application background
SURFACE: str                       # Elevated surface (cards, panels)
SURFACE_LIGHT: str                 # Lighter surface (inputs, headers)
SURFACE_HOVER: str                 # Hover state for interactive surfaces
```

**Text Colors**
```python
TEXT_PRIMARY: str                  # Primary text color
TEXT_SECONDARY: str                # Secondary/muted text
TEXT_DISABLED: str                 # Disabled element text
```

**Border & Divider Colors**
```python
BORDER: str                        # Subtle borders
BORDER_LIGHT: str                  # More visible borders
DIVIDER: str                       # Divider lines
```

**Input Colors**
```python
INPUT_BG: str                      # Input field background
INPUT_BORDER: str                  # Input field border
INPUT_FOCUS: str                   # Focused input border
```

**Shadow Colors**
```python
SHADOW_LIGHT: str                  # Light shadow (RGBA)
SHADOW_MEDIUM: str                 # Medium shadow (RGBA)
SHADOW_HEAVY: str                  # Heavy shadow (RGBA)
```

#### State Tracking
```python
current_theme: str = "dark"        # Current active theme ("dark" or "light")
```

---

## Methods

### `apply_theme_preset(app: QApplication, theme: str = "dark") -> None`

Apply a theme preset and refresh all application widgets.

**Parameters:**
- `app` (`QApplication`): The Qt application instance to apply the theme to
- `theme` (`str`, optional): Theme name - `"dark"` or `"light"`. Defaults to `"dark"`

**Returns:** `None`

**Behavior:**
1. Sets `current_theme` to the specified theme (lowercased)
2. Updates all dynamic color attributes based on theme selection
3. Calls `apply_theme()` to apply the stylesheet

**Theme Color Mappings:**

| Color Attribute | Dark Theme | Light Theme |
|----------------|------------|-------------|
| `BACKGROUND` | `#0F172A` | `#F8FAFC` |
| `SURFACE` | `#1E293B` | `#FFFFFF` |
| `SURFACE_LIGHT` | `#334155` | `#F1F5F9` |
| `SURFACE_HOVER` | `#475569` | `#E2E8F0` |
| `TEXT_PRIMARY` | `#F1F5F9` | `#0F172A` |
| `TEXT_SECONDARY` | `#CBD5E1` | `#475569` |
| `TEXT_DISABLED` | `#64748B` | `#94A3B8` |
| `BORDER` | `#334155` | `#E2E8F0` |
| `BORDER_LIGHT` | `#475569` | `#CBD5E1` |
| `DIVIDER` | `#1E293B` | `#F1F5F9` |
| `INPUT_BG` | `#1E293B` | `#FFFFFF` |
| `INPUT_BORDER` | `#475569` | `#CBD5E1` |

**Example:**
```python
from PySide6.QtWidgets import QApplication
from ui.styles.theme import ThemeManager

app = QApplication(sys.argv)

# Apply dark theme
ThemeManager.apply_theme_preset(app, "dark")

# Apply light theme
ThemeManager.apply_theme_preset(app, "light")
```

**Notes:**
- Theme names are case-insensitive (converted to lowercase)
- Invalid theme names default to dark theme behavior
- Changes take effect immediately across the entire application

---

### `apply_theme(app: QApplication) -> None`

Apply the current theme stylesheet to the application.

**Parameters:**
- `app` (`QApplication`): The Qt application instance

**Returns:** `None`

**Behavior:**
Generates and applies a comprehensive Qt stylesheet using the current color attributes. Styles 47 different widget types including buttons, inputs, tables, dialogs, and more.

**Styled Widget Types:**
- Layout: `QWidget`, `QMainWindow`, `QFrame`
- Buttons: `QPushButton` (with hover, pressed, disabled states)
- Inputs: `QLineEdit`, `QTextEdit`, `QPlainTextEdit`, `QComboBox`, `QSpinBox`
- Tables: `QTableWidget`, `QTableView`, `QHeaderView`
- Lists: `QListWidget`, `QListView`
- Tabs: `QTabWidget`, `QTabBar`
- Dialogs: `QMessageBox`, `QDialog`, `QInputDialog`, `QFileDialog`, `QProgressDialog`
- Navigation: `QMenuBar`, `QMenu`, `QScrollBar`
- Other: `QLabel`, `QCheckBox`, `QRadioButton`, `QProgressBar`, `QStatusBar`, `QToolTip`

**Example:**
```python
# Typically called by apply_theme_preset()
# Can be called standalone if color attributes are manually updated
ThemeManager.BACKGROUND = "#0F172A"
ThemeManager.TEXT_PRIMARY = "#F1F5F9"
# ... set other attributes ...
ThemeManager.apply_theme(app)
```

**Notes:**
- Uses f-strings to interpolate color values into CSS
- Includes comprehensive hover, focus, and disabled states
- Supports custom styling for dropdown items, scrollbars, and complex widgets
- Generally called automatically by `apply_theme_preset()` rather than directly

---

## Usage Patterns

### Basic Theme Application

```python
from PySide6.QtWidgets import QApplication
from ui.styles.theme import ThemeManager

# Initialize app
app = QApplication(sys.argv)

# Apply default dark theme
ThemeManager.apply_theme_preset(app)

# Or explicitly specify theme
ThemeManager.apply_theme_preset(app, "dark")
```

### Loading from Settings

```python
from core.services.settings_config_service import get_settings_service

settings = get_settings_service()
theme_pref = settings.get('ui', 'default_theme', 'dark')
ThemeManager.apply_theme_preset(app, theme_pref)
```

### Runtime Theme Switching

```python
def switch_to_light_theme():
    app = QApplication.instance()
    ThemeManager.apply_theme_preset(app, "light")
    
    # Save preference
    settings = get_settings_service()
    settings.set('ui', 'default_theme', 'light')
    settings.save_config()

def switch_to_dark_theme():
    app = QApplication.instance()
    ThemeManager.apply_theme_preset(app, "dark")
    
    # Save preference
    settings = get_settings_service()
    settings.set('ui', 'default_theme', 'dark')
    settings.save_config()
```

### Using Theme Colors in Custom Widgets

```python
from PySide6.QtWidgets import QLabel
from ui.styles.theme import ThemeManager

label = QLabel("Custom Text")
label.setStyleSheet(f"""
    QLabel {{
        color: {ThemeManager.TEXT_PRIMARY};
        background-color: {ThemeManager.SURFACE};
        border: 1px solid {ThemeManager.BORDER};
        border-radius: 4px;
        padding: 8px;
    }}
""")
```

### Theme-Aware Custom Styling

```python
def get_button_style(is_primary: bool = True) -> str:
    """Get theme-aware button style"""
    if is_primary:
        bg_color = ThemeManager.PRIMARY
        hover_color = ThemeManager.PRIMARY_LIGHT
        text_color = "white"
    else:
        bg_color = ThemeManager.SURFACE_LIGHT
        hover_color = ThemeManager.SURFACE_HOVER
        text_color = ThemeManager.TEXT_PRIMARY
    
    return f"""
        QPushButton {{
            background-color: {bg_color};
            color: {text_color};
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
    """

# Usage
primary_btn = QPushButton("Submit")
primary_btn.setStyleSheet(get_button_style(is_primary=True))

secondary_btn = QPushButton("Cancel")
secondary_btn.setStyleSheet(get_button_style(is_primary=False))
```

---

## Best Practices

### ✅ DO

1. **Always use ThemeManager colors**
   ```python
   # Good
   widget.setStyleSheet(f"color: {ThemeManager.TEXT_PRIMARY};")
   ```

2. **Test in both themes**
   ```python
   # Test dark mode
   ThemeManager.apply_theme_preset(app, "dark")
   # Verify UI
   
   # Test light mode  
   ThemeManager.apply_theme_preset(app, "light")
   # Verify UI
   ```

3. **Use semantic colors appropriately**
   ```python
   success_label.setStyleSheet(f"color: {ThemeManager.SUCCESS};")
   error_label.setStyleSheet(f"color: {ThemeManager.DANGER};")
   ```

### ❌ DON'T

1. **Don't hardcode colors**
   ```python
   # Bad
   widget.setStyleSheet("color: #F1F5F9;")
   ```

2. **Don't mix theme and hardcoded colors**
   ```python
   # Bad
   widget.setStyleSheet(f"color: {ThemeManager.TEXT_PRIMARY}; background: #FFFFFF;")
   ```

3. **Don't override without preserving theme**
   ```python
   # Bad - loses theme on switch
   widget.setStyleSheet("background: #000000;")
   
   # Good - theme-aware
   widget.setStyleSheet(f"background: {ThemeManager.SURFACE};")
   ```

---

## Type Hints

```python
from typing import Literal
from PySide6.QtWidgets import QApplication

ThemeType = Literal["dark", "light"]

def apply_theme_preset(app: QApplication, theme: ThemeType = "dark") -> None: ...
def apply_theme(app: QApplication) -> None: ...
```

---

## Version History

- **v1.0** (2025-11-24): Initial implementation with dark/light themes
  - 47 widget types styled
  - Dynamic theme switching
  - Settings persistence
  - Comprehensive color palette

---

## See Also

- [THEME_SYSTEM.md](THEME_SYSTEM.md) - Complete theme system guide
- [settings_config_service.py](../src/core/services/settings_config_service.py) - Settings management
- [settings_screen.py](../src/ui/screens/settings_screen.py) - UI for theme selection
