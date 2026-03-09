"""
Theme system for the Drawing Generator GUI.

Contains all theme color definitions, the ThemeManager for managing
theme state and notifications, and the T() helper function.
"""

import customtkinter as ctk


# ============================================================================
# MODERN THEME SYSTEM
# ============================================================================

class ThemeColors:
    """Base theme color scheme."""
    name = "Base"
    # Background colors
    bg_primary = "#0a0a0c"
    bg_secondary = "#12141a"
    bg_tertiary = "#1a1d24"
    bg_hover = "#252830"
    # Text colors
    text_primary = "#00ff88"
    text_secondary = "#00cc6a"
    text_dim = "#9ca3af"
    text_white = "#e4e4e7"
    text_on_tertiary = "#e4e4e7"
    text_on_accent = "#000000"  # Dark text for bright accent backgrounds
    tab_unselected_text = "#c0c0c0"  # Visible text for inactive tabs
    text_error = "#ff4455"
    text_warning = "#ffaa00"
    # Accent colors
    accent = "#00ff88"
    accent_dim = "#00aa55"
    accent_hover = "#00dd77"
    # UI elements
    border = "#2d3139"
    button_bg = "#1a3d2a"
    button_hover = "#2a5d4a"
    button_active = "#00ff88"
    # CustomTkinter mode
    ctk_mode = "dark"


class ObsidianTheme(ThemeColors):
    """Dark theme with green accents (default)."""
    name = "Obsidian"
    bg_primary = "#0a0a0c"
    bg_secondary = "#12141a"
    bg_tertiary = "#1a1d24"
    bg_hover = "#252830"
    text_primary = "#00ff88"
    text_secondary = "#00cc6a"
    text_dim = "#6b7280"
    text_white = "#e4e4e7"
    text_on_tertiary = "#e4e4e7"
    text_on_accent = "#000000"
    tab_unselected_text = "#c0c0c0"
    accent = "#00ff88"
    accent_dim = "#00aa55"
    accent_hover = "#00dd77"
    border = "#2d3139"
    button_bg = "#1a3d2a"
    button_hover = "#2a5d4a"
    ctk_mode = "dark"


class MidnightBlueTheme(ThemeColors):
    """Dark blue theme."""
    name = "Midnight Blue"
    bg_primary = "#0a0e14"
    bg_secondary = "#0f1419"
    bg_tertiary = "#151c24"
    bg_hover = "#1c2530"
    text_primary = "#5ccfe6"
    text_secondary = "#4db8c7"
    text_dim = "#5c6773"
    text_white = "#e4e4e7"
    text_on_tertiary = "#e4e4e7"
    text_on_accent = "#000000"
    tab_unselected_text = "#c0c0c0"
    accent = "#5ccfe6"
    accent_dim = "#3d8fa3"
    accent_hover = "#7dd9ec"
    border = "#1f2833"
    button_bg = "#1a2d3d"
    button_hover = "#2a4d5d"
    ctk_mode = "dark"


class DraculaTheme(ThemeColors):
    """Dracula-inspired purple theme."""
    name = "Dracula"
    bg_primary = "#1e1f29"
    bg_secondary = "#282a36"
    bg_tertiary = "#343746"
    bg_hover = "#424556"
    text_primary = "#bd93f9"
    text_secondary = "#a67ee8"
    text_dim = "#6272a4"
    text_white = "#e8e8e8"
    text_on_tertiary = "#e8e8e8"
    text_on_accent = "#1e1f29"
    tab_unselected_text = "#c0c0c0"
    accent = "#bd93f9"
    accent_dim = "#8a63d2"
    accent_hover = "#d4b0ff"
    border = "#44475a"
    button_bg = "#3d2d5a"
    button_hover = "#5d4d7a"
    ctk_mode = "dark"


class NordTheme(ThemeColors):
    """Nord arctic-inspired theme."""
    name = "Nord"
    bg_primary = "#242933"
    bg_secondary = "#2e3440"
    bg_tertiary = "#3b4252"
    bg_hover = "#434c5e"
    text_primary = "#88c0d0"
    text_secondary = "#81a1c1"
    text_dim = "#616e88"
    text_white = "#e5e9f0"
    text_on_tertiary = "#e5e9f0"
    text_on_accent = "#2e3440"
    tab_unselected_text = "#c0c8d0"
    accent = "#88c0d0"
    accent_dim = "#5e81ac"
    accent_hover = "#a3d5e3"
    border = "#4c566a"
    button_bg = "#3b4d5e"
    button_hover = "#4b5d6e"
    ctk_mode = "dark"


class MonokaiTheme(ThemeColors):
    """Monokai-inspired theme."""
    name = "Monokai"
    bg_primary = "#1e1f1c"
    bg_secondary = "#272822"
    bg_tertiary = "#3e3d32"
    bg_hover = "#4e4d42"
    text_primary = "#a6e22e"
    text_secondary = "#e6db74"
    text_dim = "#75715e"
    text_white = "#e8e8e8"
    text_on_tertiary = "#e8e8e8"
    text_on_accent = "#1e1f1c"
    tab_unselected_text = "#c0c0c0"
    accent = "#a6e22e"
    accent_dim = "#7ab01e"
    accent_hover = "#b8f040"
    border = "#49483e"
    button_bg = "#3d4a2a"
    button_hover = "#5d6a4a"
    ctk_mode = "dark"


class CyberpunkTheme(ThemeColors):
    """Cyberpunk neon theme."""
    name = "Cyberpunk"
    bg_primary = "#0a0012"
    bg_secondary = "#120020"
    bg_tertiary = "#1a0030"
    bg_hover = "#2a0050"
    text_primary = "#ff00ff"
    text_secondary = "#00ffff"
    text_dim = "#8844aa"
    text_white = "#e8e8e8"
    text_on_tertiary = "#e8e8e8"
    text_on_accent = "#0a0012"
    tab_unselected_text = "#d0b0e0"
    accent = "#ff00ff"
    accent_dim = "#aa00aa"
    accent_hover = "#ff44ff"
    border = "#4400aa"
    button_bg = "#3d0055"
    button_hover = "#5d0075"
    ctk_mode = "dark"


class LightTheme(ThemeColors):
    """Clean light theme with blue accents - high contrast."""
    name = "Light"
    bg_primary = "#ffffff"
    bg_secondary = "#f8fafc"
    bg_tertiary = "#e2e8f0"
    bg_hover = "#cbd5e1"
    text_primary = "#1d4ed8"
    text_secondary = "#2563eb"
    text_dim = "#64748b"
    text_white = "#1e293b"
    text_on_tertiary = "#1e293b"
    text_on_accent = "#ffffff"
    tab_unselected_text = "#334155"
    text_error = "#b91c1c"
    text_warning = "#a16207"
    accent = "#2563eb"
    accent_dim = "#3b82f6"
    accent_hover = "#1d4ed8"
    border = "#cbd5e1"
    button_bg = "#eff6ff"
    button_hover = "#dbeafe"
    ctk_mode = "light"


class LightGreenTheme(ThemeColors):
    """Light theme with green accents - high contrast."""
    name = "Light Green"
    bg_primary = "#ffffff"
    bg_secondary = "#f0fdf4"
    bg_tertiary = "#dcfce7"
    bg_hover = "#bbf7d0"
    text_primary = "#047857"
    text_secondary = "#059669"
    text_dim = "#64748b"
    text_white = "#14532d"
    text_on_tertiary = "#14532d"
    text_on_accent = "#ffffff"
    tab_unselected_text = "#1e3a2a"
    text_error = "#b91c1c"
    text_warning = "#a16207"
    accent = "#059669"
    accent_dim = "#10b981"
    accent_hover = "#047857"
    border = "#86efac"
    button_bg = "#ecfdf5"
    button_hover = "#d1fae5"
    ctk_mode = "light"


class SolarizedLightTheme(ThemeColors):
    """Solarized light theme - high contrast."""
    name = "Solarized Light"
    bg_primary = "#fdf6e3"
    bg_secondary = "#eee8d5"
    bg_tertiary = "#e4dcc8"
    bg_hover = "#d6cdb5"
    text_primary = "#268bd2"
    text_secondary = "#2aa198"
    text_dim = "#657b83"
    text_white = "#073642"
    text_on_tertiary = "#073642"
    text_on_accent = "#ffffff"
    tab_unselected_text = "#2b4450"
    text_error = "#dc322f"
    text_warning = "#b58900"
    accent = "#268bd2"
    accent_dim = "#2aa198"
    accent_hover = "#1a6091"
    border = "#93a1a1"
    button_bg = "#eee8d5"
    button_hover = "#e4dcc8"
    ctk_mode = "light"


class PaperTheme(ThemeColors):
    """Warm paper-like light theme - high contrast."""
    name = "Paper"
    bg_primary = "#fffcf5"
    bg_secondary = "#f5f0e6"
    bg_tertiary = "#e8e0d0"
    bg_hover = "#d9cfc0"
    text_primary = "#7c4a1a"
    text_secondary = "#92551f"
    text_dim = "#57534e"
    text_white = "#1c1917"
    text_on_tertiary = "#1c1917"
    text_on_accent = "#ffffff"
    tab_unselected_text = "#3d3530"
    text_error = "#b91c1c"
    text_warning = "#a16207"
    accent = "#7c4a1a"
    accent_dim = "#5c3510"
    accent_hover = "#92551f"
    border = "#a8a29e"
    button_bg = "#e8e0d0"
    button_hover = "#d9cfc0"
    ctk_mode = "light"


# Available themes
THEMES = {
    'obsidian': ObsidianTheme,
    'midnight': MidnightBlueTheme,
    'dracula': DraculaTheme,
    'nord': NordTheme,
    'monokai': MonokaiTheme,
    'cyberpunk': CyberpunkTheme,
    'light': LightTheme,
    'light_green': LightGreenTheme,
    'solarized_light': SolarizedLightTheme,
    'paper': PaperTheme,
}


class ThemeManager:
    """Manages theme state and notifications."""
    _current = ObsidianTheme
    _callbacks = []

    @classmethod
    def get(cls):
        return cls._current

    @classmethod
    def set(cls, key: str):
        if key in THEMES:
            cls._current = THEMES[key]
            ctk.set_appearance_mode(cls._current.ctk_mode)
            # Update all registered callbacks
            dead_callbacks = []
            for callback in cls._callbacks:
                try:
                    callback()
                except Exception:
                    dead_callbacks.append(callback)
            # Remove dead callbacks
            for cb in dead_callbacks:
                cls._callbacks.remove(cb)

    @classmethod
    def register(cls, callback):
        cls._callbacks.append(callback)

    @classmethod
    def unregister(cls, callback):
        if callback in cls._callbacks:
            cls._callbacks.remove(callback)


def T():
    """Shortcut to get current theme."""
    return ThemeManager.get()
