"""
Part Drawing Generator - Main Application Class

Contains the PartDrawingGeneratorApp window class and all application logic
for both the Drawing Generator and File Converter tabs.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
import pickle
import json
import os
from pathlib import Path
from typing import Optional, Dict, List

# Import our modules
from modules.pdf_converter import get_image_from_template
from modules.excel_reader import read_excel_data, get_column_info
from modules.template_editor import (
    TextRegion, TemplateMapping, DrawingTemplate,
    FieldTemplate, TemplateLibraryManager,
    apply_template_mapping, get_font, measure_text, measure_text_bbox,
    save_image_multi_format, load_settings, save_settings
)
from modules.size_limits import save_image_with_size_limit
from modules.utils import sanitize_filename

from themes import T, ThemeManager, THEMES
from widgets import (
    ModernCard, ModernSection, ModernButton, ModernEntry, ModernLabel,
    ModernCheckbox, ModernDropdown, ThemedListbox, ThemedCanvas, StatusBar,
    SearchableComboBox
)
from panels import TemplateFieldsPanel, ExportSettingsPanel, TemplateEditorCanvas


# ============================================================================
# APP DATA DIRECTORY
# ============================================================================

def get_app_data_dir():
    """Get the application data directory for storing state files."""
    if os.name == 'nt':
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        state_dir = os.path.join(app_data, 'DrawingGenerator')
    else:
        state_dir = os.path.expanduser('~/.drawing_generator')
    os.makedirs(state_dir, exist_ok=True)
    return state_dir

STATE_FILE = os.path.join(get_app_data_dir(), 'saved_states.pkl')  # Legacy, for migration only
DGP_VERSION = "1.0"


# ============================================================================
# TEMPLATE MAPPING DIALOG
# ============================================================================

class TemplateMappingDialog(ctk.CTkToplevel):
    """Modal dialog for mapping template field names to current Excel columns."""

    def __init__(self, parent, template_name: str,
                 field_names: List[str], excel_columns: List[str],
                 field_regions: Dict):
        super().__init__(parent)

        self.result: Optional[Dict[str, str]] = None
        self._field_names = field_names
        self._excel_columns = excel_columns
        self._dropdown_vars: Dict[str, ctk.StringVar] = {}

        # Window setup
        self.title(f"Map Template: {template_name}")
        self.geometry("560x520")
        self.minsize(440, 400)
        self.resizable(True, True)
        self.configure(fg_color=T().bg_primary)
        self.transient(parent)
        self.grab_set()

        # Apply icon
        if hasattr(parent, '_set_dialog_icon'):
            parent._set_dialog_icon(self)

        self._build_ui(template_name)

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    def _build_ui(self, template_name: str):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 4))

        ModernLabel(header, text=f"Template: {template_name}", style="accent").pack(anchor="w")
        ModernLabel(
            header,
            text="Map each field to an Excel column. Matching names are auto-mapped.",
            style="dim"
        ).pack(anchor="w", pady=(4, 0))

        # Column headers
        col_header = ctk.CTkFrame(self, fg_color="transparent")
        col_header.pack(fill="x", padx=16, pady=(8, 0))
        ModernLabel(col_header, text="Template Field", style="dim", width=200, anchor="w").pack(side="left")
        ModernLabel(col_header, text="→", style="dim", width=24).pack(side="left")
        ModernLabel(col_header, text="Excel Column", style="dim", width=200, anchor="w").pack(side="left")

        # Scrollable mapping area
        scroll = ctk.CTkScrollableFrame(
            self, fg_color=T().bg_secondary, corner_radius=8, height=220,
            scrollbar_fg_color=T().bg_tertiary, scrollbar_button_color=T().accent_dim
        )
        scroll.pack(fill="both", expand=True, padx=16, pady=8)

        dropdown_values = ["(skip)"] + self._excel_columns
        excel_lower = {c.lower(): c for c in self._excel_columns}

        for field_name in self._field_names:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)

            # Field label
            display = field_name[:28] + "..." if len(field_name) > 28 else field_name
            ModernLabel(row, text=display, style="primary", width=200, anchor="w").pack(side="left")
            ModernLabel(row, text="→", style="dim", width=24).pack(side="left")

            # Auto-map: exact match (case-insensitive)
            var = ctk.StringVar(value="(skip)")
            if field_name in self._excel_columns:
                var.set(field_name)
            elif field_name.lower() in excel_lower:
                var.set(excel_lower[field_name.lower()])

            dropdown = ModernDropdown(row, values=dropdown_values, variable=var, width=220)
            dropdown.pack(side="left", padx=(4, 0))

            # Match indicator
            is_matched = var.get() != "(skip)"
            indicator = ModernLabel(row, text="✓" if is_matched else "", style="accent", width=20)
            indicator.pack(side="left", padx=4)

            self._dropdown_vars[field_name] = var

            # Update indicator when dropdown changes
            def _on_change(value, ind=indicator):
                ind.configure(text="✓" if value != "(skip)" else "")
            var.trace_add("write", lambda *_, v=var, ind=indicator: ind.configure(
                text="✓" if v.get() != "(skip)" else ""
            ))

        # Position auto-map checkbox
        self._position_var = ctk.BooleanVar(value=False)
        pos_cb = ctk.CTkCheckBox(
            self, text="Auto-map unmatched by column position",
            variable=self._position_var,
            command=self._on_position_toggle,
            font=ctk.CTkFont(size=11),
            text_color=T().text_dim,
            fg_color=T().accent,
            hover_color=T().accent_hover,
            border_color=T().border
        )
        pos_cb.pack(padx=16, pady=(0, 8), anchor="w")

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        ModernButton(btn_row, "Apply", self._on_apply, variant="primary", width=100).pack(side="right", padx=4)
        ModernButton(btn_row, "Cancel", self._on_cancel, variant="ghost", width=100).pack(side="right", padx=4)

    def _on_position_toggle(self):
        """Toggle auto-mapping unmatched fields by column position."""
        excel_lower = {c.lower(): c for c in self._excel_columns}

        for i, field_name in enumerate(self._field_names):
            var = self._dropdown_vars[field_name]
            # Only touch fields that weren't name-matched
            has_name_match = (field_name in self._excel_columns or
                              field_name.lower() in excel_lower)
            if has_name_match:
                continue

            if self._position_var.get():
                # Map by position
                if i < len(self._excel_columns):
                    var.set(self._excel_columns[i])
            else:
                # Reset to skip
                var.set("(skip)")

    def _on_apply(self):
        self.result = {}
        for field_name, var in self._dropdown_vars.items():
            col = var.get()
            if col != "(skip)":
                self.result[field_name] = col
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class PartDrawingGeneratorApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Part Drawing Generator")
        self.geometry("1500x950")
        self.minsize(1200, 700)

        # Set window icon
        self._set_window_icon()

        # Set initial theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # State
        self.template_path: Optional[str] = None
        self.excel_path: Optional[str] = None
        self.output_dir: str = "./output"
        self.template_image: Optional[Image.Image] = None
        self.excel_columns: List[str] = []
        self.excel_data: List[Dict] = []
        self.edited_data: Dict[int, Dict] = {}
        self.current_part_index: int = 0
        self.template_mapping: Optional[TemplateMapping] = None
        self.is_generating = False
        self.edit_entries: Dict[str, ctk.CTkEntry] = {}

        # Template library manager
        self._app_settings = load_settings(get_app_data_dir())
        library_path = self._app_settings.get("library_path", get_app_data_dir())
        self.template_mgr = TemplateLibraryManager(library_path)
        self._current_template_name: str = ""
        self._current_project_name: str = ""
        self._fields_dirty: bool = False
        self._modified_from_template: str = ""
        self._template_field_names: set = set()  # Fields that came from a drawing template

        self._setup_ui()
        self._migrate_pkl_to_dgp()
        self._migrate_templates_to_projects()
        # Refresh lists after migration (UI was populated before migration ran)
        self._refresh_saved_states()
        self._refresh_template_list()

    def _set_window_icon(self):
        """Set the window/taskbar icon from app_icon.ico."""
        import sys
        self.icon_path = None  # Store for child dialogs
        try:
            # When running as PyInstaller exe, look in the temp extraction dir
            if getattr(sys, '_MEIPASS', None):
                icon_path = os.path.join(sys._MEIPASS, 'app_icon.ico')
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_icon.ico')

            if os.path.isfile(icon_path):
                self.iconbitmap(icon_path)
                self.icon_path = icon_path
        except Exception:
            pass  # Silently skip if icon not found

    def _set_dialog_icon(self, dialog):
        """Apply the app icon to a child dialog window (multiple attempts to beat CTk's override)."""
        if self.icon_path:
            def _apply():
                try:
                    dialog.iconbitmap(self.icon_path)
                except Exception:
                    pass
            # CTkToplevel overwrites the icon during init — retry at multiple delays
            dialog.after(50, _apply)
            dialog.after(200, _apply)
            dialog.after(500, _apply)

    def _setup_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Title bar
        self._create_title_bar()

        # Main content area with tabs
        self._create_main_content()

        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def _create_title_bar(self):
        # Store reference to title frame for theme updates
        self._title_frame = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=T().bg_secondary)
        title_frame = self._title_frame
        title_frame.grid(row=0, column=0, sticky="ew")
        title_frame.grid_propagate(False)
        title_frame.grid_columnconfigure(1, weight=1)

        # App title with icon
        title_container = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_container.grid(row=0, column=0, padx=16, pady=10, sticky="w")

        # App icon - stylized stacked images representing batch generation
        icon_container = ctk.CTkFrame(title_container, width=36, height=30, fg_color="transparent")
        icon_container.pack(side="left", padx=(0, 12))
        icon_container.pack_propagate(False)

        # Back layer (lighter)
        back_layer = ctk.CTkFrame(icon_container, width=22, height=18, corner_radius=3, fg_color=T().accent_dim)
        back_layer.place(x=12, y=0)

        # Middle layer
        mid_layer = ctk.CTkFrame(icon_container, width=22, height=18, corner_radius=3, fg_color=T().accent_hover)
        mid_layer.place(x=6, y=6)

        # Front layer (main)
        front_layer = ctk.CTkFrame(icon_container, width=22, height=18, corner_radius=3, fg_color=T().accent)
        front_layer.place(x=0, y=12)

        self._icon_container = icon_container
        self._icon_layers = [back_layer, mid_layer, front_layer]

        # Title text
        self.title_label = ctk.CTkLabel(
            title_container,
            text="Drawing Generator",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=T().text_white
        )
        self.title_label.pack(side="left")

        # Separator dot
        self.sep_label = ctk.CTkLabel(
            title_container,
            text="·",
            font=ctk.CTkFont(size=16),
            text_color=T().text_dim
        )
        self.sep_label.pack(side="left", padx=8)

        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            title_container,
            text="Image Generator",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=T().text_dim
        )
        self.subtitle_label.pack(side="left")

        # Theme selector (right side)
        theme_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        theme_frame.grid(row=0, column=2, padx=16, pady=12, sticky="e")

        self.theme_var = ctk.StringVar(value="Obsidian")
        theme_names = [t.name for t in THEMES.values()]
        self.theme_dropdown = ModernDropdown(
            theme_frame,
            values=theme_names,
            variable=self.theme_var,
            command=self._on_theme_change,
            width=140
        )
        self.theme_dropdown.pack(side="left")

        ThemeManager.register(self._update_title_theme)

    def _update_title_theme(self):
        # Update icon layers and titles
        if hasattr(self, '_icon_layers') and len(self._icon_layers) >= 3:
            self._icon_layers[0].configure(fg_color=T().accent_dim)
            self._icon_layers[1].configure(fg_color=T().accent_hover)
            self._icon_layers[2].configure(fg_color=T().accent)
        self.title_label.configure(text_color=T().text_white)
        self.subtitle_label.configure(text_color=T().text_dim)
        if hasattr(self, 'sep_label'):
            self.sep_label.configure(text_color=T().text_dim)

        # Update main window background
        self.configure(fg_color=T().bg_primary)

        # Update title frame
        if hasattr(self, '_title_frame'):
            self._title_frame.configure(fg_color=T().bg_secondary)

        # Update scrollable frames with all theme colors
        scroll_config = {
            'fg_color': T().bg_tertiary,
            'scrollbar_fg_color': T().bg_tertiary,
            'scrollbar_button_color': T().accent_dim,
            'scrollbar_button_hover_color': T().accent
        }
        transparent_scroll_config = {
            'fg_color': 'transparent',
            'scrollbar_fg_color': T().bg_tertiary,
            'scrollbar_button_color': T().accent_dim,
            'scrollbar_button_hover_color': T().accent
        }
        if hasattr(self, '_unified_scroll'):
            self._unified_scroll.configure(**transparent_scroll_config)
        if hasattr(self, '_conv_scroll'):
            self._conv_scroll.configure(**scroll_config)

        # Update files card
        if hasattr(self, '_files_card'):
            self._files_card.configure(fg_color=T().bg_secondary)

        # Update project card
        if hasattr(self, '_project_card'):
            self._project_card.configure(fg_color=T().bg_secondary)

        # Update status bar
        if hasattr(self, 'status_bar'):
            self.status_bar.configure(fg_color=T().bg_secondary)

        # Update tabview colors
        if hasattr(self, 'tabview'):
            self.tabview.configure(
                fg_color=T().bg_primary,
                segmented_button_fg_color=T().bg_secondary,
                segmented_button_selected_color=T().accent_dim,
                segmented_button_selected_hover_color=T().accent_hover,
                segmented_button_unselected_color=T().bg_tertiary,
                segmented_button_unselected_hover_color=T().bg_hover
            )

        # Update canvas cards
        if hasattr(self, '_canvas_card'):
            self._canvas_card.configure(fg_color=T().bg_secondary, border_color=T().border)
        if hasattr(self, '_preview_card'):
            self._preview_card.configure(fg_color=T().bg_secondary, border_color=T().border)

        # Update edit fields scrollable frame
        if hasattr(self, '_edit_fields_scroll'):
            self._edit_fields_scroll.configure(
                fg_color=T().bg_tertiary,
                scrollbar_fg_color=T().bg_secondary,
                scrollbar_button_color=T().accent_dim
            )

    def _on_theme_change(self, value):
        for key, theme in THEMES.items():
            if theme.name == value:
                ThemeManager.set(key)
                self.status_bar.set_status(f"Theme: {value}")
                break

    def _create_main_content(self):
        # Tabview
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color=T().bg_primary,
            segmented_button_fg_color=T().bg_secondary,
            segmented_button_selected_color=T().accent,
            segmented_button_selected_hover_color=T().accent_hover,
            segmented_button_unselected_color=T().bg_tertiary,
            segmented_button_unselected_hover_color=T().bg_hover,
            text_color="#FFFFFF",
            text_color_disabled=T().tab_unselected_text
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        # Create tabs
        self.tab_generator = self.tabview.add("  Drawing Generator  ")
        self.tab_converter = self.tabview.add("  File Converter  ")

        # Setup each tab
        self._setup_generator_tab()
        self._setup_converter_tab()

        ThemeManager.register(self._update_tabview_theme)

    def _update_tabview_theme(self):
        self.tabview.configure(
            fg_color=T().bg_primary,
            segmented_button_fg_color=T().bg_secondary,
            segmented_button_selected_color=T().accent,
            segmented_button_selected_hover_color=T().accent_hover,
            segmented_button_unselected_color=T().bg_tertiary,
            segmented_button_unselected_hover_color=T().bg_hover,
            text_color="#FFFFFF",
            text_color_disabled=T().tab_unselected_text
        )

    def _setup_generator_tab(self):
        """Setup the Drawing Generator tab."""
        self.tab_generator.grid_columnconfigure(1, weight=1)
        self.tab_generator.grid_rowconfigure(0, weight=1)

        # Left panel container
        left_frame = ctk.CTkFrame(self.tab_generator, width=420, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_frame.grid_rowconfigure(2, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        # === FILES Section (always visible at top) ===
        files_card = ctk.CTkFrame(left_frame, fg_color=T().bg_secondary, corner_radius=8)
        files_card.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self._files_card = files_card

        files_section = ModernSection(files_card, "FILES", "◈")
        files_section.pack(fill="x", padx=4, pady=4)

        # Template file
        template_row = ctk.CTkFrame(files_section.content, fg_color="transparent")
        template_row.pack(fill="x", pady=6)

        ModernLabel(template_row, text="Template:", style="dim", width=80, anchor="e").pack(side="left")
        self.template_entry = ModernEntry(template_row, placeholder="Select PDF or image...")
        self.template_entry.pack(side="left", padx=8, expand=True, fill="x")
        ModernButton(template_row, "...", self._browse_template, variant="secondary", width=40, height=32).pack(side="right")

        # Excel file
        excel_row = ctk.CTkFrame(files_section.content, fg_color="transparent")
        excel_row.pack(fill="x", pady=6)

        ModernLabel(excel_row, text="Excel:", style="dim", width=80, anchor="e").pack(side="left")
        self.excel_entry = ModernEntry(excel_row, placeholder="Select Excel file...")
        self.excel_entry.pack(side="left", padx=8, expand=True, fill="x")
        ModernButton(excel_row, "...", self._browse_excel, variant="secondary", width=40, height=32).pack(side="right")

        # Output folder
        output_row = ctk.CTkFrame(files_section.content, fg_color="transparent")
        output_row.pack(fill="x", pady=6)

        ModernLabel(output_row, text="Output:", style="dim", width=80, anchor="e").pack(side="left")
        self.output_entry = ModernEntry(output_row, placeholder="./output")
        self.output_entry.insert(0, "./output")
        self.output_entry.pack(side="left", padx=8, expand=True, fill="x")
        ModernButton(output_row, "...", self._browse_output, variant="secondary", width=40, height=32).pack(side="right")

        # === PROJECT CARD (fixed, always visible) ===
        self._project_card = ctk.CTkFrame(left_frame, fg_color=T().bg_secondary, corner_radius=8)
        self._project_card.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        proj_header = ctk.CTkFrame(self._project_card, fg_color="transparent")
        proj_header.pack(fill="x", padx=8, pady=(6, 2))
        ModernLabel(proj_header, text="PROJECT", style="dim").pack(side="left")
        ModernButton(proj_header, "Save As", self._save_as_project, variant="ghost", width=60, height=24).pack(side="right", padx=2)
        ModernButton(proj_header, "Save", self._save_state, variant="secondary", width=50, height=24).pack(side="right", padx=2)

        proj_sel_row = ctk.CTkFrame(self._project_card, fg_color="transparent")
        proj_sel_row.pack(fill="x", padx=8, pady=(2, 2))
        self._project_combo = SearchableComboBox(
            proj_sel_row, values=[], width=240,
            command=lambda v: None  # no-op; user must click Load
        )
        self._project_combo.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._project_combo.set("")
        self._project_combo._entry.bind("<Return>", lambda e: self._load_state())
        ModernButton(proj_sel_row, "Load", self._load_state, variant="secondary", width=50, height=28).pack(side="left", padx=2)
        ModernButton(proj_sel_row, "Delete", self._delete_state, variant="ghost", width=55, height=28).pack(side="left", padx=2)

        proj_info_row = ctk.CTkFrame(self._project_card, fg_color="transparent")
        proj_info_row.pack(fill="x", padx=8, pady=(0, 6))
        self._project_info_label = ModernLabel(proj_info_row, text="No fields placed", style="dim")
        self._project_info_label.pack(side="left")

        # === UNIFIED SCROLL (single workflow) ===
        unified_scroll = ctk.CTkScrollableFrame(
            left_frame, fg_color="transparent",
            scrollbar_fg_color=T().bg_tertiary,
            scrollbar_button_color=T().accent_dim,
            scrollbar_button_hover_color=T().accent
        )
        self._unified_scroll = unified_scroll
        unified_scroll.grid(row=2, column=0, sticky="nsew")

        # ── 1. DRAWING TEMPLATES ──
        lib_section = ModernSection(unified_scroll, "DRAWING TEMPLATES", "◈")
        lib_section.pack(fill="x", pady=(0, 12))

        # Shared folder path
        lib_path_row = ctk.CTkFrame(lib_section.content, fg_color="transparent")
        lib_path_row.pack(fill="x", pady=4)
        ModernLabel(lib_path_row, text="Folder:", style="dim", width=50).pack(side="left")
        ModernButton(lib_path_row, "Browse", self._browse_library_path, variant="secondary", width=60, height=28).pack(side="right")
        shared_root = self._app_settings.get("library_path", get_app_data_dir())
        self._lib_path_label = ModernLabel(lib_path_row, text=self._truncate_path(shared_root), style="primary")
        self._lib_path_label.pack(side="left", padx=4, fill="x", expand=True)
        self._lib_path_full = shared_root
        self._lib_path_label.bind("<Enter>", lambda e: self._show_path_tooltip(e))
        self._lib_path_label.bind("<Leave>", lambda e: self._hide_path_tooltip())

        self._file_count_label = ModernLabel(lib_section.content, text="", style="dim")
        self._file_count_label.pack(anchor="w", pady=(0, 4))

        tmpl_combo_row = ctk.CTkFrame(lib_section.content, fg_color="transparent")
        tmpl_combo_row.pack(fill="x", pady=4)
        self._tmpl_combo = SearchableComboBox(
            tmpl_combo_row, values=[], width=280,
            command=lambda v: None
        )
        self._tmpl_combo.pack(side="left", fill="x", expand=True)
        self._tmpl_combo.set("")
        self._tmpl_combo._entry.bind("<Return>", lambda e: self._load_template())

        tmpl_btns = ctk.CTkFrame(lib_section.content, fg_color="transparent")
        tmpl_btns.pack(fill="x", pady=4)
        ModernButton(tmpl_btns, "New", self._new_template, variant="secondary", width=55).pack(side="left", padx=2)
        ModernButton(tmpl_btns, "Save", self._save_template, variant="primary", width=55).pack(side="left", padx=2)
        ModernButton(tmpl_btns, "Apply", self._load_template, variant="secondary", width=55).pack(side="left", padx=2)
        ModernButton(tmpl_btns, "Delete", self._delete_template, variant="ghost", width=55).pack(side="left", padx=2)

        # ── 3. FIELD PLACEMENT ──
        field_section = ModernSection(unified_scroll, "FIELD PLACEMENT", "◈")
        field_section.pack(fill="x", pady=(0, 12))

        mode_row = ctk.CTkFrame(field_section.content, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 6))
        ModernLabel(mode_row, text="Place as:", style="dim").pack(side="left")
        self._placement_mode = ctk.StringVar(value="template")
        self._tmpl_mode_btn = ctk.CTkRadioButton(
            mode_row, text="Template Field", variable=self._placement_mode, value="template",
            font=ctk.CTkFont(size=11), text_color=T().accent,
            fg_color=T().accent, hover_color=T().accent_hover, border_color=T().border,
            command=self._on_placement_mode_change
        )
        self._tmpl_mode_btn.pack(side="left", padx=(8, 4))
        self._custom_mode_btn = ctk.CTkRadioButton(
            mode_row, text="Custom Field", variable=self._placement_mode, value="custom",
            font=ctk.CTkFont(size=11), text_color="#6B8E6B",
            fg_color="#6B8E6B", hover_color="#5A7A5A", border_color=T().border,
            command=self._on_placement_mode_change
        )
        self._custom_mode_btn.pack(side="left", padx=4)

        self._placement_hint = ModernLabel(field_section.content,
                    text="Select a column, then click the drawing to place it.",
                    style="dim", wraplength=280)
        self._placement_hint.pack(anchor="w", pady=(0, 8))

        self.fields_panel = TemplateFieldsPanel(
            field_section.content,
            on_column_select=self._on_column_select,
            on_column_double_click=self._on_column_double_click,
            on_region_select=self._on_region_list_select,
            on_field_change=self._on_text_editor_change
        )
        self.fields_panel.pack(fill="x")

        field_btns = ctk.CTkFrame(field_section.content, fg_color="transparent")
        field_btns.pack(fill="x", pady=(8, 0))
        ModernButton(field_btns, "Clear", self._clear_fields, variant="ghost", width=70).pack(side="left", padx=2)
        ModernButton(field_btns, "Export", self._export_dgt, variant="ghost", width=70).pack(side="left", padx=2)
        ModernButton(field_btns, "Import", self._import_dgt, variant="ghost", width=70).pack(side="left", padx=2)

        # ── 4. EXPORT SETTINGS ──
        export_section = ModernSection(unified_scroll, "EXPORT SETTINGS", "◈")
        export_section.pack(fill="x", pady=(0, 12))

        self.export_settings_panel = ExportSettingsPanel(export_section.content)
        self.export_settings_panel.pack(fill="x")

        # ── 5. PART PREVIEW ──
        preview_section = ModernSection(unified_scroll, "PART PREVIEW", "◈")
        preview_section.pack(fill="x", pady=(0, 12))

        selector_row = ctk.CTkFrame(preview_section.content, fg_color="transparent")
        selector_row.pack(fill="x", pady=4)
        ModernLabel(selector_row, text="Part:", style="dim", width=50).pack(side="left")
        self.part_selector_var = ctk.StringVar(value="1")
        self.part_selector = ModernEntry(selector_row, width=60)
        self.part_selector.insert(0, "1")
        self.part_selector.pack(side="left", padx=4)
        self.part_selector.bind("<Return>", lambda e: self._on_part_selected())

        self.part_total_label = ModernLabel(selector_row, text="of 0", style="dim")
        self.part_total_label.pack(side="left", padx=8)
        ModernButton(selector_row, "◀", self._prev_part, variant="ghost", width=32, height=28).pack(side="left", padx=2)
        ModernButton(selector_row, "▶", self._next_part, variant="ghost", width=32, height=28).pack(side="left", padx=2)

        self.part_id_label = ModernLabel(preview_section.content, text="Part ID: --", style="accent")
        self.part_id_label.pack(fill="x", pady=(8, 4))

        ModernLabel(preview_section.content, text="Edit Values (modify before generating):", style="dim").pack(anchor="w", pady=(4, 4))

        self.edit_fields_frame = ctk.CTkScrollableFrame(
            preview_section.content, height=100,
            fg_color=T().bg_tertiary, corner_radius=6,
            scrollbar_fg_color=T().bg_secondary,
            scrollbar_button_color=T().accent_dim
        )
        self.edit_fields_frame.pack(fill="x", pady=4)
        self._edit_fields_scroll = self.edit_fields_frame

        preview_btn_row = ctk.CTkFrame(preview_section.content, fg_color="transparent")
        preview_btn_row.pack(fill="x", pady=(8, 0))
        self.apply_edits_btn = ModernButton(preview_btn_row, "Apply Edits", self._apply_edits, variant="secondary", width=100, height=28)
        self.apply_edits_btn.pack(side="left", padx=2)
        self.apply_edits_btn.configure(state="disabled")
        self.generate_one_btn = ModernButton(preview_btn_row, "Generate This", self._generate_single, variant="secondary", width=110, height=28)
        self.generate_one_btn.pack(side="left", padx=2)

        # ── 6. GENERATE ──
        gen_section = ModernSection(unified_scroll, "GENERATE", "◈")
        gen_section.pack(fill="x", pady=(0, 12))

        range_row = ctk.CTkFrame(gen_section.content, fg_color="transparent")
        range_row.pack(fill="x", pady=4)
        ModernLabel(range_row, text="Range:", style="dim", width=50).pack(side="left")
        self.range_from_var = ctk.StringVar(value="1")
        self.range_from_entry = ModernEntry(range_row, width=60)
        self.range_from_entry.insert(0, "1")
        self.range_from_entry.pack(side="left", padx=4)
        ModernLabel(range_row, text="to", style="dim").pack(side="left", padx=4)
        self.range_to_var = ctk.StringVar(value="")
        self.range_to_entry = ModernEntry(range_row, width=60)
        self.range_to_entry.pack(side="left", padx=4)
        ModernLabel(range_row, text="(blank = all)", style="dim").pack(side="left", padx=8)

        gen_btn_row = ctk.CTkFrame(gen_section.content, fg_color="transparent")
        gen_btn_row.pack(fill="x", pady=(8, 0))
        self.generate_btn = ModernButton(gen_btn_row, "Generate All", self._generate_images, variant="primary", width=120)
        self.generate_btn.pack(side="left", padx=4)
        self.generate_range_btn = ModernButton(gen_btn_row, "Generate Range", self._generate_range, variant="secondary", width=120)
        self.generate_range_btn.pack(side="left", padx=4)

        self._refresh_template_list()

        # Right side - Canvas only (full width)
        right_frame = ctk.CTkFrame(self.tab_generator, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Canvas area
        self._canvas_card = ModernCard(right_frame)
        canvas_card = self._canvas_card
        canvas_card.grid(row=0, column=0, sticky="nsew")
        canvas_card.grid_rowconfigure(0, weight=1)
        canvas_card.grid_columnconfigure(0, weight=1)

        self.editor_canvas = TemplateEditorCanvas(canvas_card, on_region_changed=self._on_region_changed)
        self.editor_canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # Initialize
        self._all_saved_states = []
        self._refresh_saved_states()

    def _setup_converter_tab(self):
        """Setup the File Converter tab."""
        self.tab_converter.grid_columnconfigure(1, weight=1)
        self.tab_converter.grid_rowconfigure(0, weight=1)

        # Left panel
        left_frame = ctk.CTkScrollableFrame(
            self.tab_converter,
            width=420,
            corner_radius=8,
            fg_color=T().bg_secondary,
            scrollbar_fg_color=T().bg_tertiary,
            scrollbar_button_color=T().accent_dim,
            scrollbar_button_hover_color=T().accent
        )
        self._conv_scroll = left_frame  # Store reference for theme updates
        left_frame.grid(row=0, column=0, sticky="ns", padx=(0, 8))

        # === INPUT FILES Section ===
        input_section = ModernSection(left_frame, "INPUT FILES", "◈")
        input_section.pack(fill="x", pady=(0, 20))

        # File listbox
        self.conv_file_listbox = ThemedListbox(
            input_section.content,
            height=8,
            selectmode=tk.EXTENDED
        )
        self.conv_file_listbox.pack(fill="x", pady=4)
        self.conv_file_listbox.bind('<<ListboxSelect>>', self._conv_on_file_select)

        # File buttons
        file_btns = ctk.CTkFrame(input_section.content, fg_color="transparent")
        file_btns.pack(fill="x", pady=4)

        ModernButton(file_btns, "Add Files", self._conv_add_files, variant="primary", width=90).pack(side="left", padx=2)
        ModernButton(file_btns, "Add Folder", self._conv_add_folder, variant="secondary", width=90).pack(side="left", padx=2)
        ModernButton(file_btns, "Remove", self._conv_remove_files, variant="ghost", width=70).pack(side="left", padx=2)
        ModernButton(file_btns, "Clear", self._conv_clear_files, variant="ghost", width=60).pack(side="left", padx=2)

        self.conv_file_count_label = ModernLabel(input_section.content, text="0 files selected", style="dim")
        self.conv_file_count_label.pack(anchor="w", pady=4)

        # === OUTPUT Section ===
        output_section = ModernSection(left_frame, "OUTPUT", "◈")
        output_section.pack(fill="x", pady=(0, 20))

        out_row = ctk.CTkFrame(output_section.content, fg_color="transparent")
        out_row.pack(fill="x", pady=4)

        self.conv_output_entry = ModernEntry(out_row, placeholder="Output folder...", width=260)
        self.conv_output_entry.pack(side="left", fill="x", expand=True)
        ModernButton(out_row, "...", self._conv_browse_output, variant="secondary", width=36).pack(side="right", padx=(8, 0))

        self.conv_same_folder_var = ctk.BooleanVar(value=True)
        self.conv_same_folder_cb = ModernCheckbox(
            output_section.content,
            text="Save to same folder as source",
            variable=self.conv_same_folder_var,
            command=self._conv_toggle_output
        )
        self.conv_same_folder_cb.pack(anchor="w", pady=4)

        # === EXPORT SETTINGS Section (unified formats, quality, and size limits) ===
        export_section = ModernSection(left_frame, "EXPORT SETTINGS", "◈")
        export_section.pack(fill="x", pady=(0, 20))

        self.conv_export_panel = ExportSettingsPanel(export_section.content)
        self.conv_export_panel.pack(fill="x")

        # Right panel - Preview
        right_frame = ctk.CTkFrame(self.tab_converter, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        self._preview_card = ModernCard(right_frame)
        preview_card = self._preview_card
        preview_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        preview_card.grid_rowconfigure(0, weight=1)
        preview_card.grid_columnconfigure(0, weight=1)

        self.conv_preview_canvas = ThemedCanvas(preview_card)
        self.conv_preview_canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.conv_preview_photo = None

        self.conv_preview_label = ModernLabel(preview_card, text="Select a file to preview", style="dim")
        self.conv_preview_label.place(relx=0.5, rely=0.5, anchor="center")

        # Convert button
        btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent", height=50)
        btn_frame.grid(row=1, column=0, sticky="ew")

        self.convert_btn = ModernButton(btn_frame, "CONVERT FILES", self._conv_start_conversion, variant="primary", width=200, height=44)
        self.convert_btn.pack(pady=8)

        self.conv_progress_label = ModernLabel(btn_frame, text="", style="dim")
        self.conv_progress_label.pack()

        # Initialize state
        self._conv_toggle_output()

    # ========================================================================
    # DRAWING GENERATOR METHODS
    # ========================================================================

    def _browse_template(self):
        path = filedialog.askopenfilename(
            title="Select Template",
            filetypes=[("PDF/Image", "*.pdf *.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if path:
            self.template_entry.delete(0, "end")
            self.template_entry.insert(0, path)
            self._try_auto_load()

    def _browse_excel(self):
        path = filedialog.askopenfilename(
            title="Select Data File",
            filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("Excel", "*.xlsx *.xls"), ("CSV", "*.csv"), ("All", "*.*")]
        )
        if path:
            self.excel_entry.delete(0, "end")
            self.excel_entry.insert(0, path)
            self._try_auto_load()

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)
            self.output_dir = path

    def _try_auto_load(self):
        template = self.template_entry.get().strip()
        excel = self.excel_entry.get().strip()
        if template and excel and os.path.exists(template) and os.path.exists(excel):
            self._load_files()

    def _load_files(self):
        self.template_path = self.template_entry.get().strip()
        self.excel_path = self.excel_entry.get().strip()

        output_val = self.output_entry.get().strip()
        if not output_val or output_val == "./output":
            if self.template_path:
                self.output_dir = os.path.join(os.path.dirname(self.template_path), "output")
                self.output_entry.delete(0, "end")
                self.output_entry.insert(0, self.output_dir)
        else:
            self.output_dir = os.path.abspath(output_val)

        if not self.template_path or not self.excel_path:
            return

        self.status_bar.set_status("Loading...")

        try:
            dpi = self.export_settings_panel.get_dpi()
            self.template_image = get_image_from_template(self.template_path, dpi=dpi)
            self.editor_canvas.load_image(self.template_image, dpi=dpi)

            import pandas as pd
            ext = os.path.splitext(self.excel_path)[1].lower()
            if ext == '.csv':
                df = pd.read_csv(self.excel_path, dtype=str).fillna('')
            else:
                df = pd.read_excel(self.excel_path, dtype=str, engine='openpyxl').fillna('')
            self.excel_columns = list(df.columns)
            self.excel_data = df.to_dict('records')

            # Populate fields panel with actual Excel column names
            self.fields_panel.column_listbox.delete(0, "end")
            for col in self.excel_columns:
                self.fields_panel.column_listbox.insert("end", col)

            if self.excel_data:
                self.editor_canvas.set_sample_data(self.excel_data[0])

            # Preserve existing field placements if we have them (e.g. from a loaded state)
            existing_regions = {}
            if self.template_mapping and self.template_mapping.regions:
                existing_regions = self.template_mapping.regions

            self.template_mapping = TemplateMapping(
                template_name=Path(self.template_path).stem,
                template_path=self.template_path,
                regions=existing_regions,
                dpi=dpi
            )
            self.editor_canvas.set_regions(self.template_mapping.regions)

            self.edited_data = {}
            self.current_part_index = 0
            total = len(self.excel_data)
            self.part_total_label.configure(text=f"of {total}")
            self.part_selector_var.set("1")
            self._update_part_preview()

            self.status_bar.set_status(f"Loaded: {len(self.excel_columns)} columns, {len(self.excel_data)} rows")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_bar.set_status(f"Error: {str(e)}", is_error=True)

    def _on_placement_mode_change(self):
        """Update hint text when placement mode changes."""
        mode = self._placement_mode.get()
        if mode == "template":
            self._placement_hint.configure(text="Select a column, then click the drawing to place a template field.")
        else:
            self._placement_hint.configure(text="Select a column, then click the drawing to place a custom field.")

    def _on_column_select(self, event=None):
        """Place a field from the Template tab's column list."""
        selection = self.fields_panel.column_listbox.curselection()
        if not selection or not self.template_image:
            return

        column_name = self.excel_columns[selection[0]]

        if self.template_mapping and column_name in self.template_mapping.regions:
            self.editor_canvas.selected_region = column_name
            self.editor_canvas._update_display()
            self.status_bar.set_status(f"'{column_name}' already placed. Double-click to replace.")
            return

        mode = self._placement_mode.get() if hasattr(self, '_placement_mode') else "template"
        mode_label = "template" if mode == "template" else "custom"
        self._pending_place_column = column_name
        self.editor_canvas.set_mode("place", column_name)
        self.status_bar.set_status(f"Click on drawing to place '{column_name}' as {mode_label} field")
        self.fields_panel.instructions_label.configure(text=f"Click where you want '{column_name}' ({mode_label})")

    def _on_column_double_click(self, event=None):
        selection = self.fields_panel.column_listbox.curselection()
        if not selection or not self.template_image:
            return

        column_name = self.excel_columns[selection[0]]
        if self.template_mapping and column_name in self.template_mapping.regions:
            # Remove from template_field_names if it was there
            self._template_field_names.discard(column_name)
            del self.template_mapping.regions[column_name]
            self.editor_canvas.regions = self.template_mapping.regions
            self.editor_canvas._render_preview()

        mode = self._placement_mode.get() if hasattr(self, '_placement_mode') else "template"
        self._pending_place_column = column_name
        self.editor_canvas.set_mode("place", column_name)
        self.status_bar.set_status(f"Click on drawing to place '{column_name}'")

    def _on_region_changed(self):
        if self.template_mapping:
            # Detect newly placed field and track based on placement mode
            new_names = set(self.editor_canvas.regions.keys()) - set(self.template_mapping.regions.keys())
            self.template_mapping.regions = self.editor_canvas.regions.copy()

            if new_names and not getattr(self, '_loading_template', False):
                mode = self._placement_mode.get() if hasattr(self, '_placement_mode') else "template"
                for name in new_names:
                    if mode == "template":
                        self._template_field_names.add(name)
                    else:
                        self._template_field_names.discard(name)
                self._sync_template_field_visuals()

            # Clean up template_field_names for removed regions
            current_keys = set(self.editor_canvas.regions.keys())
            removed = self._template_field_names - current_keys
            if removed:
                self._template_field_names -= removed
                self._sync_template_field_visuals()
        else:
            new_names = set()

        # Skip dirty tracking during programmatic template/project loading
        if not getattr(self, '_loading_template', False):
            if not self._fields_dirty and self._current_template_name:
                # First modification — template is no longer the saved version
                self._modified_from_template = self._current_template_name
                self._current_template_name = ""
                # Clear template combo to show it's modified
                self._tmpl_combo.set("")

            self._fields_dirty = True

        # Update active template indicator
        self._update_active_labels()

        # Update the fields panel
        all_regions = self.editor_canvas.regions
        selected = self.editor_canvas.selected_region

        self.fields_panel.update_regions(all_regions, selected)

        # Update properties
        if selected:
            region = all_regions.get(selected)
            if region:
                if hasattr(region, '_delete_requested') and region._delete_requested:
                    self._template_field_names.discard(selected)
                    del self.editor_canvas.regions[selected]
                    self.editor_canvas.selected_region = None
                    self.fields_panel.set_region(None)
                    self.editor_canvas._render_preview()
                    self._sync_template_field_visuals()
                    self._on_region_changed()
                    return
                self.fields_panel.set_region(region)
        else:
            self.fields_panel.set_region(None)

        self._update_part_preview()

    def _on_region_list_select(self, name: str):
        """Called when a region is selected from the panel's placed list."""
        if name in self.editor_canvas.regions:
            self.editor_canvas.selected_region = name
            self.editor_canvas._update_display()
            region = self.editor_canvas.regions[name]

            self.fields_panel.update_regions(self.editor_canvas.regions, name)
            self.fields_panel.set_region(region)

    def _on_text_editor_change(self):
        """Called when text properties are changed in the panel."""
        current = self.fields_panel.current_region if hasattr(self, 'fields_panel') else None

        if current:
            if hasattr(current, '_delete_requested') and current._delete_requested:
                name = current.column_name
                self._template_field_names.discard(name)
                if name in self.editor_canvas.regions:
                    del self.editor_canvas.regions[name]
                self.editor_canvas.selected_region = None
                self.fields_panel.set_region(None)
                self._sync_template_field_visuals()

            self.editor_canvas._render_preview()
            self._on_region_changed()

    def _prev_part(self):
        """Navigate to previous part."""
        if self.current_part_index > 0:
            self.current_part_index -= 1
            self.part_selector.delete(0, "end")
            self.part_selector.insert(0, str(self.current_part_index + 1))
            self._update_part_preview()

    def _next_part(self):
        """Navigate to next part."""
        if self.excel_data and self.current_part_index < len(self.excel_data) - 1:
            self.current_part_index += 1
            self.part_selector.delete(0, "end")
            self.part_selector.insert(0, str(self.current_part_index + 1))
            self._update_part_preview()

    def _on_part_selected(self):
        if not self.excel_data:
            return
        try:
            part_num = max(1, min(int(self.part_selector.get()), len(self.excel_data)))
            self.part_selector.delete(0, "end")
            self.part_selector.insert(0, str(part_num))
            self.current_part_index = part_num - 1
            self._update_part_preview()
        except ValueError:
            self.part_selector.delete(0, "end")
            self.part_selector.insert(0, "1")
            self.current_part_index = 0

    def _update_part_preview(self):
        if not self.excel_data:
            return

        idx = self.current_part_index
        if idx < 0 or idx >= len(self.excel_data):
            return

        row_data = self.edited_data.get(idx, self.excel_data[idx])
        first_col = self.excel_columns[0] if self.excel_columns else None
        part_id = row_data.get(first_col, f"Part {idx + 1}") if first_col else f"Part {idx + 1}"
        self.part_id_label.configure(text=f"ID: {part_id}")
        self.editor_canvas.set_sample_data(row_data)

        # Update edit fields
        self._populate_edit_fields(row_data)

    def _populate_edit_fields(self, row_data: Dict):
        """Populate the edit fields with current row data."""
        # Clear existing widgets
        for widget in self.edit_fields_frame.winfo_children():
            widget.destroy()
        self.edit_entries = {}

        if not row_data or not self.template_mapping:
            return

        # Only show fields that are placed on the template
        placed_columns = set(self.template_mapping.regions.keys())

        for col_name in self.excel_columns:
            if col_name not in placed_columns:
                continue

            row = ctk.CTkFrame(self.edit_fields_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            # Label (truncate if too long)
            display_name = col_name[:12] + ".." if len(col_name) > 12 else col_name
            label = ctk.CTkLabel(
                row,
                text=display_name + ":",
                font=ctk.CTkFont(size=11),
                text_color=T().text_dim,
                width=90,
                anchor="e"
            )
            label.pack(side="left", padx=(0, 4))

            # Entry - fills remaining space
            entry = ctk.CTkEntry(
                row,
                height=28,
                font=ctk.CTkFont(size=11),
                fg_color=T().bg_secondary,
                border_color=T().border,
                text_color=T().text_white
            )
            value = str(row_data.get(col_name, ""))
            if value.lower() == 'nan':
                value = ""
            entry.insert(0, value)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

            self.edit_entries[col_name] = entry

        # Enable apply button if there are editable fields
        if self.edit_entries:
            self.apply_edits_btn.configure(state="normal")
        else:
            self.apply_edits_btn.configure(state="disabled")

    def _apply_edits(self):
        """Apply edited values to the current part."""
        if not self.excel_data or not self.edit_entries:
            return

        idx = self.current_part_index
        if idx < 0 or idx >= len(self.excel_data):
            return

        # Get edited values
        edited = {}
        for col_name, entry in self.edit_entries.items():
            edited[col_name] = entry.get()

        # Merge with original data
        original = self.excel_data[idx].copy()
        original.update(edited)
        self.edited_data[idx] = original

        # Update preview
        self.editor_canvas.set_sample_data(original)
        self.status_bar.set_status(f"Edits applied to part {idx + 1}")

    def _generate_range(self):
        """Generate images for a range of parts."""
        if self.is_generating or not self.template_mapping or not self.excel_data:
            return

        # Prompt to save unsaved template
        if not self._check_unsaved_template():
            return

        # Parse range
        try:
            from_idx = int(self.range_from_entry.get() or "1") - 1
        except ValueError:
            from_idx = 0

        to_str = self.range_to_entry.get().strip()
        if to_str:
            try:
                to_idx = int(to_str) - 1
            except ValueError:
                to_idx = len(self.excel_data) - 1
        else:
            to_idx = len(self.excel_data) - 1

        # Validate
        from_idx = max(0, min(from_idx, len(self.excel_data) - 1))
        to_idx = max(from_idx, min(to_idx, len(self.excel_data) - 1))

        count = to_idx - from_idx + 1
        if not messagebox.askyesno("Confirm", f"Generate {count} images (parts {from_idx + 1} to {to_idx + 1})?"):
            return

        self.is_generating = True
        self.generate_btn.configure(state="disabled")
        self.generate_range_btn.configure(state="disabled")

        # Capture export settings on main thread for thread safety
        export_config = {
            'formats': self._get_selected_formats() or {'png'},
            'dpi': self.export_settings_panel.get_dpi(),
            'quality': self.export_settings_panel.get_quality(),
            'size_limits': self.export_settings_panel.get_all_limits(),
            'allow_resize': self.export_settings_panel.get_allow_resize()
        }
        threading.Thread(target=self._generate_thread, args=(from_idx, to_idx, export_config), daemon=True).start()

    def _get_selected_formats(self) -> set:
        """Get selected export formats from the unified export settings panel."""
        return self.export_settings_panel.get_selected_formats()

    def _generate_single(self):
        if not self.template_mapping or not self.excel_data or not self.template_image:
            return

        # Prompt to save unsaved template
        if not self._check_unsaved_template():
            return

        idx = self.current_part_index
        row_data = self.edited_data.get(idx, self.excel_data[idx])
        row_str = {k: str(v) if v and str(v).lower() != 'nan' else "" for k, v in row_data.items()}

        try:
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            result = apply_template_mapping(self.template_image, self.template_mapping, row_str)

            first_col = self.excel_columns[0] if self.excel_columns else None
            part_id = str(row_data.get(first_col, f"part_{idx}")) if first_col else f"part_{idx}"
            part_id = sanitize_filename(part_id)

            # Get all export settings from unified panel
            formats = self._get_selected_formats() or {'png'}
            dpi = self.export_settings_panel.get_dpi()
            quality = self.export_settings_panel.get_quality()
            size_limits = self.export_settings_panel.get_all_limits()
            allow_resize = self.export_settings_panel.get_allow_resize()

            saved = save_image_multi_format(
                result, str(output_path), part_id.strip(), formats,
                dpi=dpi, jpeg_quality=quality,
                size_limits=size_limits, allow_resize=allow_resize
            )

            # Check for errors in saved results
            errors = [v for k, v in saved.items() if k.endswith('_error')]
            infos = [v for k, v in saved.items() if k.endswith('_info')]
            actual_saved = len([k for k in saved.keys() if not k.endswith('_error') and not k.endswith('_info')])

            msg = f"Generated {actual_saved} file(s)"
            if infos:
                msg += f"\n\nNotes:\n" + "\n".join(infos)
            if errors:
                msg += f"\n\nWarnings:\n" + "\n".join(errors)

            self.status_bar.set_status(f"Generated {actual_saved} file(s)")
            messagebox.showinfo("Success", msg)

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_bar.set_status(f"Error: {str(e)}", is_error=True)

    def _generate_images(self):
        if self.is_generating or not self.template_mapping or not self.excel_data:
            return

        # Prompt to save unsaved template
        if not self._check_unsaved_template():
            return

        count = len(self.excel_data)
        if not messagebox.askyesno("Confirm", f"Generate {count} images?"):
            return

        self.is_generating = True
        self.generate_btn.configure(state="disabled")
        if hasattr(self, 'generate_range_btn'):
            self.generate_range_btn.configure(state="disabled")

        # Capture export settings on main thread for thread safety
        export_config = {
            'formats': self._get_selected_formats() or {'png'},
            'dpi': self.export_settings_panel.get_dpi(),
            'quality': self.export_settings_panel.get_quality(),
            'size_limits': self.export_settings_panel.get_all_limits(),
            'allow_resize': self.export_settings_panel.get_allow_resize()
        }
        threading.Thread(target=self._generate_thread, args=(0, len(self.excel_data) - 1, export_config), daemon=True).start()

    def _generate_thread(self, from_idx: int = 0, to_idx: int = None, export_config: dict = None):
        try:
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            if to_idx is None:
                to_idx = len(self.excel_data) - 1

            total = to_idx - from_idx + 1
            success = 0
            first_col = self.excel_columns[0] if self.excel_columns else None

            # Use pre-captured export settings (thread-safe)
            formats = export_config.get('formats', {'png'}) if export_config else {'png'}
            dpi = export_config.get('dpi', 300) if export_config else 300
            quality = export_config.get('quality', 95) if export_config else 95
            size_limits = export_config.get('size_limits', {}) if export_config else {}
            allow_resize = export_config.get('allow_resize', False) if export_config else False

            for i in range(from_idx, to_idx + 1):
                row_data = self.excel_data[i]
                data = self.edited_data.get(i, row_data)
                row_str = {k: str(v) if v and str(v).lower() != 'nan' else "" for k, v in data.items()}

                result = apply_template_mapping(self.template_image, self.template_mapping, row_str)

                part_id = str(data.get(first_col, f"part_{i}")) if first_col else f"part_{i}"
                part_id = sanitize_filename(part_id)

                save_image_multi_format(
                    result, str(output_path), part_id, formats,
                    dpi=dpi, jpeg_quality=quality,
                    size_limits=size_limits, allow_resize=allow_resize
                )
                success += 1

                self.after(0, lambda c=success: self.status_bar.set_progress(c, total))

            self.after(0, lambda: self._generation_complete(success, total))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.is_generating = False
            self.after(0, lambda: self.generate_btn.configure(state="normal"))
            if hasattr(self, 'generate_range_btn'):
                self.after(0, lambda: self.generate_range_btn.configure(state="normal"))

    def _generation_complete(self, success: int, total: int):
        self.status_bar.set_progress(0, 0)
        self.status_bar.set_status(f"Done! {success}/{total} generated")
        messagebox.showinfo("Complete", f"Generated {success} images")

    # ========================================================================
    # STATE MANAGEMENT — .dgp project files
    # ========================================================================

    def _get_projects_dir(self) -> Path:
        """Return the projects subfolder of the shared folder."""
        library_path = self._app_settings.get("library_path", get_app_data_dir())
        projects_dir = Path(library_path) / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        return projects_dir

    def _load_all_states(self) -> dict:
        """Load all project states by scanning .dgp files in the projects folder."""
        projects_dir = self._get_projects_dir()
        states = {}
        for dgp_path in sorted(projects_dir.glob("*.dgp")):
            try:
                with open(dgp_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                states[dgp_path.stem] = data
            except (json.JSONDecodeError, OSError):
                continue
        return states

    def _save_project_file(self, name: str, state: dict):
        """Save a single project as a .dgp JSON file."""
        projects_dir = self._get_projects_dir()
        dgp_path = projects_dir / f"{name}.dgp"
        state["version"] = DGP_VERSION
        with open(dgp_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

    def _load_project_file(self, name: str) -> Optional[dict]:
        """Load a single project from a .dgp file."""
        projects_dir = self._get_projects_dir()
        dgp_path = projects_dir / f"{name}.dgp"
        if not dgp_path.exists():
            return None
        try:
            with open(dgp_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _delete_project_file(self, name: str) -> bool:
        """Delete a .dgp project file."""
        projects_dir = self._get_projects_dir()
        dgp_path = projects_dir / f"{name}.dgp"
        if dgp_path.exists():
            dgp_path.unlink()
            return True
        return False

    def _migrate_pkl_to_dgp(self):
        """Migrate old saved_states.pkl to individual .dgp files."""
        for pkl_path in [STATE_FILE, STATE_FILE + '.bak']:
            if not os.path.exists(pkl_path):
                continue
            try:
                with open(pkl_path, 'rb') as f:
                    data = pickle.load(f)
                if not isinstance(data, dict):
                    continue
                for name, state in data.items():
                    # Convert edited_data keys from int to str for JSON
                    if "edited_data" in state:
                        state["edited_data"] = {
                            str(k): v for k, v in state["edited_data"].items()
                        }
                    self._save_project_file(name, state)
                # Rename so migration doesn't repeat
                os.rename(pkl_path, pkl_path + ".migrated")
            except (pickle.PickleError, OSError, EOFError, Exception):
                continue

    def _migrate_templates_to_projects(self):
        """Auto-migrate templates with project context into .dgp project files."""
        migrated_key = "migrated_templates"
        already_migrated = set(self._app_settings.get(migrated_key, []))
        existing_projects = set(self._load_all_states().keys())
        new_migrations = False

        for name in self.template_mgr.list_names():
            if name in already_migrated:
                continue
            tmpl = self.template_mgr.get(name)
            if not tmpl:
                continue
            if not (tmpl.template_path or tmpl.excel_path or tmpl.output_dir):
                continue
            if name in existing_projects:
                already_migrated.add(name)
                continue

            regions_dict = {n: r.to_dict() for n, r in tmpl.regions.items()}
            state = {
                "template_path": tmpl.template_path or "",
                "excel_path": tmpl.excel_path or "",
                "output_dir": tmpl.output_dir or "",
                "edited_data": {},
                "template_mapping": {
                    "template_name": tmpl.name,
                    "template_path": tmpl.template_path or "",
                    "dpi": tmpl.dpi,
                    "regions": regions_dict
                },
                "export_settings": tmpl.export_settings,
            }
            self._save_project_file(name, state)
            already_migrated.add(name)
            new_migrations = True

        if new_migrations or already_migrated:
            self._app_settings[migrated_key] = list(already_migrated)
            save_settings(get_app_data_dir(), self._app_settings)

    def _refresh_saved_states(self):
        projects_dir = self._get_projects_dir()
        self._all_saved_states = sorted(p.stem for p in projects_dir.glob("*.dgp"))
        if hasattr(self, '_project_combo'):
            self._project_combo.configure(values=self._all_saved_states)
            if self._current_project_name:
                self._project_combo.set(self._current_project_name)

    def _save_as_project(self):
        """Clone current project under a new name."""
        dialog = ctk.CTkInputDialog(
            text="Enter new project name:",
            title="Save As"
        )
        new_name = dialog.get_input()
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()
        self._project_combo.set(new_name)
        self._save_state()

    def _save_state(self):
        name = self._project_combo.get().strip()
        if not name:
            if self.template_path:
                name = Path(self.template_path).stem
            else:
                messagebox.showwarning("Warning", "Enter a name")
                return

        try:
            # Convert edited_data keys to str for JSON serialization
            edited_data_str = {str(k): v for k, v in self.edited_data.items()}

            state = {
                "template_path": self.template_path or "",
                "excel_path": self.excel_path or "",
                "output_dir": self.output_dir or "",
                "edited_data": edited_data_str,
                "template_mapping": None,
                "export_settings": self.export_settings_panel.get_state(),
            }

            if self.template_mapping:
                state["template_mapping"] = {
                    "template_name": self.template_mapping.template_name,
                    "template_path": self.template_mapping.template_path,
                    "dpi": self.template_mapping.dpi,
                    "regions": {n: r.to_dict() for n, r in self.template_mapping.regions.items()}
                }

            state["template_field_names"] = list(self._template_field_names)

            self._save_project_file(name, state)
            self._refresh_saved_states()

            self._current_project_name = name
            self._update_active_labels()
            self.status_bar.set_status(f"Saved project: {name}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _load_state(self):
        name = self._project_combo.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Select or type a project name")
            return
        if name not in self._all_saved_states:
            messagebox.showwarning("Warning", f"Project '{name}' not found")
            return
        state = self._load_project_file(name)

        if state is None:
            messagebox.showerror("Error", f"Could not load project '{name}'")
            return

        try:
            self._loading_template = True

            if state.get("template_path"):
                self.template_entry.delete(0, "end")
                self.template_entry.insert(0, state["template_path"])

            if state.get("excel_path"):
                self.excel_entry.delete(0, "end")
                self.excel_entry.insert(0, state["excel_path"])

            if state.get("output_dir"):
                self.output_entry.delete(0, "end")
                self.output_entry.insert(0, state["output_dir"])

            # Load export settings (new unified format)
            if state.get("export_settings"):
                self.export_settings_panel.set_state(state["export_settings"])
            # Handle old format for backwards compatibility
            elif state.get("export_formats") or state.get("size_limits"):
                old_state = {
                    'dpi': str(state.get("dpi", 300)),
                    'quality': state.get("jpeg_quality", 95),
                    'allow_resize': state.get("size_limits", {}).get("allow_resize", True) if state.get("size_limits") else True,
                    'formats': {}
                }
                for fmt in ['png', 'jpg', 'pdf', 'webp', 'bmp', 'tiff', 'gif']:
                    old_state['formats'][fmt] = {
                        'export': fmt in state.get("export_formats", ["png"]),
                        'limit_enabled': state.get("size_limits", {}).get("limits", {}).get(fmt, {}).get("enabled", False) if state.get("size_limits") else False,
                        'limit_value': state.get("size_limits", {}).get("limits", {}).get(fmt, {}).get("value", "500") if state.get("size_limits") else "500",
                        'limit_unit': state.get("size_limits", {}).get("limits", {}).get(fmt, {}).get("unit", "KB") if state.get("size_limits") else "KB"
                    }
                self.export_settings_panel.set_state(old_state)

            # Restore template mapping (field placements) FIRST so _load_files preserves them
            mapping = state.get("template_mapping")
            if mapping and mapping.get("regions"):
                regions = {n: TextRegion.from_dict(r) for n, r in mapping["regions"].items()}
                self.template_mapping = TemplateMapping(
                    template_name=mapping.get("template_name", ""),
                    template_path=mapping.get("template_path", ""),
                    regions=regions,
                    dpi=mapping.get("dpi", 300)
                )

            # Check if file paths exist, prompt user to browse if not
            files_loaded = False
            tp = state.get("template_path", "")
            ep = state.get("excel_path", "")
            template_missing = tp and not os.path.isfile(tp)
            excel_missing = ep and not os.path.isfile(ep)

            if template_missing or excel_missing:
                # Build message about which files are missing
                missing = []
                if template_missing:
                    missing.append(f"  Template: {tp}")
                if excel_missing:
                    missing.append(f"  Excel: {ep}")

                messagebox.showinfo(
                    "File Paths Changed",
                    f"The following file(s) could not be found:\n\n"
                    + "\n".join(missing) +
                    "\n\nThe file location may have changed. "
                    "Please browse to the correct file(s).\n\n"
                    "Your field placements and settings have been preserved."
                )

                # Auto-open browser for template file if missing
                if template_missing:
                    new_tp = filedialog.askopenfilename(
                        title="Select Template File (PDF or Image)",
                        filetypes=[("PDF/Image", "*.pdf *.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
                    )
                    if new_tp:
                        self.template_entry.delete(0, "end")
                        self.template_entry.insert(0, new_tp)
                        tp = new_tp

                # Auto-open browser for Excel file if missing
                if excel_missing:
                    new_ep = filedialog.askopenfilename(
                        title="Select Data File",
                        filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("CSV", "*.csv"), ("All", "*.*")]
                    )
                    if new_ep:
                        self.excel_entry.delete(0, "end")
                        self.excel_entry.insert(0, new_ep)
                        ep = new_ep

            # Attempt to load files if both paths now exist
            if tp and ep and os.path.isfile(tp) and os.path.isfile(ep):
                self._load_files()
                files_loaded = self.template_image is not None

            # Push regions to canvas if files loaded successfully
            if files_loaded and self.template_mapping and self.template_mapping.regions:
                self.editor_canvas.set_regions(self.template_mapping.regions)
                self.editor_canvas._render_preview()

            # Restore edited data AFTER _load_files (which resets it)
            saved_edits = state.get("edited_data", {})
            if saved_edits:
                self.edited_data = saved_edits.copy()

            self._loading_template = False
            self._current_project_name = name
            if self.template_mapping:
                self._current_template_name = self.template_mapping.template_name or ""
            saved_tmpl_fields = state.get("template_field_names")
            if saved_tmpl_fields is not None:
                self._template_field_names = set(saved_tmpl_fields)
            elif self.template_mapping and self.template_mapping.regions:
                # Old project without template_field_names — treat all as template fields
                self._template_field_names = set(self.template_mapping.regions.keys())
            self._fields_dirty = False
            self._modified_from_template = ""
            self._update_active_labels()
            self._sync_template_field_visuals()

            # Highlight the active template in the library listbox
            self._highlight_active_template()

            if files_loaded:
                self.status_bar.set_status(f"Loaded project: {name}")
            else:
                self.status_bar.set_status(f"Loaded settings for: {name} — update file paths and click Load Files")

        except Exception as e:
            self._loading_template = False
            messagebox.showerror("Error", f"Failed to load project '{name}': {str(e)}")

    def _delete_state(self):
        name = self._project_combo.get().strip()
        if not name or name not in self._all_saved_states:
            return
        if not messagebox.askyesno("Confirm", f"Delete project '{name}'?"):
            return

        if self._delete_project_file(name):
            self._refresh_saved_states()
            self.status_bar.set_status(f"Deleted project: {name}")

    def _export_dgt(self):
        """Export current template configuration to a .dgt file."""
        if not self.template_mapping or not self.template_mapping.regions:
            messagebox.showwarning("Nothing to Export", "Place some fields on the template first.")
            return

        # Suggest filename from template name
        default_name = self.template_mapping.template_name or "template"
        filepath = filedialog.asksaveasfilename(
            title="Export Template File",
            defaultextension=".dgt",
            initialfile=f"{default_name}.dgt",
            filetypes=[("Drawing Generator Template", "*.dgt"), ("All", "*.*")]
        )
        if not filepath:
            return

        try:
            DrawingTemplate.export_to_dgt(
                filepath,
                regions=self.template_mapping.regions,
                dpi=self.template_mapping.dpi,
                export_settings=self.export_settings_panel.get_state()
            )
            self.status_bar.set_status(f"Exported: {os.path.basename(filepath)}")
            messagebox.showinfo("Export Complete",
                f"Template exported to:\n{filepath}\n\n"
                f"{len(self.template_mapping.regions)} field(s) saved.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _import_dgt(self):
        """Import template configuration from a .dgt file."""
        filepath = filedialog.askopenfilename(
            title="Import Template File",
            filetypes=[("Drawing Generator Template", "*.dgt"), ("All", "*.*")]
        )
        if not filepath:
            return

        try:
            data = DrawingTemplate.import_from_dgt(filepath)
            imported_regions = data["regions"]

            if not imported_regions:
                messagebox.showwarning("Empty Template", "The .dgt file contains no field placements.")
                return

            # Merge imported regions into current workspace
            if self.template_mapping is None:
                self.template_mapping = TemplateMapping(
                    template_name=Path(filepath).stem,
                    template_path="",
                    regions={},
                    dpi=data.get("dpi", 300)
                )

            # Check for conflicts
            existing = set(self.template_mapping.regions.keys())
            incoming = set(imported_regions.keys())
            conflicts = existing & incoming

            if conflicts:
                if not messagebox.askyesno(
                    "Overwrite Fields?",
                    f"The following fields already exist and will be overwritten:\n\n"
                    + ", ".join(sorted(conflicts)) +
                    f"\n\nOverwrite {len(conflicts)} field(s)?"
                ):
                    # Only import non-conflicting fields
                    imported_regions = {k: v for k, v in imported_regions.items() if k not in conflicts}

            self.template_mapping.regions.update(imported_regions)

            # Apply export settings if available
            if data.get("export_settings"):
                self.export_settings_panel.set_state(data["export_settings"])

            # Update canvas
            if self.template_image:
                self.editor_canvas.set_regions(self.template_mapping.regions)
                self.editor_canvas._render_preview()

            self.status_bar.set_status(f"Imported {len(imported_regions)} field(s) from {os.path.basename(filepath)}")
            messagebox.showinfo("Import Complete",
                f"Imported {len(imported_regions)} field(s) from:\n{os.path.basename(filepath)}")

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import template:\n{str(e)}")

    # ========================================================================
    # TEMPLATE LIBRARY METHODS
    # ========================================================================

    def _refresh_template_list(self):
        """Reload the template combo from the manager."""
        self._all_template_names = self.template_mgr.list_names()
        if hasattr(self, '_tmpl_combo'):
            self._tmpl_combo.configure(values=self._all_template_names)
            self._highlight_active_template()
        self._update_file_counts()

    def _highlight_active_template(self):
        """Set the template combo to the currently active template name."""
        if not self._current_template_name:
            return
        # Find case-insensitive match in available names
        for name in self._all_template_names:
            if name.lower() == self._current_template_name.lower():
                self._tmpl_combo.set(name)
                return
        self._tmpl_combo.set(self._current_template_name)

    def _new_template(self):
        """Clear all placed fields to start a fresh template. Keeps drawing/Excel loaded."""
        if self._fields_dirty and self.template_mapping and self.template_mapping.regions:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved field placements.\nSave before starting a new template?")
            if result is True:
                self._save_template()
            elif result is None:
                return  # Cancel

        if self.template_mapping:
            self.template_mapping.regions.clear()

        self._current_template_name = ""
        self._fields_dirty = False
        self._modified_from_template = ""
        self._tmpl_combo.set("")

        if self.template_image:
            self.editor_canvas.set_regions({})
            self.editor_canvas._render_preview()

        self._update_active_labels()
        self.status_bar.set_status("New template — place fields on the drawing")

    def _save_template(self):
        """Save all placed fields as a template to the library."""
        if not self.template_mapping or not self.template_mapping.regions:
            messagebox.showwarning("No Fields",
                "No fields to save.\n\n"
                "Place fields from the column list,\n"
                "then click Save.")
            return

        name = self._tmpl_combo.get().strip()
        if not name:
            if self._current_template_name:
                name = self._current_template_name
                self._tmpl_combo.set(name)
            else:
                messagebox.showwarning("Warning", "Enter a name for the template.")
                return

        # Check if name exists
        if self.template_mgr.get(name):
            if not messagebox.askyesno("Overwrite?",
                f"Template '{name}' already exists. Overwrite?"):
                return

        regions = {n: TextRegion.from_dict(r.to_dict())
                   for n, r in self.template_mapping.regions.items()}

        tmpl = FieldTemplate(
            name=name,
            regions=regions,
            dpi=self.template_mapping.dpi,
            template_path=self.template_path or "",
            excel_path=self.excel_path or "",
            output_dir=self.output_dir or "",
            export_settings=self.export_settings_panel.get_state() if hasattr(self, 'export_settings_panel') else None
        )
        self.template_mgr.save_template(tmpl)
        self._refresh_template_list()

        self._current_template_name = name
        self._fields_dirty = False
        self._modified_from_template = ""
        self._update_active_labels()

        self.status_bar.set_status(f"Saved template: {name} ({len(regions)} field(s))")

    def _load_template(self):
        """Apply the selected template with column mapping if needed."""
        name = self._tmpl_combo.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Select a template to apply.")
            return
        if name not in self._all_template_names:
            messagebox.showwarning("Warning", f"Template '{name}' not found.")
            return

        # Load the template data
        tmpl = self.template_mgr.get(name)
        if not tmpl or not tmpl.regions:
            self.status_bar.set_status(f"Template '{name}' is empty.")
            return

        field_names = list(tmpl.regions.keys())

        # Check if all template field names match current Excel columns
        if self.excel_columns:
            all_match = all(n in self.excel_columns for n in field_names)
        else:
            all_match = False

        if all_match:
            # Direct load — no mapping dialog needed
            mapping = {n: n for n in field_names}
        else:
            if not self.excel_columns:
                messagebox.showwarning(
                    "No Excel Loaded",
                    "Load an Excel file first, then load the template "
                    "to map its fields to your columns."
                )
                return

            # Show mapping dialog
            dialog = TemplateMappingDialog(
                self,
                template_name=name,
                field_names=field_names,
                excel_columns=self.excel_columns,
                field_regions=tmpl.regions
            )

            if dialog.result is None:
                return  # User cancelled
            mapping = dialog.result

        if not mapping:
            self.status_bar.set_status("No fields mapped — template not loaded.")
            return

        # Initialize template_mapping if needed
        if self.template_mapping is None:
            self.template_mapping = TemplateMapping(
                template_name="",
                template_path="",
                regions={},
                dpi=tmpl.dpi
            )

        # Clear existing regions before loading
        self.template_mapping.regions.clear()

        # Add fields with mapped column names but original positions/formatting
        current_dpi = self.template_mapping.dpi or 300
        tmpl_dpi = tmpl.dpi or 300
        dpi_scale = current_dpi / tmpl_dpi if tmpl_dpi != current_dpi else 1.0

        added = 0
        for slot_name, mapped_col in mapping.items():
            original = tmpl.regions[slot_name]

            new_region = TextRegion(
                column_name=mapped_col,
                x=int(original.x * dpi_scale),
                y=int(original.y * dpi_scale),
                font_size=max(1, int(original.font_size * dpi_scale)),
                font_color=original.font_color,
                font_name=original.font_name,
                align=original.align,
                bold=original.bold,
                italic=original.italic,
            )

            self.template_mapping.regions[mapped_col] = new_region
            added += 1

        # Update canvas (use guard to prevent _on_region_changed from marking dirty)
        self._loading_template = True
        if self.template_image:
            self.editor_canvas.set_regions(self.template_mapping.regions)
            self.editor_canvas._render_preview()
            self._on_region_changed()
        self._loading_template = False

        self._current_template_name = name
        self._template_field_names = set(self.template_mapping.regions.keys())
        self._fields_dirty = False
        self._modified_from_template = ""

        self._update_active_labels()
        self._highlight_active_template()
        self._sync_template_field_visuals()
        self.status_bar.set_status(f"Loaded template '{name}': {added} field(s)")

    def _delete_template(self):
        """Delete the selected template from the library."""
        name = self._tmpl_combo.get().strip()
        if not name or name not in self._all_template_names:
            return
        if not messagebox.askyesno("Confirm", f"Delete template '{name}'?"):
            return

        self.template_mgr.delete(name)

        if name == self._current_template_name:
            self._current_template_name = ""

        self._refresh_template_list()
        self._update_active_labels()
        self.status_bar.set_status(f"Deleted template: {name}")

    def _browse_library_path(self):
        """Let user choose a shared folder for templates and projects."""
        current = self._app_settings.get("library_path", get_app_data_dir())
        path = filedialog.askdirectory(title="Select Shared Folder for Templates & Projects", initialdir=current)
        if path:
            self.template_mgr.set_library_path(path)
            self._app_settings["library_path"] = path
            save_settings(get_app_data_dir(), self._app_settings)
            self._lib_path_full = path
            self._lib_path_label.configure(text=self._truncate_path(path))
            # Ensure subfolders exist
            Path(path, "templates").mkdir(parents=True, exist_ok=True)
            Path(path, "projects").mkdir(parents=True, exist_ok=True)
            self._refresh_template_list()
            self._refresh_saved_states()
            self._update_file_counts()
            self.status_bar.set_status(f"Shared folder set to: {path}")

    def _update_file_counts(self):
        """Update the file count indicator label."""
        if not hasattr(self, '_file_count_label'):
            return
        n_templates = self.template_mgr.count()
        projects_dir = self._get_projects_dir()
        n_projects = len(list(projects_dir.glob("*.dgp")))
        self._file_count_label.configure(
            text=f"{n_templates} template{'s' if n_templates != 1 else ''}, "
                 f"{n_projects} project{'s' if n_projects != 1 else ''}")

    @staticmethod
    def _truncate_path(path: str, max_len: int = 30) -> str:
        """Truncate a path from the left, keeping the end visible."""
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len - 3):]

    def _show_path_tooltip(self, event):
        """Show full library path in a tooltip near the label."""
        self._path_tooltip = tk.Toplevel(self)
        self._path_tooltip.wm_overrideredirect(True)
        x = event.x_root + 10
        y = event.y_root + 10
        self._path_tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self._path_tooltip,
            text=self._lib_path_full,
            bg="#2d2d2d", fg="#ffffff",
            font=("Segoe UI", 10),
            padx=8, pady=4,
            relief="solid", borderwidth=1
        )
        label.pack()

    def _hide_path_tooltip(self):
        """Hide the library path tooltip."""
        if hasattr(self, '_path_tooltip') and self._path_tooltip:
            self._path_tooltip.destroy()
            self._path_tooltip = None

    def _check_unsaved_template(self) -> bool:
        """Prompt to save template if fields are dirty. Returns False if user cancels."""
        if self._fields_dirty and self.template_mapping and self.template_mapping.regions:
            result = messagebox.askyesnocancel(
                "Unsaved Template",
                "You have unsaved field placements.\nSave as template before generating?")
            if result is True:
                self._save_template()
            elif result is None:
                return False  # Cancel
            # False = skip saving, continue generating
        return True

    def _clear_fields(self):
        """Clear all fields from the canvas."""
        if not self.template_mapping or not self.template_mapping.regions:
            self.status_bar.set_status("No fields to clear.")
            return

        n = len(self.template_mapping.regions)
        self.template_mapping.regions.clear()
        self._current_template_name = ""
        self._current_project_name = ""
        self._template_field_names = set()
        self._fields_dirty = False
        self._modified_from_template = ""

        if self.template_image:
            self.editor_canvas.set_regions(self.template_mapping.regions)
            self.editor_canvas._render_preview()
            self._on_region_changed()

        self._sync_template_field_visuals()
        self._update_active_labels()
        self.status_bar.set_status(f"Cleared all {n} field(s).")

    def _update_active_labels(self):
        """Update the PROJECT card info label and combo display."""
        if not hasattr(self, '_project_info_label'):
            return

        # Update project combo display
        if hasattr(self, '_project_combo') and self._current_project_name:
            self._project_combo.set(self._current_project_name)

        # Template info line
        all_regions = self.editor_canvas.regions if hasattr(self, 'editor_canvas') else {}
        n = len(all_regions)
        n_tmpl = len(self._template_field_names & set(all_regions.keys()))
        n_custom = n - n_tmpl
        dirty = " \u2022 modified" if self._fields_dirty else ""

        # Build field count detail
        if n_tmpl > 0 and n_custom > 0:
            detail = f"{n_tmpl}T + {n_custom}C"
        elif n_tmpl > 0:
            detail = f"{n_tmpl} field{'s' if n_tmpl != 1 else ''}"
        elif n_custom > 0:
            detail = f"{n_custom} custom"
        else:
            detail = ""

        if self._current_template_name and n > 0:
            self._project_info_label.configure(
                text=f"Template:  {self._current_template_name}  ({detail}){dirty}")
        elif self._fields_dirty and hasattr(self, '_modified_from_template') and self._modified_from_template and n > 0:
            self._project_info_label.configure(
                text=f"Template:  {self._modified_from_template}  ({detail}) \u2022 modified")
        elif n > 0:
            self._project_info_label.configure(
                text=f"Template:  None  ({detail}){dirty}")
        else:
            self._project_info_label.configure(text="No fields placed")

    def _sync_template_field_visuals(self):
        """Push template field names to the canvas and fields panel for visual distinction."""
        if hasattr(self, 'editor_canvas'):
            self.editor_canvas.set_template_field_names(self._template_field_names)
        if hasattr(self, 'fields_panel'):
            self.fields_panel.set_template_field_names(self._template_field_names)

    # ========================================================================
    # FILE CONVERTER METHODS
    # ========================================================================

    def _conv_add_files(self):
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.pdf"), ("All", "*.*")]
        )
        for f in files:
            if f not in self.conv_file_listbox.get(0, tk.END):
                self.conv_file_listbox.insert(tk.END, f)
        self._conv_update_count()

    def _conv_add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.pdf')
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(exts):
                        path = os.path.join(root, f)
                        if path not in self.conv_file_listbox.get(0, tk.END):
                            self.conv_file_listbox.insert(tk.END, path)
        self._conv_update_count()

    def _conv_remove_files(self):
        for i in reversed(self.conv_file_listbox.curselection()):
            self.conv_file_listbox.delete(i)
        self._conv_update_count()

    def _conv_clear_files(self):
        self.conv_file_listbox.delete(0, tk.END)
        self._conv_update_count()
        self.conv_preview_label.configure(text="Select a file to preview")
        self.conv_preview_canvas.delete("all")

    def _conv_update_count(self):
        count = self.conv_file_listbox.size()
        self.conv_file_count_label.configure(text=f"{count} file{'s' if count != 1 else ''} selected")

    def _conv_browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.conv_output_entry.delete(0, tk.END)
            self.conv_output_entry.insert(0, path)
            self.conv_same_folder_var.set(False)

    def _conv_toggle_output(self):
        state = "disabled" if self.conv_same_folder_var.get() else "normal"
        self.conv_output_entry.configure(state=state)

    def _conv_on_file_select(self, event):
        selection = self.conv_file_listbox.curselection()
        if selection:
            self._conv_show_preview(self.conv_file_listbox.get(selection[0]))

    def _conv_show_preview(self, file_path):
        try:
            if file_path.lower().endswith('.pdf'):
                img = get_image_from_template(file_path, dpi=72)
            else:
                img = Image.open(file_path)

            self.conv_preview_canvas.update_idletasks()
            w = self.conv_preview_canvas.winfo_width() - 20
            h = self.conv_preview_canvas.winfo_height() - 20
            if w < 100: w = 400
            if h < 100: h = 300

            img.thumbnail((w, h), Image.Resampling.LANCZOS)
            self.conv_preview_photo = ImageTk.PhotoImage(img)

            self.conv_preview_canvas.delete("all")
            self.conv_preview_canvas.create_image(w // 2 + 10, h // 2 + 10, image=self.conv_preview_photo, anchor="center")
            self.conv_preview_label.configure(text="")

            size = os.path.getsize(file_path)
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
            self.conv_progress_label.configure(text=f"{os.path.basename(file_path)} - {size_str}")

        except Exception as e:
            self.conv_preview_label.configure(text=f"Cannot preview: {str(e)[:50]}")

    def _conv_start_conversion(self):
        files = self.conv_file_listbox.get(0, tk.END)
        if not files:
            messagebox.showwarning("No Files", "Add files to convert")
            return

        formats = list(self.conv_export_panel.get_selected_formats())
        if not formats:
            messagebox.showwarning("No Formats", "Select output format(s)")
            return

        if not messagebox.askyesno("Confirm", f"Convert {len(files)} file(s) to {', '.join(formats).upper()}?"):
            return

        # Capture settings on main thread for thread safety
        conv_config = {
            'quality': self.conv_export_panel.get_quality(),
            'dpi': self.conv_export_panel.get_dpi(),
            'allow_resize': self.conv_export_panel.get_allow_resize(),
            'same_folder': self.conv_same_folder_var.get(),
            'output_folder': self.conv_output_entry.get().strip(),
            'size_limits': {fmt: self.conv_export_panel.get_limit_bytes(fmt) for fmt in formats}
        }

        self.convert_btn.configure(state="disabled")
        threading.Thread(target=self._conv_thread, args=(files, formats, conv_config), daemon=True).start()

    def _conv_thread(self, files, formats, conv_config):
        success = 0
        total = len(files)
        errors = []
        quality = conv_config['quality']
        dpi = conv_config['dpi']
        allow_resize = conv_config['allow_resize']
        same_folder = conv_config['same_folder']
        output_folder = conv_config['output_folder'] if not same_folder else None
        size_limits = conv_config['size_limits']

        for i, file_path in enumerate(files):
            try:
                self.after(0, lambda n=os.path.basename(file_path), c=i + 1: self.conv_progress_label.configure(text=f"Converting {c}/{total}: {n}"))

                if file_path.lower().endswith('.pdf'):
                    img = get_image_from_template(file_path, dpi=dpi)
                else:
                    img = Image.open(file_path)

                out_dir = os.path.dirname(file_path) if same_folder else (output_folder or os.path.dirname(file_path))
                os.makedirs(out_dir, exist_ok=True)
                base_name = os.path.splitext(os.path.basename(file_path))[0]

                for fmt in formats:
                    out_path = os.path.join(out_dir, f"{base_name}.{fmt}")

                    try:
                        size_limit = size_limits.get(fmt)
                        if size_limit:
                            result = save_image_with_size_limit(
                                img, out_path, fmt, size_limit,
                                initial_quality=quality, allow_resize=allow_resize
                            )
                            if not result[0]:  # Save failed
                                errors.append(f"{base_name}.{fmt}: {result[2]}")
                        elif fmt == 'pdf':
                            save_image_multi_format(img, out_dir, base_name, {'pdf'}, dpi=dpi, jpeg_quality=quality)
                        elif fmt in ('jpg', 'jpeg'):
                            img_rgb = img.convert('RGB') if img.mode in ('RGBA', 'P') else img
                            img_rgb.save(out_path, 'JPEG', quality=quality, optimize=True)
                        elif fmt == 'webp':
                            img.save(out_path, 'WEBP', quality=quality)
                        elif fmt == 'png':
                            img.save(out_path, 'PNG', optimize=True)
                        elif fmt == 'bmp':
                            img_rgb = img.convert('RGB') if img.mode in ('RGBA', 'P') else img
                            img_rgb.save(out_path, 'BMP')
                        elif fmt in ('tiff', 'tif'):
                            img.save(out_path, 'TIFF', compression='tiff_lzw')
                        elif fmt == 'gif':
                            img_p = img.convert('P', palette=Image.ADAPTIVE, colors=256) if img.mode != 'P' else img
                            img_p.save(out_path, 'GIF')
                        elif fmt == 'ico':
                            # ICO format - resize to standard icon size
                            ico_img = img.copy()
                            ico_img.thumbnail((256, 256), Image.Resampling.LANCZOS)
                            ico_img.save(out_path, 'ICO')
                        else:
                            img.save(out_path)
                    except Exception as fmt_err:
                        errors.append(f"{base_name}.{fmt}: {str(fmt_err)}")

                success += 1

            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

        self.after(0, lambda: self._conv_complete(success, total, formats, errors))

    def _conv_complete(self, success: int, total: int, formats: list, errors: list = None):
        self.convert_btn.configure(state="normal")
        self.conv_progress_label.configure(text=f"Done! {success}/{total} converted")

        msg = f"Converted {success} files to {', '.join(formats).upper()}"
        if errors:
            msg += f"\n\n{len(errors)} error(s):\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += f"\n... and {len(errors) - 5} more"
            messagebox.showwarning("Complete with Errors", msg)
        else:
            messagebox.showinfo("Complete", msg)
