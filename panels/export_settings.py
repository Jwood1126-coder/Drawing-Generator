"""Export Settings Panel - format selection, quality, DPI, and size limits."""

import customtkinter as ctk
from typing import Optional, Dict, Set

from themes import T, ThemeManager
from widgets import ModernLabel, ModernEntry, ModernButton, ModernCheckbox, ModernSlider, ModernDropdown


class ExportSettingsPanel(ctk.CTkFrame):
    """
    Unified panel for all export settings:
    - Format selection with individual size limits
    - Global quality/DPI settings
    - Resize options
    """

    # Default size limits for each format
    DEFAULT_LIMITS = {
        'png':  {'value': '500', 'unit': 'KB'},
        'jpg':  {'value': '200', 'unit': 'KB'},
        'pdf':  {'value': '500', 'unit': 'KB'},
        'webp': {'value': '200', 'unit': 'KB'},
        'bmp':  {'value': '2', 'unit': 'MB'},
        'tiff': {'value': '1', 'unit': 'MB'},
        'gif':  {'value': '500', 'unit': 'KB'},
    }

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        # Format configurations - each format has: enabled, size_limit_enabled, limit_value, limit_unit
        self.format_configs = {}

        # Formats header row
        header = ctk.CTkFrame(self, fg_color=T().bg_tertiary, corner_radius=6)
        header.pack(fill="x", pady=(0, 8))
        self._header_frame = header

        # Column headers
        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=8, pady=6)

        ModernLabel(header_inner, text="Format", style="dim", width=70, anchor="w").pack(side="left")
        ModernLabel(header_inner, text="", style="dim", width=30).pack(side="left", padx=(10, 0))
        ModernLabel(header_inner, text="Limit", style="dim", width=30).pack(side="left", padx=(4, 0))
        ModernLabel(header_inner, text="Size", style="dim", width=100).pack(side="left", padx=(4, 0))

        # Format rows
        formats_frame = ctk.CTkFrame(self, fg_color=T().bg_tertiary, corner_radius=6)
        formats_frame.pack(fill="x", pady=(0, 12))
        self._formats_frame = formats_frame

        formats = [
            ('png', 'PNG', 'Lossless, large files'),
            ('jpg', 'JPEG', 'Lossy, small files'),
            ('pdf', 'PDF', 'Document format'),
            ('webp', 'WebP', 'Modern, efficient'),
            ('bmp', 'BMP', 'Uncompressed'),
            ('tiff', 'TIFF', 'High quality'),
            ('gif', 'GIF', '256 colors max'),
            ('ico', 'ICO', 'Icon format'),
        ]

        for fmt, label, tooltip in formats:
            defaults = self.DEFAULT_LIMITS.get(fmt, {'value': '500', 'unit': 'KB'})

            row = ctk.CTkFrame(formats_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=4)

            # Format checkbox (export enabled)
            export_var = ctk.BooleanVar(value=(fmt == 'png'))
            export_cb = ModernCheckbox(row, text=label, variable=export_var, width=70)
            export_cb.pack(side="left")

            # Size limit checkbox with "Limit:" label
            limit_var = ctk.BooleanVar(value=False)
            limit_cb = ModernCheckbox(row, text="Limit:", variable=limit_var, width=60)
            limit_cb.pack(side="left", padx=(10, 0))

            # Size limit entry - auto-enable limit when user types
            limit_entry = ModernEntry(row, width=50)
            limit_entry.insert(0, defaults['value'])
            limit_entry.pack(side="left", padx=(4, 0))
            limit_entry.bind("<Key>", lambda e, lv=limit_var: lv.set(True))

            # Size unit dropdown
            unit_var = ctk.StringVar(value=defaults['unit'])
            unit_dropdown = ModernDropdown(row, values=["KB", "MB"], variable=unit_var, width=60)
            unit_dropdown.pack(side="left", padx=(4, 0))

            self.format_configs[fmt] = {
                'export': export_var,
                'limit_enabled': limit_var,
                'limit_entry': limit_entry,
                'limit_unit': unit_var,
                'row': row
            }

        # Quick select row
        quick_row = ctk.CTkFrame(self, fg_color="transparent")
        quick_row.pack(fill="x", pady=(0, 12))

        ModernLabel(quick_row, text="Quick:", style="dim").pack(side="left")
        ModernButton(quick_row, "All", self._select_all, variant="ghost", width=50, height=26).pack(side="left", padx=2)
        ModernButton(quick_row, "None", self._select_none, variant="ghost", width=50, height=26).pack(side="left", padx=2)
        ModernButton(quick_row, "Common", self._select_common, variant="ghost", width=60, height=26).pack(side="left", padx=2)

        # Quality settings frame
        quality_frame = ctk.CTkFrame(self, fg_color=T().bg_tertiary, corner_radius=6)
        quality_frame.pack(fill="x", pady=(0, 8))
        self._quality_frame = quality_frame

        quality_inner = ctk.CTkFrame(quality_frame, fg_color="transparent")
        quality_inner.pack(fill="x", padx=12, pady=10)

        # DPI row
        dpi_row = ctk.CTkFrame(quality_inner, fg_color="transparent")
        dpi_row.pack(fill="x", pady=2)

        ModernLabel(dpi_row, text="Resolution:", style="dim", width=80, anchor="e").pack(side="left")
        self.dpi_var = ctk.StringVar(value="300")
        self.dpi_entry = ModernEntry(dpi_row, width=60)
        self.dpi_entry.insert(0, "300")
        self.dpi_entry.pack(side="left", padx=(8, 4))
        ModernLabel(dpi_row, text="DPI", style="dim").pack(side="left")

        # Quick DPI buttons
        for dpi in [150, 300, 600]:
            btn = ModernButton(dpi_row, str(dpi), lambda d=dpi: self._set_dpi(d),
                             variant="ghost", width=40, height=24)
            btn.pack(side="left", padx=2)

        # Quality row
        qual_row = ctk.CTkFrame(quality_inner, fg_color="transparent")
        qual_row.pack(fill="x", pady=2)

        ModernLabel(qual_row, text="Quality:", style="dim", width=80, anchor="e").pack(side="left")
        self.quality_var = ctk.IntVar(value=95)
        self.quality_slider = ModernSlider(qual_row, from_=10, to=100, variable=self.quality_var, width=120)
        self.quality_slider.pack(side="left", padx=8)
        self.quality_label = ModernLabel(qual_row, text="95%", style="accent", width=40)
        self.quality_label.pack(side="left")
        self.quality_var.trace_add("write", lambda *_: self.quality_label.configure(text=f"{self.quality_var.get()}%"))

        ModernLabel(qual_row, text="(JPG/WebP/PDF)", style="dim").pack(side="left", padx=(8, 0))

        # Resize option
        resize_row = ctk.CTkFrame(quality_inner, fg_color="transparent")
        resize_row.pack(fill="x", pady=(8, 0))

        self.resize_var = ctk.BooleanVar(value=True)
        self.resize_cb = ModernCheckbox(
            resize_row,
            text="Allow resize to meet size limits",
            variable=self.resize_var
        )
        self.resize_cb.pack(side="left", padx=(80, 0))

        # Register for theme updates
        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self._header_frame.configure(fg_color=T().bg_tertiary)
        self._formats_frame.configure(fg_color=T().bg_tertiary)
        self._quality_frame.configure(fg_color=T().bg_tertiary)

    def _set_dpi(self, dpi: int):
        self.dpi_entry.delete(0, "end")
        self.dpi_entry.insert(0, str(dpi))

    def _select_all(self):
        for config in self.format_configs.values():
            config['export'].set(True)

    def _select_none(self):
        for config in self.format_configs.values():
            config['export'].set(False)

    def _select_common(self):
        for fmt, config in self.format_configs.items():
            config['export'].set(fmt in ('png', 'jpg', 'pdf'))

    # === Public API (compatible with old ModernSizeLimitPanel) ===

    def get_selected_formats(self) -> Set[str]:
        """Get set of formats selected for export."""
        return {fmt for fmt, config in self.format_configs.items() if config['export'].get()}

    def get_dpi(self) -> int:
        try:
            return int(self.dpi_entry.get())
        except ValueError:
            return 300

    def get_quality(self) -> int:
        return self.quality_var.get()

    def get_allow_resize(self) -> bool:
        return self.resize_var.get()

    def get_limit_bytes(self, fmt: str) -> Optional[int]:
        """Get size limit in bytes for a format, or None if not limited."""
        config = self.format_configs.get(fmt.lower())
        if not config or not config['limit_enabled'].get():
            return None

        try:
            value = float(config['limit_entry'].get())
            unit = config['limit_unit'].get()
            multiplier = 1024 * 1024 if unit == "MB" else 1024
            return int(value * multiplier)
        except ValueError:
            return None

    def get_all_limits(self) -> Dict[str, int]:
        """Get dictionary of all enabled format limits in bytes."""
        limits = {}
        for fmt in self.format_configs:
            limit = self.get_limit_bytes(fmt)
            if limit is not None:
                limits[fmt] = limit
        return limits

    def get_state(self) -> dict:
        """Get panel state for saving."""
        state = {
            'dpi': self.dpi_entry.get(),
            'quality': self.quality_var.get(),
            'allow_resize': self.resize_var.get(),
            'formats': {}
        }
        for fmt, config in self.format_configs.items():
            state['formats'][fmt] = {
                'export': config['export'].get(),
                'limit_enabled': config['limit_enabled'].get(),
                'limit_value': config['limit_entry'].get(),
                'limit_unit': config['limit_unit'].get()
            }
        return state

    def set_state(self, state: dict):
        """Restore panel state."""
        if not state:
            return

        # Handle old state format (from ModernSizeLimitPanel)
        if 'enabled' in state and 'limits' in state:
            # Old format - convert
            self.resize_var.set(state.get('allow_resize', True))
            for fmt, limit_config in state.get('limits', {}).items():
                if fmt in self.format_configs:
                    self.format_configs[fmt]['limit_enabled'].set(limit_config.get('enabled', False))
                    self.format_configs[fmt]['limit_entry'].delete(0, 'end')
                    self.format_configs[fmt]['limit_entry'].insert(0, limit_config.get('value', '500'))
                    self.format_configs[fmt]['limit_unit'].set(limit_config.get('unit', 'KB'))
            return

        # New format
        self.dpi_entry.delete(0, 'end')
        self.dpi_entry.insert(0, state.get('dpi', '300'))
        self.quality_var.set(state.get('quality', 95))
        self.resize_var.set(state.get('allow_resize', True))

        for fmt, fmt_state in state.get('formats', {}).items():
            if fmt in self.format_configs:
                self.format_configs[fmt]['export'].set(fmt_state.get('export', False))
                self.format_configs[fmt]['limit_enabled'].set(fmt_state.get('limit_enabled', False))
                self.format_configs[fmt]['limit_entry'].delete(0, 'end')
                self.format_configs[fmt]['limit_entry'].insert(0, fmt_state.get('limit_value', '500'))
                self.format_configs[fmt]['limit_unit'].set(fmt_state.get('limit_unit', 'KB'))

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()


# Keep old class name as alias for compatibility
ModernSizeLimitPanel = ExportSettingsPanel
