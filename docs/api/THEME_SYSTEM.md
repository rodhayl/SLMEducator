# Theme System Documentation

## Overview

The SLMEducator application features a professional theme system supporting both dark and light modes with dynamic switching. All UI components are styled consistently through a centralized `ThemeManager` class.

## Architecture

### ThemeManager Class

Located: `src/ui/styles/theme.py`

The `ThemeManager` is a centralized theme controller with static methods for applying themes application-wide.

#### Key Features

- **Dual Theme Support**: Dark (default) and Light modes
- **Dynamic Switching**: Themes can be changed at runtime without restart
- **Persistent Settings**: Theme preference saved to `settings.properties`
- **47 Widget Types Styled**: Comprehensive coverage of Qt widgets
- **Brand Consistency**: Core brand colors remain constant across themes

## Color Palette

### Dark Theme (Default)

```python
BACKGROUND = "#0F172A"      # Deep slate
SURFACE = "#1E293B"         # Elevated surface
SURFACE_LIGHT = "#334155"   # Cards/inputs
TEXT_PRIMARY = "#F1F5F9"    # Near white
TEXT_SECONDARY = "#CBD5E1"  # Subtle gray
```

### Light Theme

```python
BACKGROUND = "#F8FAFC"      # Light gray
SURFACE = "#FFFFFF"         # Pure white
SURFACE_LIGHT = "#F1F5F9"   # Light slate
TEXT_PRIMARY = "#0F172A"    # Deep slate
TEXT_SECONDARY = "#475569"  # Gray
```

### Brand Colors (Constant)

```python
PRIMARY = "#6366F1"         # Indigo (main brand)
PRIMARY_LIGHT = "#818CF8"   # Lighter indigo
PRIMARY_DARK = "#4F46E5"    # Darker indigo
SUCCESS = "#10B981"         # Emerald
WARNING = "#F59E0B"         # Amber
DANGER = "#EF4444"          # Red
INFO = "#3B82F6"            # Blue
```

## Usage

### Applying a Theme

```python
from PySide6.QtWidgets import QApplication
from ui.styles.theme import ThemeManager

app = QApplication(sys.argv)

# Apply dark theme
ThemeManager.apply_theme_preset(app, "dark")

# Apply light theme
ThemeManager.apply_theme_preset(app, "light")
```

### Loading Theme from Settings

```python
from core.services.settings_config_service import get_settings_service

settings = get_settings_service()
theme = settings.get('ui', 'default_theme', 'dark')
ThemeManager.apply_theme_preset(app, theme)
```

### Saving Theme Preference

```python
# In settings screen
settings.set('ui', 'default_theme', 'light')
settings.save_config()

# Apply immediately
ThemeManager.apply_theme_preset(app, 'light')
```

## Styled Components

The theme system provides comprehensive styling for:

### Input Widgets
- `QPushButton` - Standard buttons with hover/pressed states
- `QLineEdit` - Text input fields
- `QTextEdit`, `QPlainTextEdit` - Multi-line text areas
- `QComboBox` - Dropdown menus with styled items
- `QSpinBox` - Numeric input

### Display Widgets
- `QLabel` - Text labels
- `QFrame` - Container frames
- `QTableWidget`, `QTableView` - Data tables
- `QListWidget`, `QListView` - List displays
- `QTabWidget`, `QTabBar` - Tabbed interfaces
- `QProgressBar` - Progress indicators

### Interactive Elements
- `QCheckBox`, `QRadioButton` - Selection controls
- `QScrollBar` - Scrollbars (vertical and horizontal)
- `QMenu`, `QMenuBar` - Application menus
- `QStatusBar` - Status bar

### Dialogs
- `QMessageBox` - Message dialogs
- `QDialog` - Custom dialogs
- `QInputDialog` - Input dialogs
- `QFileDialog` - File selection dialogs
- `QProgressDialog` - Progress dialogs

### Special Elements
- `QToolTip` - Hover tooltips
- `QHeaderView` - Table headers

## Theme Switching Behavior

### Immediate Application
When `apply_theme_preset()` is called, the theme is applied immediately to the entire application through Qt's stylesheet system.

### Widget Refresh
Most widgets refresh automatically. Complex custom widgets may require manual refresh:

```python
widget.setStyleSheet(widget.styleSheet())  # Force refresh
```

### Persistence Across Restarts
Theme preference is stored in `settings.properties`:

```ini
[ui]
default_theme = dark  # or "light"
```

On application startup (`src/ui/app.py`):

```python
settings = get_settings_service()
theme = settings.get('ui', 'default_theme', 'dark')
ThemeManager.apply_theme_preset(self.app, theme)
```

## Customization

### Adding New Colors

Add to `ThemeManager` class and update in both theme presets:

```python
class ThemeManager:
    # Add new color
    CUSTOM_COLOR = "#AABBCC"
    
    @staticmethod
    def apply_theme_preset(app, theme="dark"):
        if theme.lower() == "light":
            ThemeManager.CUSTOM_COLOR = "#DDEEFF"
        else:
            ThemeManager.CUSTOM_COLOR = "#112233"
```

### Styling New Widgets

Add to the stylesheet in `apply_theme()`:

```python
app.setStyleSheet(f"""
    /* ... existing styles ... */
    
    QYourWidget {{
        background-color: {ThemeManager.SURFACE};
        color: {ThemeManager.TEXT_PRIMARY};
        border: 1px solid {ThemeManager.BORDER};
    }}
""")
```

## Best Practices

### 1. Use Theme Colors
Always reference `ThemeManager` colors instead of hardcoding:

```python
# ✅ Good
label.setStyleSheet(f"color: {ThemeManager.TEXT_PRIMARY};")

# ❌ Bad
label.setStyleSheet("color: #F1F5F9;")
```

### 2. Support Both Themes
Test UI components in both dark and light modes to ensure readability.

### 3. Avoid Inline Styles When Possible
Prefer using the global stylesheet. Add widget-specific styles only when necessary.

### 4. Check Text Contrast
Ensure sufficient contrast between text and background colors, especially for:
- Dialog messages
- Error messages
- Disabled states

## Migration Guide

### From Hardcoded Colors

1. Identify all color values in your component
2. Map them to semantic `ThemeManager` colors
3. Replace with theme color references
4. Test in both dark and light modes

Example:

```python
# Before
widget.setStyleSheet("background: #1E293B; color: #F1F5F9;")

# After
widget.setStyleSheet(f"background: {ThemeManager.SURFACE}; color: {ThemeManager.TEXT_PRIMARY};")
```

### Adding Theme Toggle

```python
from PySide6.QtWidgets import QPushButton
from ui.styles.theme import ThemeManager

toggle_btn = QPushButton("Toggle Theme")

def toggle_theme():
    new_theme = "light" if ThemeManager.current_theme == "dark" else "dark"
    ThemeManager.apply_theme_preset(QApplication.instance(), new_theme)
    
    # Save preference
    settings = get_settings_service()
    settings.set('ui', 'default_theme', new_theme)
    settings.save_config()

toggle_btn.clicked.connect(toggle_theme)
```

## Testing

### Unit Tests

See `tests/test_theme_switching.py` for comprehensive test coverage:

- Color value verification
- Theme switching transitions
- Brand color consistency
- Settings persistence
- Edge cases (invalid themes, case sensitivity)

### Manual Testing Checklist

- [ ] All screens display correctly in dark mode
- [ ] All screens display correctly in light mode
- [ ] Theme changes apply immediately
- [ ] No visual artifacts after theme switch
- [ ] Dialog text is readable in both modes
- [ ] Theme preference persists across restarts
- [ ] Settings screen theme dropdown works correctly

## Troubleshooting

### Theme Not Applying

1. Check that `QApplication` instance exists before calling `apply_theme_preset()`
2. Verify `ThemeManager` is imported correctly
3. Ensure stylesheet isn't being overridden by widget-specific styles

### Colors Not Updating

1. Some custom widgets may need manual refresh
2. Check if widget has inline `setStyleSheet()` that overrides global theme
3. Verify theme colors are correctly set in both theme blocks

### Persistence Issues

1. Check `settings.properties` file exists
2. Verify write permissions for settings file
3. Ensure `save_config()` is called after `set()`

## Future Enhancements

Potential improvements for the theme system:

1. **Auto Theme**: Match system theme (Windows/macOS)
2. **Custom Themes**: User-defined color schemes
3. **Theme Preview**: Live preview before applying
4. **Per-Widget Themes**: Component-specific theming
5. **Animation**: Smooth transitions between themes
6. **Accessibility**: High contrast mode, larger text options
