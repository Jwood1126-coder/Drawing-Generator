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



class SearchableComboBox(ctk.CTkFrame):
    """A searchable dropdown that keeps focus while typing.

    Uses a CTkEntry + a Toplevel listbox popup instead of CTkComboBox,
    which loses focus when values are reconfigured.
    """

    def __init__(self, parent, values=None, width=240, command=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._all_values = list(values or [])
        self._command = command
        self._popup = None
        self._debounce_id = None

        self._entry = ctk.CTkEntry(
            self, width=width, height=32, corner_radius=8,
            border_width=1, font=ctk.CTkFont(size=12),
            fg_color=T().bg_tertiary, border_color=T().border,
            text_color=T().text_white, placeholder_text_color=T().text_dim,
        )
        self._entry.pack(side="left", fill="x", expand=True)

        self._btn = ctk.CTkButton(
            self, text="\u25BC", width=28, height=32, corner_radius=8,
            fg_color=T().accent_dim, hover_color=T().accent,
            text_color=T().bg_primary if T().ctk_mode == "dark" else "#ffffff",
            font=ctk.CTkFont(size=10),
            command=self._toggle_popup,
        )
        self._btn.pack(side="left", padx=(2, 0))

        self._entry.bind("<KeyRelease>", self._on_key)
        self._entry.bind("<Return>", self._on_enter)
        self._entry.bind("<Escape>", lambda e: self._close_popup())
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Down>", self._on_arrow_down)

        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self._entry.configure(
            fg_color=T().bg_tertiary, border_color=T().border,
            text_color=T().text_white, placeholder_text_color=T().text_dim,
        )
        self._btn.configure(
            fg_color=T().accent_dim, hover_color=T().accent,
            text_color=T().bg_primary if T().ctk_mode == "dark" else "#ffffff",
        )

    def get(self):
        return self._entry.get()

    def set(self, value):
        self._entry.delete(0, "end")
        self._entry.insert(0, value)

    def configure(self, **kwargs):
        if "values" in kwargs:
            self._all_values = list(kwargs.pop("values"))
        super().configure(**kwargs)

    def _on_key(self, event):
        if event.keysym in ("Return", "Escape", "Tab", "Down", "Up"):
            return
        # Debounce: wait 150ms after last keystroke before filtering
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(150, self._show_filtered)

    def _show_filtered(self):
        self._debounce_id = None
        search = self._entry.get().lower().strip()
        if not search:
            filtered = self._all_values
        else:
            filtered = [v for v in self._all_values if search in v.lower()]
        self._show_popup(filtered)

    def _toggle_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._close_popup()
        else:
            self._show_popup(self._all_values)
            self._entry.focus_set()

    def _show_popup(self, values):
        if not values:
            self._close_popup()
            return

        if self._popup and self._popup.winfo_exists():
            # Reuse existing popup — just update contents
            lb = self._listbox
            lb.delete(0, "end")
            for v in values:
                lb.insert("end", v)
            # Resize height
            h = min(len(values), 8) * 20 + 4
            self._popup.geometry(
                f"{self._entry.winfo_width() + 30}x{h}"
                f"+{self._entry.winfo_rootx()}+{self._entry.winfo_rooty() + self._entry.winfo_height() + 2}"
            )
            return

        self._popup = tk.Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.attributes("-topmost", True)

        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height() + 2
        w = self._entry.winfo_width() + 30
        h = min(len(values), 8) * 20 + 4
        self._popup.geometry(f"{w}x{h}+{x}+{y}")

        self._listbox = tk.Listbox(
            self._popup,
            bg=T().bg_secondary, fg=T().text_white,
            selectbackground=T().accent_dim, selectforeground=T().text_white,
            highlightthickness=1, highlightbackground=T().border,
            relief="flat", font=("Segoe UI", 10), activestyle="none",
            borderwidth=1,
        )
        self._listbox.pack(fill="both", expand=True)
        for v in values:
            self._listbox.insert("end", v)

        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        self._listbox.bind("<Return>", self._on_select)

    def _on_select(self, event=None):
        if not self._listbox.curselection():
            return
        value = self._listbox.get(self._listbox.curselection()[0])
        self.set(value)
        self._close_popup()
        if self._command:
            self._command(value)

    def _on_enter(self, event=None):
        # If popup is open and something is selected, pick it
        if self._popup and self._popup.winfo_exists() and self._listbox.curselection():
            self._on_select()
        # Otherwise fire the command with current text
        elif self._command:
            self._command(self.get())

    def _on_arrow_down(self, event=None):
        if self._popup and self._popup.winfo_exists():
            self._listbox.focus_set()
            if not self._listbox.curselection():
                self._listbox.selection_set(0)

    def _on_focus_out(self, event=None):
        # Delay close so click on listbox can register
        self.after(200, self._maybe_close)

    def _maybe_close(self):
        try:
            focused = self.focus_get()
            if self._popup and self._popup.winfo_exists():
                if focused and (focused == self._listbox or focused == self._entry):
                    return
            self._close_popup()
        except KeyError:
            self._close_popup()

    def _close_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None

    def destroy(self):
        self._close_popup()
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
