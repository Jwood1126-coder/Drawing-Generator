"""Template Editor Canvas - interactive canvas for editing template regions."""

import tkinter as tk
from typing import Optional, Dict, Tuple
from PIL import Image, ImageTk, ImageDraw

from themes import T, ThemeManager
from modules.template_editor import TextRegion, get_font, measure_text, measure_text_bbox


class TemplateEditorCanvas(tk.Canvas):
    """Interactive canvas for editing template regions."""

    def __init__(self, parent, on_region_changed=None):
        super().__init__(
            parent,
            bg=T().bg_tertiary,
            highlightthickness=1,
            highlightbackground=T().border
        )

        self.on_region_changed = on_region_changed

        # Image state
        self.original_image: Optional[Image.Image] = None
        self.display_image: Optional[Image.Image] = None
        self.photo: Optional[ImageTk.PhotoImage] = None
        self.scale: float = 1.0
        self.offset_x: int = 0
        self.offset_y: int = 0
        self.dpi: int = 300

        # Region state
        self.regions: Dict[str, TextRegion] = {}
        self.selected_region: Optional[str] = None
        self.sample_data: Dict[str, str] = {}
        self._template_field_names: set = set()

        # Interaction state
        self.mode = "select"
        self.pending_column: Optional[str] = None
        self.drag_start: Optional[Tuple[int, int]] = None
        self.drag_offset: Optional[Tuple[int, int]] = None
        self.is_dragging: bool = False

        # Bind events
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Button-3>", self._on_right_click)
        self.bind("<Delete>", self._on_delete)
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", lambda e: self.focus_set())

        ThemeManager.register(self._update_theme)

    def _update_theme(self):
        self.configure(bg=T().bg_tertiary, highlightbackground=T().border)

    def load_image(self, pil_image: Image.Image, dpi: int = 300):
        self.original_image = pil_image.copy()
        self.dpi = dpi
        self._render_preview()

    def set_sample_data(self, data: Dict[str, str]):
        self.sample_data = {k: str(v) if v is not None and str(v).lower() != 'nan' else ""
                          for k, v in data.items()}
        self._render_preview()

    def set_regions(self, regions: Dict[str, TextRegion]):
        self.regions = regions
        self._render_preview()
        # Notify listeners that regions changed
        if self.on_region_changed:
            self.on_region_changed()

    def set_template_field_names(self, names: set):
        """Set which field names are template fields (vs custom). Triggers redraw."""
        self._template_field_names = names
        if self.original_image:
            self._render_preview()

    def set_mode(self, mode: str, pending_column: str = None):
        self.mode = mode
        self.pending_column = pending_column
        self.config(cursor="crosshair" if mode == "place" else "")

    def _on_configure(self, event):
        self._update_display()

    def _image_to_canvas(self, x: int, y: int) -> Tuple[int, int]:
        return (int(x * self.scale) + self.offset_x, int(y * self.scale) + self.offset_y)

    def _canvas_to_image(self, cx: int, cy: int) -> Tuple[int, int]:
        return (int((cx - self.offset_x) / self.scale), int((cy - self.offset_y) / self.scale))

    def _render_preview(self):
        if self.original_image is None:
            return

        self.display_image = self.original_image.copy()
        if self.display_image.mode != 'RGBA':
            self.display_image = self.display_image.convert('RGBA')

        text_layer = Image.new('RGBA', self.display_image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        for col_name, region in self.regions.items():
            value = self.sample_data.get(col_name, "") or f"[{col_name}]"

            font = get_font(region.font_name, region.font_size, dpi=self.dpi,
                           bold=region.bold, italic=region.italic)
            text_width, text_height = measure_text(value, font)
            region.update_size(text_width, text_height)

            if region.align == "center":
                x = region.x - text_width // 2
            elif region.align == "right":
                x = region.x - text_width
            else:
                x = region.x

            draw.text((x, region.y), value, fill=region.font_color, font=font)

        self.display_image = Image.alpha_composite(self.display_image, text_layer)
        self._update_display()

    def _update_display(self):
        if self.display_image is None:
            return

        self.update_idletasks()
        canvas_w = self.winfo_width() - 20
        canvas_h = self.winfo_height() - 20

        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w, canvas_h = 800, 600

        img_w, img_h = self.display_image.size
        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h
        self.scale = min(scale_w, scale_h, 1.0)

        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)
        self.offset_x = (canvas_w - new_w) // 2 + 10
        self.offset_y = (canvas_h - new_h) // 2 + 10

        resized = self.display_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)

        self.delete("all")
        self.create_image(self.offset_x, self.offset_y, image=self.photo, anchor="nw")
        self._draw_selection_indicators()

    def _draw_selection_indicators(self):
        for col_name, region in self.regions.items():
            is_selected = (col_name == self.selected_region)
            is_template = col_name in self._template_field_names
            value = self.sample_data.get(col_name, f"[{col_name}]") or f"[{col_name}]"

            font = get_font(region.font_name, region.font_size, dpi=self.dpi,
                           bold=region.bold, italic=region.italic)
            x_off, y_off, text_width, text_height = measure_text_bbox(value, font)

            if region.align == "center":
                x = region.x - text_width // 2
            elif region.align == "right":
                x = region.x - text_width
            else:
                x = region.x

            actual_x = x + x_off
            actual_y = region.y + y_off
            padding = 3

            cx1, cy1 = self._image_to_canvas(actual_x - padding, actual_y - padding)
            cx2, cy2 = self._image_to_canvas(actual_x + text_width + padding, actual_y + text_height + padding)

            # Template fields: accent color, Custom fields: muted/green
            outline_color = T().accent if is_template else "#6B8E6B"

            if is_selected:
                self.create_rectangle(cx1, cy1, cx2, cy2, outline=T().text_warning, width=2, dash=(4, 2))
                tag_prefix = "[T] " if is_template else "[C] "
                self.create_text(cx1, cy1 - 5, text=tag_prefix + col_name, fill=T().text_warning, anchor="sw",
                               font=("Segoe UI", 9, "bold"))
            else:
                self.create_rectangle(cx1, cy1, cx2, cy2, outline=outline_color, width=1)

    def _find_region_at(self, img_x: int, img_y: int) -> Optional[str]:
        for col_name, region in self.regions.items():
            if region.contains_point(img_x, img_y):
                return col_name
        return None

    def _on_click(self, event):
        img_x, img_y = self._canvas_to_image(event.x, event.y)

        if self.mode == "place" and self.pending_column:
            new_region = TextRegion(column_name=self.pending_column, x=img_x, y=img_y, font_size=14)
            self.regions[self.pending_column] = new_region
            self.selected_region = self.pending_column
            self.set_mode("select")
            self._render_preview()
            if self.on_region_changed:
                self.on_region_changed()
            return

        clicked = self._find_region_at(img_x, img_y)
        if clicked:
            self.selected_region = clicked
            region = self.regions[clicked]
            self.drag_start = (img_x, img_y)
            self.drag_offset = (img_x - region.x, img_y - region.y)
            self._update_display()
        else:
            self.selected_region = None
            self._update_display()

    def _on_drag(self, event):
        if not self.selected_region or not self.drag_start:
            return

        img_x, img_y = self._canvas_to_image(event.x, event.y)
        region = self.regions[self.selected_region]

        if self.drag_offset:
            new_x = img_x - self.drag_offset[0]
            new_y = img_y - self.drag_offset[1]
        else:
            new_x, new_y = img_x, img_y

        region.x = new_x
        region.y = new_y

        if not self.is_dragging:
            self.is_dragging = True

        self._update_drag_elements()

    def _update_drag_elements(self):
        self.delete("drag_elements")
        if not self.selected_region:
            return

        region = self.regions[self.selected_region]
        text_width = region._cached_width
        text_height = region._cached_height

        if region.align == "center":
            x = region.x - text_width // 2
        elif region.align == "right":
            x = region.x - text_width
        else:
            x = region.x

        padding = 3
        cx1, cy1 = self._image_to_canvas(x - padding, region.y - padding)
        cx2, cy2 = self._image_to_canvas(x + text_width + padding, region.y + text_height + padding)

        self.create_rectangle(cx1, cy1, cx2, cy2, outline=T().text_warning, width=2, dash=(4, 2), tags="drag_elements")
        self.create_text(cx1, cy1 - 5, text=f"{self.selected_region} ({region.x}, {region.y})",
                        fill=T().text_warning, anchor="sw", font=("Segoe UI", 9, "bold"), tags="drag_elements")

    def _on_release(self, event):
        if self.selected_region and self.drag_start and self.is_dragging:
            self._render_preview()
            if self.on_region_changed:
                self.on_region_changed()

        self.drag_start = None
        self.drag_offset = None
        self.is_dragging = False

    def _on_right_click(self, event):
        img_x, img_y = self._canvas_to_image(event.x, event.y)
        clicked = self._find_region_at(img_x, img_y)

        if clicked:
            self.selected_region = clicked
            self._update_display()

            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label=f"Delete '{clicked}'", command=lambda: self._delete_region(clicked))
            menu.tk_popup(event.x_root, event.y_root)

    def _on_delete(self, event):
        if self.selected_region:
            self._delete_region(self.selected_region)

    def _delete_region(self, name: str):
        if name in self.regions:
            del self.regions[name]
            self.selected_region = None
            self._render_preview()
            if self.on_region_changed:
                self.on_region_changed()

    def destroy(self):
        ThemeManager.unregister(self._update_theme)
        super().destroy()
