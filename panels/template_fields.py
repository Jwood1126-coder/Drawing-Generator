"""Template Fields Panel - columns list, placed fields, and field properties editor."""

import customtkinter as ctk
import tkinter as tk
from typing import Optional, Dict, List

from themes import T, ThemeManager
from widgets import ModernLabel, ModernEntry, ModernButton, ModernCheckbox, ModernDropdown, ThemedListbox
from modules.template_editor import TextRegion


class TemplateFieldsPanel(ctk.CTkFrame):
    """
    Unified panel combining:
    - Excel Columns (for placing new fields)
    - Placed Fields (list of placed text regions)
    - Field Properties (editor for selected field)

    Uses a tabbed interface for compact presentation.
    """

    def __init__(self, parent, on_column_select=None, on_column_double_click=None,
                 on_region_select=None, on_field_change=None):
        super().__init__(parent, fg_color="transparent")

        self.on_column_select = on_column_select
        self.on_column_double_click = on_column_double_click
        self.on_region_select = on_region_select
        self.on_field_change = on_field_change
        self.current_region: Optional[TextRegion] = None
        self._updating = False
        self._last_regions = {}
        self._last_selected = None
        self._template_field_names: set = set()
        # Tab selector
        tab_frame = ctk.CTkFrame(self, fg_color=T().bg_tertiary, corner_radius=6)
        tab_frame.pack(fill="x", pady=(0, 8))

        tab_inner = ctk.CTkFrame(tab_frame, fg_color="transparent")
        tab_inner.pack(fill="x", padx=4, pady=4)

        self.current_tab = ctk.StringVar(value="columns")
        self._tab_buttons = {}

        tabs = [
            ("columns", "Columns"),
            ("placed", "Placed"),
            ("properties", "Properties")
        ]

        for tab_id, tab_label in tabs:
            is_active = (tab_id == "columns")
            btn = ctk.CTkButton(
                tab_inner,
                text=tab_label,
                width=80,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=T().accent if is_active else "transparent",
                hover_color=T().accent_hover,
                text_color=T().text_on_accent if is_active else T().text_white,
                command=lambda t=tab_id: self._switch_tab(t)
            )
            btn.pack(side="left", padx=2)
            self._tab_buttons[tab_id] = btn

        self._tab_frame = tab_frame

        # Content area - one frame per tab
        self._content_area = ctk.CTkFrame(self, fg_color="transparent")
        self._content_area.pack(fill="both", expand=True)

        # === COLUMNS TAB ===
        self._columns_frame = ctk.CTkFrame(self._content_area, fg_color="transparent")

        self.column_listbox = ThemedListbox(self._columns_frame, height=10)
        self.column_listbox.pack(fill="both", expand=True, pady=(0, 4))
        self.column_listbox.bind('<<ListboxSelect>>', self._on_column_listbox_select)
        self.column_listbox.bind('<Double-Button-1>', self._on_column_listbox_double_click)

        self.instructions_label = ModernLabel(
            self._columns_frame,
            text="Select column, then click on template to place",
            style="dim"
        )
        self.instructions_label.pack(anchor="w")

        # === PLACED TAB ===
        self._placed_frame = ctk.CTkFrame(self._content_area, fg_color="transparent")

        self.placed_scroll = ctk.CTkScrollableFrame(
            self._placed_frame,
            fg_color=T().bg_tertiary,
            corner_radius=6,
            height=150,
            scrollbar_fg_color=T().bg_secondary,
            scrollbar_button_color=T().accent_dim
        )
        self.placed_scroll.pack(fill="both", expand=True)
        self.region_items = {}

        # === PROPERTIES TAB ===
        self._properties_frame = ctk.CTkFrame(self._content_area, fg_color="transparent")
        self._build_properties_tab()

        # Show initial tab
        self._columns_frame.pack(fill="both", expand=True)

        ThemeManager.register(self._update_theme)

    def _build_properties_tab(self):
        """Build the properties editor tab - compact layout."""
        # Selection indicator
        sel_row = ctk.CTkFrame(self._properties_frame, fg_color="transparent")
        sel_row.pack(fill="x", pady=(0, 4))

        ModernLabel(sel_row, text="Field:", style="dim").pack(side="left")
        self.selection_label = ctk.CTkLabel(
            sel_row,
            text="(none selected)",
            font=ctk.CTkFont(size=11),
            text_color=T().text_primary
        )
        self.selection_label.pack(side="left", padx=8)

        # Content frame - no expand, just fill width
        content = ctk.CTkFrame(self._properties_frame, fg_color=T().bg_tertiary, corner_radius=6)
        content.pack(fill="x")
        self._props_content = content

        inner = ctk.CTkFrame(content, fg_color="transparent")
        inner.pack(fill="x", padx=6, pady=6)

        # Row 1: Size + Font (combined)
        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=2)

        ModernLabel(row1, text="Size:", style="dim", width=36, anchor="e").pack(side="left")
        self.size_entry = ModernEntry(row1, width=40)
        self.size_entry.insert(0, "14")
        self.size_entry.pack(side="left", padx=(4, 2))
        self.size_entry.bind("<Return>", lambda e: self._apply_changes())
        self.size_entry.bind("<FocusOut>", lambda e: self._apply_changes())

        for size in [10, 12, 14, 18]:
            btn = ModernButton(row1, str(size), lambda s=size: self._set_size(s),
                             variant="ghost", width=26, height=22)
            btn.pack(side="left", padx=1)

        # Row 2: Font dropdown
        row2 = ctk.CTkFrame(inner, fg_color="transparent")
        row2.pack(fill="x", pady=2)

        ModernLabel(row2, text="Font:", style="dim", width=36, anchor="e").pack(side="left")

        self.available_fonts = [
            ("Gotham XNarrow", "GothamXNarrow"),
            ("Arial", "arial.ttf"),
            ("Arial Black", "ariblk.ttf"),
            ("Calibri", "calibri.ttf"),
            ("Consolas", "consola.ttf"),
            ("Georgia", "georgia.ttf"),
            ("Impact", "impact.ttf"),
            ("Segoe UI", "segoeui.ttf"),
            ("Tahoma", "tahoma.ttf"),
            ("Times New Roman", "times.ttf"),
            ("Verdana", "verdana.ttf"),
        ]

        self.font_var = ctk.StringVar(value="Gotham XNarrow")
        self.font_dropdown = ModernDropdown(
            row2,
            values=[f[0] for f in self.available_fonts],
            variable=self.font_var,
            command=lambda v: self._apply_changes(),
            width=140
        )
        self.font_dropdown.pack(side="left", padx=4)

        # Row 3: Style (Bold, Italic) + Alignment
        row3 = ctk.CTkFrame(inner, fg_color="transparent")
        row3.pack(fill="x", pady=2)

        ModernLabel(row3, text="Style:", style="dim", width=36, anchor="e").pack(side="left")

        self.bold_var = ctk.BooleanVar(value=False)
        self.bold_btn = ctk.CTkButton(
            row3, text="B", width=28, height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=T().bg_hover, hover_color=T().accent_dim,
            command=self._toggle_bold
        )
        self.bold_btn.pack(side="left", padx=(4, 2))

        self.italic_var = ctk.BooleanVar(value=False)
        self.italic_btn = ctk.CTkButton(
            row3, text="I", width=28, height=24,
            font=ctk.CTkFont(size=10, slant="italic"),
            fg_color=T().bg_hover, hover_color=T().accent_dim,
            command=self._toggle_italic
        )
        self.italic_btn.pack(side="left", padx=1)

        # Alignment buttons (same row)
        self.align_var = ctk.StringVar(value="left")
        self.align_buttons = {}
        for align, symbol in [("left", "◀"), ("center", "◆"), ("right", "▶")]:
            btn = ctk.CTkButton(
                row3, text=symbol, width=28, height=24,
                fg_color=T().bg_hover, hover_color=T().accent_dim,
                command=lambda a=align: self._set_align(a)
            )
            btn.pack(side="left", padx=1)
            self.align_buttons[align] = btn

        # Row 4: Color
        row4 = ctk.CTkFrame(inner, fg_color="transparent")
        row4.pack(fill="x", pady=2)

        ModernLabel(row4, text="Color:", style="dim", width=36, anchor="e").pack(side="left")

        self.color_preview = ctk.CTkFrame(row4, width=22, height=22, fg_color="#000000", corner_radius=3)
        self.color_preview.pack(side="left", padx=(4, 3))

        self.color_entry = ModernEntry(row4, width=65)
        self.color_entry.insert(0, "#000000")
        self.color_entry.pack(side="left", padx=(0, 3))
        self.color_entry.bind("<Return>", lambda e: self._apply_color())
        self.color_entry.bind("<FocusOut>", lambda e: self._apply_color())

        for color, name in [("#000000", "Blk"), ("#FFFFFF", "Wht"), ("#FF0000", "Red")]:
            fg = "#FFFFFF" if color in ["#000000", "#FF0000"] else "#000000"
            btn = ctk.CTkButton(
                row4, text=name, width=30, height=22,
                fg_color=color, hover_color=color, text_color=fg,
                font=ctk.CTkFont(size=9),
                command=lambda c=color: self._set_color(c)
            )
            btn.pack(side="left", padx=1)

        # Row 5: Position
        row5 = ctk.CTkFrame(inner, fg_color="transparent")
        row5.pack(fill="x", pady=2)

        ModernLabel(row5, text="Pos:", style="dim", width=36, anchor="e").pack(side="left")

        ModernLabel(row5, text="X:", style="dim").pack(side="left", padx=(4, 2))
        self.x_entry = ModernEntry(row5, width=50)
        self.x_entry.insert(0, "0")
        self.x_entry.pack(side="left")
        self.x_entry.bind("<Return>", lambda e: self._apply_position())

        ModernLabel(row5, text="Y:", style="dim").pack(side="left", padx=(6, 2))
        self.y_entry = ModernEntry(row5, width=50)
        self.y_entry.insert(0, "0")
        self.y_entry.pack(side="left")
        self.y_entry.bind("<Return>", lambda e: self._apply_position())

        # Delete button (inline with position)
        self.delete_btn = ModernButton(row5, "Delete", self._delete_region,
                                       variant="ghost", width=50, height=24)
        self.delete_btn.pack(side="right", padx=2)
        self.delete_btn.configure(state="disabled")

        # Initially disable controls
        self._set_controls_enabled(False)

    def _switch_tab(self, tab_id: str):
        """Switch to the specified tab."""
        self.current_tab.set(tab_id)

        # Hide all frames
        for frame in [self._columns_frame, self._placed_frame, self._properties_frame]:
            frame.pack_forget()

        # Show selected frame
        if tab_id == "columns":
            self._columns_frame.pack(fill="both", expand=True)
        elif tab_id == "placed":
            self._placed_frame.pack(fill="both", expand=True)
            # Refresh the placed list when switching to this tab
            if self._last_regions:
                self._rebuild_placed_list()
        elif tab_id == "properties":
            self._properties_frame.pack(fill="both", expand=True)

        # Update button colors
        for tid, btn in self._tab_buttons.items():
            is_active = (tid == tab_id)
            btn.configure(
                fg_color=T().accent if is_active else "transparent",
                text_color=T().text_on_accent if is_active else T().text_white
            )

    def _update_theme(self):
        self._tab_frame.configure(fg_color=T().bg_tertiary)
        self.placed_scroll.configure(
            fg_color=T().bg_tertiary,
            scrollbar_fg_color=T().bg_secondary,
            scrollbar_button_color=T().accent_dim
        )
        self._props_content.configure(fg_color=T().bg_tertiary)
        self.selection_label.configure(text_color=T().text_primary)
        self.bold_btn.configure(fg_color=T().accent_dim if self.bold_var.get() else T().bg_hover)
        self.italic_btn.configure(fg_color=T().accent_dim if self.italic_var.get() else T().bg_hover)
        for align, btn in self.align_buttons.items():
            btn.configure(fg_color=T().accent_dim if self.align_var.get() == align else T().bg_hover)
        # Update tab buttons
        current = self.current_tab.get()
        for tid, btn in self._tab_buttons.items():
            is_active = (tid == current)
            btn.configure(
                fg_color=T().accent if is_active else "transparent",
                text_color=T().text_on_accent if is_active else T().text_white
            )

    # === COLUMN METHODS ===

    def _on_column_listbox_select(self, event):
        if self.on_column_select:
            self.on_column_select(event)

    def _on_column_listbox_double_click(self, event):
        if self.on_column_double_click:
            self.on_column_double_click(event)

    def set_columns(self, columns: List[str]):
        """Update the column list."""
        self.column_listbox.delete(0, "end")
        for col in columns:
            self.column_listbox.insert("end", col)

    def get_selected_column(self) -> Optional[str]:
        """Get currently selected column name."""
        selection = self.column_listbox.curselection()
        if selection:
            return self.column_listbox.get(selection[0])
        return None

    # === PLACED FIELDS METHODS ===

    def set_template_field_names(self, names: set):
        """Set which field names came from a drawing template (vs custom/manual)."""
        self._template_field_names = names
        self._rebuild_placed_list()

    def update_regions(self, regions: Dict[str, TextRegion], selected: str = None):
        """Update the list of placed regions."""
        # Store for later refresh
        self._last_regions = regions
        self._last_selected = selected
        self._rebuild_placed_list()

    def _rebuild_placed_list(self):
        """Rebuild the placed fields list from stored data."""
        regions = self._last_regions
        selected = self._last_selected

        # Clear existing items
        for widget in self.placed_scroll.winfo_children():
            widget.destroy()
        self.region_items = {}

        if not regions:
            empty_label = ctk.CTkLabel(
                self.placed_scroll,
                text="No fields placed yet.\nSelect column \u2192 click template",
                font=ctk.CTkFont(size=11),
                text_color=T().text_dim,
                justify="center"
            )
            empty_label.pack(pady=20)
            return

        # Split into template fields and custom fields
        tmpl_fields = {n: r for n, r in sorted(regions.items()) if n in self._template_field_names}
        custom_fields = {n: r for n, r in sorted(regions.items()) if n not in self._template_field_names}

        # Template fields group
        if tmpl_fields:
            header = ctk.CTkLabel(
                self.placed_scroll,
                text=f"TEMPLATE  ({len(tmpl_fields)})",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=T().accent, anchor="w"
            )
            header.pack(fill="x", padx=8, pady=(4, 2))

            for name, region in tmpl_fields.items():
                self._add_placed_row(name, region, selected, bar_color=T().accent)

        # Custom fields group
        if custom_fields:
            header = ctk.CTkLabel(
                self.placed_scroll,
                text=f"CUSTOM  ({len(custom_fields)})",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color="#6B8E6B", anchor="w"
            )
            header.pack(fill="x", padx=8, pady=(8 if tmpl_fields else 4, 2))

            for name, region in custom_fields.items():
                self._add_placed_row(name, region, selected, bar_color="#6B8E6B")

    def _add_placed_row(self, name: str, region, selected: str, bar_color: str):
        """Add a single field row to the placed list with a colored left border."""
        is_selected = (name == selected)

        row = ctk.CTkFrame(
            self.placed_scroll,
            fg_color=T().accent_dim if is_selected else "transparent",
            corner_radius=4
        )
        row.pack(fill="x", pady=1, padx=4)

        # Colored left border bar
        bar = ctk.CTkFrame(row, width=3, fg_color=bar_color, corner_radius=1)
        bar.pack(side="left", fill="y", padx=(2, 0), pady=2)

        # Field name
        display_name = name[:24] + "..." if len(name) > 24 else name
        label = ctk.CTkLabel(
            row,
            text=display_name,
            font=ctk.CTkFont(size=11),
            text_color=T().text_white,
            anchor="w"
        )
        label.pack(side="left", fill="x", expand=True, padx=6, pady=3)

        # Font size info
        info = ctk.CTkLabel(
            row,
            text=f"{region.font_size}pt",
            font=ctk.CTkFont(size=10),
            text_color=T().text_dim,
        )
        info.pack(side="right", padx=8, pady=3)

        # Bind click
        for widget in [row, bar, label, info]:
            widget.bind("<Button-1>", lambda e, n=name: self._on_region_click(n))

        self.region_items[name] = row

    def _on_region_click(self, name: str):
        if self.on_region_select:
            self.on_region_select(name)
        # Also switch to properties tab
        self._switch_tab("properties")

    # === PROPERTIES METHODS ===

    def _set_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.size_entry.configure(state=state)
        self.font_dropdown.configure(state=state)
        self.color_entry.configure(state=state)
        self.x_entry.configure(state=state)
        self.y_entry.configure(state=state)
        self.delete_btn.configure(state=state)

    def set_region(self, region: Optional[TextRegion]):
        """Set the region to edit."""
        self._updating = True
        self.current_region = region

        if region:
            self.selection_label.configure(text=region.column_name[:22])
            self.size_entry.delete(0, "end")
            self.size_entry.insert(0, str(region.font_size))
            self.bold_var.set(region.bold)
            self.italic_var.set(region.italic)
            self.align_var.set(region.align)
            self.color_entry.delete(0, "end")
            self.color_entry.insert(0, region.font_color)
            self.color_preview.configure(fg_color=region.font_color)
            self.x_entry.delete(0, "end")
            self.x_entry.insert(0, str(region.x))
            self.y_entry.delete(0, "end")
            self.y_entry.insert(0, str(region.y))

            # Set font selection
            font_display = "Gotham XNarrow"
            for display_name, font_file in self.available_fonts:
                if region.font_name == font_file:
                    font_display = display_name
                    break
            self.font_var.set(font_display)

            # Update button states
            self.bold_btn.configure(fg_color=T().accent_dim if region.bold else T().bg_hover)
            self.italic_btn.configure(fg_color=T().accent_dim if region.italic else T().bg_hover)
            for align, btn in self.align_buttons.items():
                btn.configure(fg_color=T().accent_dim if region.align == align else T().bg_hover)

            self._set_controls_enabled(True)
        else:
            self.selection_label.configure(text="(none selected)")
            self._set_controls_enabled(False)

        self._updating = False

    def _set_size(self, size: int):
        self.size_entry.delete(0, "end")
        self.size_entry.insert(0, str(size))
        self._apply_changes()

    def _set_color(self, color: str):
        self.color_entry.delete(0, "end")
        self.color_entry.insert(0, color)
        self.color_preview.configure(fg_color=color)
        self._apply_changes()

    def _apply_color(self):
        color = self.color_entry.get()
        if color.startswith("#") and len(color) == 7:
            self.color_preview.configure(fg_color=color)
        self._apply_changes()

    def _toggle_bold(self):
        self.bold_var.set(not self.bold_var.get())
        self.bold_btn.configure(fg_color=T().accent_dim if self.bold_var.get() else T().bg_hover)
        self._apply_changes()

    def _toggle_italic(self):
        self.italic_var.set(not self.italic_var.get())
        self.italic_btn.configure(fg_color=T().accent_dim if self.italic_var.get() else T().bg_hover)
        self._apply_changes()

    def _set_align(self, align: str):
        self.align_var.set(align)
        for a, btn in self.align_buttons.items():
            btn.configure(fg_color=T().accent_dim if a == align else T().bg_hover)
        self._apply_changes()

    def _apply_changes(self):
        if self._updating or not self.current_region:
            return

        try:
            self.current_region.font_size = int(self.size_entry.get())
        except ValueError:
            pass

        self.current_region.bold = self.bold_var.get()
        self.current_region.italic = self.italic_var.get()
        self.current_region.align = self.align_var.get()

        # Get font file name
        font_display = self.font_var.get()
        for display_name, font_file in self.available_fonts:
            if display_name == font_display:
                self.current_region.font_name = font_file
                break

        color = self.color_entry.get()
        if color.startswith("#") and len(color) == 7:
            self.current_region.font_color = color

        # Note: x/y position is only applied via _apply_position on Enter key
        # to prevent accidental repositioning from FocusOut events

        if self.on_field_change:
            self.on_field_change()

    def _apply_position(self):
        """Apply position changes - only called on explicit Enter key press."""
        if self._updating or not self.current_region:
            return
        try:
            self.current_region.x = int(self.x_entry.get())
            self.current_region.y = int(self.y_entry.get())
            if self.on_field_change:
                self.on_field_change()
        except ValueError:
            pass

    def _delete_region(self):
        if self.current_region and self.on_field_change:
            self.current_region._delete_requested = True
            self.on_field_change()

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()
