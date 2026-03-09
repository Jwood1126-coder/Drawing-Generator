"""
Modern themed UI widget classes for the Drawing Generator application.

Provides customtkinter and tkinter widget subclasses with automatic theme
support via ThemeManager registration.
"""

import customtkinter as ctk
import tkinter as tk
from themes import T, ThemeManager


# ============================================================================
# MODERN UI COMPONENTS
# ============================================================================

class ModernCard(ctk.CTkFrame):
    """A modern card container with rounded corners and subtle shadow effect."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            corner_radius=12,
            fg_color=T().bg_secondary,
            border_width=1,
            border_color=T().border,
            **kwargs
        )
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.configure(
            fg_color=T().bg_secondary,
            border_color=T().border
        )

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ModernSection(ctk.CTkFrame):
    """A section with header and content area."""

    def __init__(self, parent, title: str, icon: str = "◈", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        self.icon_label = ctk.CTkLabel(
            header,
            text=icon,
            font=ctk.CTkFont(size=14),
            text_color=T().accent,
            width=20
        )
        self.icon_label.pack(side="left", padx=(0, 8))

        self.title_label = ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=T().text_primary
        )
        self.title_label.pack(side="left")

        # Separator line
        self.separator = ctk.CTkFrame(
            header,
            height=1,
            fg_color=T().accent_dim
        )
        self.separator.pack(side="left", fill="x", expand=True, padx=(12, 0), pady=16)

        # Content frame with proper background
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=4)

        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.icon_label.configure(text_color=T().accent)
        self.title_label.configure(text_color=T().text_primary)
        self.separator.configure(fg_color=T().accent_dim)

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ModernButton(ctk.CTkButton):
    """A modern button with consistent styling."""

    def __init__(self, parent, text: str, command=None, variant="primary", width=140, height=36, **kwargs):
        if variant == "primary":
            fg_color = T().accent_dim
            hover_color = T().accent_hover
            text_color = T().bg_primary if T().ctk_mode == "dark" else "#ffffff"
        elif variant == "secondary":
            fg_color = T().bg_tertiary
            hover_color = T().bg_hover
            text_color = T().text_white
        else:  # ghost
            fg_color = "transparent"
            hover_color = T().bg_hover
            text_color = T().text_white

        super().__init__(
            parent,
            text=text,
            command=command,
            width=width,
            height=height,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            **kwargs
        )
        self._variant = variant
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        if self._variant == "primary":
            self.configure(
                fg_color=T().accent_dim,
                hover_color=T().accent_hover,
                text_color=T().bg_primary if T().ctk_mode == "dark" else "#ffffff"
            )
        elif self._variant == "secondary":
            self.configure(
                fg_color=T().bg_tertiary,
                hover_color=T().bg_hover,
                text_color=T().text_white
            )
        else:
            self.configure(
                fg_color="transparent",
                hover_color=T().bg_hover,
                text_color=T().text_white
            )

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ModernEntry(ctk.CTkEntry):
    """A modern entry field."""

    def __init__(self, parent, placeholder: str = "", width=None, **kwargs):
        super().__init__(
            parent,
            width=width if width else 200,
            height=32,
            corner_radius=8,
            border_width=1,
            fg_color=T().bg_tertiary,
            border_color=T().border,
            text_color=T().text_white,
            placeholder_text_color=T().text_dim,
            placeholder_text=placeholder,
            font=ctk.CTkFont(size=12),
            **kwargs
        )
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.configure(
            fg_color=T().bg_tertiary,
            border_color=T().border,
            text_color=T().text_white,
            placeholder_text_color=T().text_dim
        )

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ModernLabel(ctk.CTkLabel):
    """A modern label with theme support."""

    def __init__(self, parent, text: str, style="default", width=None, anchor=None, **kwargs):
        if style == "title":
            font = ctk.CTkFont(size=16, weight="bold")
            text_color = T().text_white
        elif style == "heading":
            font = ctk.CTkFont(size=13, weight="bold")
            text_color = T().text_primary
        elif style == "accent":
            font = ctk.CTkFont(size=12)
            text_color = T().accent
        elif style == "dim":
            font = ctk.CTkFont(size=11)
            text_color = T().text_dim
        else:
            font = ctk.CTkFont(size=12)
            text_color = T().text_white

        super().__init__(
            parent,
            text=text,
            font=font,
            text_color=text_color,
            width=width if width else 0,
            anchor=anchor if anchor else "w",
            **kwargs
        )
        self._style = style
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        if self._style == "title":
            self.configure(text_color=T().text_white)
        elif self._style == "heading":
            self.configure(text_color=T().text_primary)
        elif self._style == "accent":
            self.configure(text_color=T().accent)
        elif self._style == "dim":
            self.configure(text_color=T().text_dim)
        else:
            self.configure(text_color=T().text_white)

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ModernCheckbox(ctk.CTkCheckBox):
    """A modern checkbox."""

    def __init__(self, parent, text: str, variable=None, command=None, **kwargs):
        super().__init__(
            parent,
            text=text,
            variable=variable,
            command=command,
            font=ctk.CTkFont(size=12),
            text_color=T().text_white,
            fg_color=T().accent,
            hover_color=T().accent_hover,
            border_color=T().border,
            checkmark_color=T().bg_primary if T().ctk_mode == "dark" else "#ffffff",
            corner_radius=4,
            border_width=2,
            **kwargs
        )
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.configure(
            text_color=T().text_white,
            fg_color=T().accent,
            hover_color=T().accent_hover,
            border_color=T().border,
            checkmark_color=T().bg_primary if T().ctk_mode == "dark" else "#ffffff"
        )

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ModernSlider(ctk.CTkSlider):
    """A modern slider."""

    def __init__(self, parent, from_=0, to=100, variable=None, command=None, **kwargs):
        super().__init__(
            parent,
            from_=from_,
            to=to,
            variable=variable,
            command=command,
            height=16,
            corner_radius=8,
            button_corner_radius=8,
            button_length=0,
            fg_color=T().bg_tertiary,
            progress_color=T().accent_dim,
            button_color=T().accent,
            button_hover_color=T().accent_hover,
            **kwargs
        )
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.configure(
            fg_color=T().bg_tertiary,
            progress_color=T().accent_dim,
            button_color=T().accent,
            button_hover_color=T().accent_hover
        )

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ModernDropdown(ctk.CTkOptionMenu):
    """A modern dropdown menu."""

    def __init__(self, parent, values: list, variable=None, command=None, width=140, **kwargs):
        super().__init__(
            parent,
            values=values,
            variable=variable,
            command=command,
            width=width,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=12),
            dropdown_font=ctk.CTkFont(size=12),
            fg_color=T().bg_tertiary,
            button_color=T().bg_hover,
            button_hover_color=T().accent_dim,
            dropdown_fg_color=T().bg_secondary,
            dropdown_hover_color=T().bg_hover,
            text_color=T().text_white,
            dropdown_text_color=T().text_white,
            **kwargs
        )
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.configure(
            fg_color=T().bg_tertiary,
            button_color=T().bg_hover,
            button_hover_color=T().accent_dim,
            dropdown_fg_color=T().bg_secondary,
            dropdown_hover_color=T().bg_hover,
            text_color=T().text_white,
            dropdown_text_color=T().text_white
        )

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ModernProgressBar(ctk.CTkProgressBar):
    """A modern progress bar."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            height=6,
            corner_radius=3,
            fg_color=T().bg_tertiary,
            progress_color=T().accent,
            **kwargs
        )
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.configure(
            fg_color=T().bg_tertiary,
            progress_color=T().accent
        )

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()



class ThemedListbox(tk.Listbox):
    """A tkinter Listbox that updates with theme changes."""

    def __init__(self, parent, **kwargs):
        # Set theme-aware defaults
        defaults = {
            'bg': T().bg_tertiary,
            'fg': T().text_on_tertiary,
            'selectbackground': T().accent_dim,
            'selectforeground': T().text_white,
            'highlightthickness': 2,
            'highlightbackground': T().border,
            'highlightcolor': T().accent,
            'relief': 'flat',
            'font': ('Segoe UI', 10),
            'activestyle': 'none',
            'borderwidth': 2,
        }
        defaults.update(kwargs)
        super().__init__(parent, **defaults)
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        try:
            self.configure(
                bg=T().bg_tertiary,
                fg=T().text_on_tertiary,
                selectbackground=T().accent_dim,
                selectforeground=T().text_white,
                highlightbackground=T().border,
                highlightcolor=T().accent
            )
        except tk.TclError:
            pass  # Widget destroyed

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class ThemedCanvas(tk.Canvas):
    """A tkinter Canvas that updates with theme changes."""

    def __init__(self, parent, **kwargs):
        defaults = {
            'bg': T().bg_tertiary,
            'highlightthickness': 0,
        }
        defaults.update(kwargs)
        super().__init__(parent, **defaults)
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        try:
            self.configure(bg=T().bg_tertiary)
        except tk.TclError:
            pass  # Widget destroyed

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


class StatusBar(ctk.CTkFrame):
    """Modern status bar with progress indicator."""

    def __init__(self, parent):
        super().__init__(parent, height=36, corner_radius=0, fg_color=T().bg_secondary)
        self.pack_propagate(False)

        self.status_label = ModernLabel(self, text="Ready", style="accent")
        self.status_label.pack(side="left", padx=16)

        self.progress_label = ModernLabel(self, text="", style="dim")
        self.progress_label.pack(side="right", padx=16)

        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.configure(fg_color=T().bg_secondary)

    def set_status(self, text: str, is_error: bool = False):
        color = T().text_error if is_error else T().accent
        self.status_label.configure(text=text, text_color=color)

    def set_progress(self, current: int, total: int):
        if total > 0:
            pct = (current / total) * 100
            self.progress_label.configure(text=f"{current}/{total} ({pct:.1f}%)")
        else:
            self.progress_label.configure(text="")

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()
