"""
Template Editor Module

Provides visual editing of text regions on a template image.
Regions are mapped directly to Excel columns (no intermediate letter labels).
Text is overlaid transparently without covering the background.
Supports export to multiple formats including PDF.
"""

import json
import io
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Set


@dataclass
class TextRegion:
    """
    A text region that maps directly to an Excel column.

    Position is defined by x, y (top-left corner of where text starts).
    Size is auto-calculated based on font_size and text content.
    Text is rendered transparently over the background.
    """
    column_name: str  # Excel column name (e.g., "Part Number", "Description")
    x: int  # X position (left edge of text)
    y: int  # Y position (top edge of text)
    font_size: int = 14
    font_color: str = "#000000"
    font_name: str = "GothamXNarrow"  # Font file name or None for default
    align: str = "left"  # left, center, right (affects position relative to x)
    bold: bool = False
    italic: bool = False

    # These are calculated dynamically based on text content
    _cached_width: int = 100
    _cached_height: int = 20

    def to_dict(self) -> dict:
        return {
            "column_name": self.column_name,
            "x": self.x,
            "y": self.y,
            "font_size": self.font_size,
            "font_color": self.font_color,
            "font_name": self.font_name,
            "align": self.align,
            "bold": self.bold,
            "italic": self.italic
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TextRegion':
        return cls(
            column_name=data["column_name"],
            x=data["x"],
            y=data["y"],
            font_size=data.get("font_size", 14),
            font_color=data.get("font_color", "#000000"),
            font_name=data.get("font_name", "GothamXNarrow"),
            align=data.get("align", "left"),
            bold=data.get("bold", False),
            italic=data.get("italic", False)
        )

    def update_size(self, width: int, height: int):
        """Update cached size based on rendered text dimensions."""
        self._cached_width = max(width, 20)
        self._cached_height = max(height, 10)

    @property
    def width(self) -> int:
        return self._cached_width

    @property
    def height(self) -> int:
        return self._cached_height

    def contains_point(self, px: int, py: int, padding: int = 5) -> bool:
        """Check if a point is inside this region (with padding for easier clicking)."""
        return (self.x - padding <= px <= self.x + self._cached_width + padding and
                self.y - padding <= py <= self.y + self._cached_height + padding)


@dataclass
class TemplateMapping:
    """
    Mapping of text regions to Excel columns for a template.
    """
    template_name: str  # Name/identifier for this template
    template_path: str  # Path to the template file
    regions: Dict[str, TextRegion] = field(default_factory=dict)  # column_name -> TextRegion
    dpi: int = 300  # DPI used when creating the mapping

    def add_region(self, region: TextRegion):
        """Add a text region."""
        self.regions[region.column_name] = region

    def remove_region(self, column_name: str):
        """Remove a region by column name."""
        if column_name in self.regions:
            del self.regions[column_name]

    def get_region_at_point(self, px: int, py: int) -> Optional[TextRegion]:
        """Find region containing the given point."""
        for region in self.regions.values():
            if region.contains_point(px, py):
                return region
        return None

    def save(self, path: str):
        """Save mapping to JSON file."""
        data = {
            "template_name": self.template_name,
            "template_path": self.template_path,
            "dpi": self.dpi,
            "regions": {name: region.to_dict() for name, region in self.regions.items()}
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'TemplateMapping':
        """Load mapping from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)

        regions = {}
        for name, region_data in data.get("regions", {}).items():
            regions[name] = TextRegion.from_dict(region_data)

        return cls(
            template_name=data.get("template_name", ""),
            template_path=data.get("template_path", ""),
            regions=regions,
            dpi=data.get("dpi", 300)
        )


@dataclass
class FieldTemplate:
    """
    A reusable drawing template — field positions, formatting, and project context.

    Like a SolidWorks drawing template: defines where text fields go and how
    they're formatted. Optionally stores file paths and export settings so
    the entire project can be restored from a single save.
    """
    name: str
    regions: Dict[str, TextRegion] = field(default_factory=dict)
    dpi: int = 300

    # Optional project context (stored alongside layout for convenience)
    template_path: str = ""
    excel_path: str = ""
    output_dir: str = ""
    export_settings: Optional[dict] = None

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "dpi": self.dpi,
            "regions": {name: region.to_dict() for name, region in self.regions.items()}
        }
        if self.template_path:
            d["template_path"] = self.template_path
        if self.excel_path:
            d["excel_path"] = self.excel_path
        if self.output_dir:
            d["output_dir"] = self.output_dir
        if self.export_settings:
            d["export_settings"] = self.export_settings
        return d

    @classmethod
    def from_dict(cls, data: dict) -> 'FieldTemplate':
        regions = {}
        for name, region_data in data.get("regions", {}).items():
            regions[name] = TextRegion.from_dict(region_data)
        return cls(
            name=data.get("name", ""),
            regions=regions,
            dpi=data.get("dpi", 300),
            template_path=data.get("template_path", ""),
            excel_path=data.get("excel_path", ""),
            output_dir=data.get("output_dir", ""),
            export_settings=data.get("export_settings")
        )


class TemplateLibraryManager:
    """Manages field templates as individual .dgt files in a templates/ subfolder."""

    def __init__(self, library_path: str):
        self.templates_dir = Path(library_path) / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._migrate_old_formats(library_path)

    def _migrate_old_formats(self, library_path: str):
        """Migrate from old templates.json or base_templates.json to individual .dgt files."""
        for old_name in ("templates.json", "base_templates.json"):
            old_file = Path(library_path) / old_name
            if not old_file.exists():
                continue
            try:
                with open(old_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for name, tdata in data.items():
                    dgt_path = self.templates_dir / f"{name}.dgt"
                    if dgt_path.exists():
                        continue  # Don't overwrite existing .dgt files
                    tmpl = FieldTemplate.from_dict(tdata)
                    DrawingTemplate.export_to_dgt(
                        str(dgt_path),
                        regions=tmpl.regions,
                        dpi=tmpl.dpi,
                        export_settings=tmpl.export_settings
                    )
                # Rename old file so migration doesn't repeat
                old_file.rename(old_file.with_suffix(old_file.suffix + ".migrated"))
            except (json.JSONDecodeError, OSError):
                pass

    def set_library_path(self, new_path: str):
        """Change the library directory at runtime."""
        self.templates_dir = Path(new_path) / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def list_names(self) -> List[str]:
        """Get sorted list of template names (filenames without .dgt extension)."""
        if not self.templates_dir.exists():
            return []
        return sorted(p.stem for p in self.templates_dir.glob("*.dgt"))

    def get(self, name: str) -> Optional[FieldTemplate]:
        """Get a template by name (reads the .dgt file)."""
        dgt_path = self.templates_dir / f"{name}.dgt"
        if not dgt_path.exists():
            return None
        try:
            data = DrawingTemplate.import_from_dgt(str(dgt_path))
            return FieldTemplate(
                name=name,
                regions=data["regions"],
                dpi=data.get("dpi", 300),
                export_settings=data.get("export_settings")
            )
        except (json.JSONDecodeError, OSError):
            return None

    def save_template(self, template: FieldTemplate):
        """Save a template as a .dgt file."""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        dgt_path = self.templates_dir / f"{template.name}.dgt"
        DrawingTemplate.export_to_dgt(
            str(dgt_path),
            regions=template.regions,
            dpi=template.dpi,
            export_settings=template.export_settings
        )

    def delete(self, name: str) -> bool:
        """Delete a template's .dgt file. Returns True if it existed."""
        dgt_path = self.templates_dir / f"{name}.dgt"
        if dgt_path.exists():
            dgt_path.unlink()
            return True
        return False

    def count(self) -> int:
        """Return number of template files."""
        if not self.templates_dir.exists():
            return 0
        return len(list(self.templates_dir.glob("*.dgt")))


def load_settings(data_dir: str) -> dict:
    """Load settings.json from app data dir."""
    settings_path = Path(data_dir) / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_settings(data_dir: str, settings: dict):
    """Save settings.json to app data dir."""
    settings_path = Path(data_dir) / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)


class DrawingTemplate:
    """
    Exportable/importable template file (.dgt format).

    A .dgt file is JSON containing field placements, formatting, and export
    settings — everything needed to recreate a template on a different machine.
    Excludes machine-specific data (file paths, edited row data).
    """

    VERSION = "1.0"

    @staticmethod
    def export_to_dgt(filepath: str, regions: Dict[str, TextRegion],
                      dpi: int = 300, export_settings: dict = None):
        """Export current template configuration to a .dgt file."""
        data = {
            "version": DrawingTemplate.VERSION,
            "dpi": dpi,
            "regions": {name: region.to_dict() for name, region in regions.items()},
            "export_settings": export_settings or {}
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def import_from_dgt(filepath: str) -> dict:
        """
        Import template configuration from a .dgt file.

        Returns dict with keys: version, dpi, regions (Dict[str, TextRegion]),
        export_settings, base_template_ref
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        regions = {}
        for name, region_data in data.get("regions", {}).items():
            regions[name] = TextRegion.from_dict(region_data)

        return {
            "version": data.get("version", "1.0"),
            "dpi": data.get("dpi", 300),
            "regions": regions,
            "export_settings": data.get("export_settings", {}),
            "base_template_ref": data.get("base_template_ref", "")
        }


# Font cache to avoid repeated loading
_font_cache: Dict[tuple, any] = {}


def get_font(font_path: Optional[str], size: int, dpi: int = 72, bold: bool = False, italic: bool = False):
    """
    Load a font with fallback to default. Uses caching for performance.

    Args:
        font_path: Path to font file, font name, or None for Gotham XNarrow
        size: Font size in points
        dpi: Target DPI (default 72 for screen, use 300 for print)
        bold: Use bold variant
        italic: Use italic variant

    Returns:
        PIL ImageFont object scaled for the target DPI
    """
    from PIL import ImageFont

    # Scale point size to pixels based on DPI
    # Standard: 72 points = 1 inch, so at 300 DPI we need more pixels
    pixel_size = int(size * dpi / 72)

    # Check cache first
    cache_key = (font_path, pixel_size, bold, italic)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    # Font names to try (in order of preference)
    font_names = []

    # Determine style suffix
    if bold and italic:
        style_suffixes = ["-BoldItalic", "-BoldOblique", "bi", "z"]
    elif bold:
        style_suffixes = ["-Bold", "-Medium", "bd", "b"]
    elif italic:
        style_suffixes = ["-Italic", "-Oblique", "i"]
    else:
        style_suffixes = ["-Book", "-Regular", "", "-Medium"]

    if font_path:
        # User specified a font - try various forms with style
        base_name = font_path.replace(".ttf", "").replace(".otf", "")
        for suffix in style_suffixes:
            font_names.append(f"{base_name}{suffix}.otf")
            font_names.append(f"{base_name}{suffix}.ttf")
            font_names.append(f"{base_name}{suffix}")
        # Also try the exact path
        font_names.append(font_path)

    # Gotham XNarrow variations based on style
    gotham_bases = ["GothamXNarrow", "Gotham XNarrow", "gothamxnarrow"]
    for base in gotham_bases:
        for suffix in style_suffixes:
            font_names.append(f"{base}{suffix}.otf")
            font_names.append(f"{base}{suffix}.ttf")
            font_names.append(f"{base}{suffix}")

    # Arial fallbacks with style
    if bold and italic:
        font_names.extend(["arialbi.ttf", "Arial Bold Italic"])
    elif bold:
        font_names.extend(["arialbd.ttf", "Arial Bold"])
    elif italic:
        font_names.extend(["ariali.ttf", "Arial Italic"])
    else:
        font_names.extend(["arial.ttf", "Arial"])

    for font_name in font_names:
        try:
            font = ImageFont.truetype(font_name, pixel_size)
            _font_cache[cache_key] = font
            return font
        except:
            continue

    # Last resort - use default font
    font = ImageFont.load_default()
    _font_cache[cache_key] = font
    return font


def measure_text(text: str, font) -> Tuple[int, int]:
    """Measure the size of text with given font. Returns (width, height)."""
    from PIL import ImageDraw, Image
    # Create a temporary image to measure text
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def measure_text_bbox(text: str, font) -> Tuple[int, int, int, int]:
    """
    Measure text and return full bounding box offsets.
    Returns (x_offset, y_offset, width, height) where offsets are relative to draw position.
    """
    from PIL import ImageDraw, Image
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    # bbox = (left, top, right, bottom) relative to (0, 0)
    return bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]


def apply_template_mapping(
    template_image,
    mapping: TemplateMapping,
    row_data: dict,
    font_path: Optional[str] = None
):
    """
    Apply data to template using the mapping.
    Text is overlaid TRANSPARENTLY - no background fill.

    Args:
        template_image: PIL Image of the template
        mapping: TemplateMapping with region definitions
        row_data: Dictionary of column_name -> value
        font_path: Optional path to font file

    Returns:
        PIL Image with text overlaid (transparent background)
    """
    from PIL import Image, ImageDraw, ImageFont

    # Create a copy to work on
    result = template_image.copy()

    # Convert to RGBA if not already (for transparency support)
    if result.mode != 'RGBA':
        result = result.convert('RGBA')

    # Create a transparent overlay for text
    text_layer = Image.new('RGBA', result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    # Get DPI from mapping for proper font scaling
    dpi = mapping.dpi if mapping.dpi else 300

    for column_name, region in mapping.regions.items():
        # Get the value for this column
        value = row_data.get(column_name, "")
        if value is None:
            value = ""
        value = str(value)

        # Handle 'nan' values from pandas
        if value.lower() == 'nan':
            value = ""

        if not value:
            continue

        # Load font with DPI scaling and style
        # Use region's font_name if set, otherwise fall back to font_path parameter
        region_font = region.font_name if region.font_name else font_path
        font = get_font(region_font, region.font_size, dpi=dpi, bold=region.bold, italic=region.italic)

        # Measure text
        text_width, text_height = measure_text(value, font)

        # Calculate position based on alignment
        # x, y in region is the anchor point
        if region.align == "center":
            x = region.x - text_width // 2
        elif region.align == "right":
            x = region.x - text_width
        else:  # left
            x = region.x

        y = region.y

        # Draw text directly on transparent layer (no background fill!)
        draw.text((x, y), value, fill=region.font_color, font=font)

    # Composite the text layer onto the result
    result = Image.alpha_composite(result, text_layer)

    return result


def render_preview_with_sample(
    template_image,
    mapping: TemplateMapping,
    row_data: dict,
    font_path: Optional[str] = None
) -> Tuple:
    """
    Render a preview and return both the image and updated region sizes.

    Returns:
        (preview_image, {column_name: (width, height), ...})
    """
    from PIL import Image, ImageDraw

    result = template_image.copy()
    if result.mode != 'RGBA':
        result = result.convert('RGBA')

    text_layer = Image.new('RGBA', result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    region_sizes = {}

    for column_name, region in mapping.regions.items():
        value = row_data.get(column_name, "")
        if value is None:
            value = ""
        value = str(value)
        if value.lower() == 'nan':
            value = ""

        font = get_font(font_path, region.font_size)

        if value:
            text_width, text_height = measure_text(value, font)
        else:
            # Use placeholder size for empty values
            text_width, text_height = measure_text(f"[{column_name}]", font)

        region_sizes[column_name] = (text_width, text_height)

        # Calculate position
        if region.align == "center":
            x = region.x - text_width // 2
        elif region.align == "right":
            x = region.x - text_width
        else:
            x = region.x

        y = region.y

        if value:
            draw.text((x, y), value, fill=region.font_color, font=font)

    result = Image.alpha_composite(result, text_layer)
    return result, region_sizes


def save_image_as_pdf(image, output_path: str, dpi: int = 300, optimize_size: bool = True):
    """
    Save a PIL Image as a PDF file with optimized file size.

    Args:
        image: PIL Image object
        output_path: Path to save the PDF
        dpi: DPI for the PDF (affects print quality)
        optimize_size: If True, compress the image for smaller file size
    """
    from PIL import Image
    import io

    # Convert to RGB if necessary (PDF doesn't support RGBA)
    if image.mode in ('RGBA', 'P'):
        # Create white background and paste image onto it
        bg = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'RGBA':
            bg.paste(image, mask=image.split()[3])  # Use alpha channel as mask
        else:
            bg.paste(image)
        image = bg
    elif image.mode != 'RGB':
        image = image.convert('RGB')

    if optimize_size:
        # For optimized PDF: compress as JPEG first, then embed in PDF
        # This significantly reduces file size (from ~24MB to ~500KB typically)
        jpeg_buffer = io.BytesIO()
        image.save(jpeg_buffer, 'JPEG', quality=85, optimize=True)
        jpeg_buffer.seek(0)
        compressed_image = Image.open(jpeg_buffer)

        # Save as PDF with the compressed image
        compressed_image.save(output_path, 'PDF', resolution=dpi)
    else:
        # Save as PDF directly (larger file size)
        image.save(output_path, 'PDF', resolution=dpi)


def save_image_multi_format(
    image,
    output_dir: str,
    base_filename: str,
    formats: Set[str],
    dpi: int = 300,
    jpeg_quality: int = 95,
    size_limits: Dict[str, int] = None,
    allow_resize: bool = True
) -> Dict[str, str]:
    """
    Save an image in multiple formats simultaneously with optional size limits.

    Args:
        image: PIL Image object
        output_dir: Directory to save files
        base_filename: Base filename without extension
        formats: Set of format strings (e.g., {'png', 'jpg', 'pdf', 'webp', 'bmp', 'tiff'})
        dpi: DPI for PDF export
        jpeg_quality: Quality for JPEG/WebP (1-100)
        size_limits: Dict of {format: max_size_bytes} for formats that have limits
        allow_resize: If True, allow dimension scaling to meet size limits

    Returns:
        Dictionary of {format: filepath} for successfully saved files
    """
    from PIL import Image
    from pathlib import Path
    from modules.size_limits import save_image_with_size_limit

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_files = {}
    size_limits = size_limits or {}

    for fmt in formats:
        fmt_lower = fmt.lower().strip()

        try:
            filepath = output_path / f"{base_filename}.{fmt_lower if fmt_lower not in ('jpeg', 'tif') else ('jpg' if fmt_lower == 'jpeg' else 'tiff')}"

            # Check if this format has a size limit
            max_size = size_limits.get(fmt_lower)
            if max_size:
                # Use size-limited save
                success, final_size, error_msg = save_image_with_size_limit(
                    image, str(filepath), fmt_lower, max_size,
                    initial_quality=jpeg_quality,
                    min_quality=10,
                    allow_resize=allow_resize
                )
                if success:
                    saved_files[fmt_lower] = str(filepath)
                    if error_msg:  # Contains resize info
                        saved_files[f'{fmt_lower}_info'] = error_msg
                else:
                    saved_files[f'{fmt_lower}_error'] = error_msg or f"Failed to meet size limit"
                continue

            # No size limit - save normally
            if fmt_lower == 'pdf':
                filepath = output_path / f"{base_filename}.pdf"
                save_image_as_pdf(image, str(filepath), dpi=dpi)
                saved_files['pdf'] = str(filepath)

            elif fmt_lower in ('jpg', 'jpeg'):
                filepath = output_path / f"{base_filename}.jpg"
                # Convert to RGB for JPEG
                img_to_save = image
                if img_to_save.mode in ('RGBA', 'P'):
                    bg = Image.new('RGB', img_to_save.size, (255, 255, 255))
                    if img_to_save.mode == 'RGBA':
                        bg.paste(img_to_save, mask=img_to_save.split()[3])
                    else:
                        bg.paste(img_to_save)
                    img_to_save = bg
                elif img_to_save.mode != 'RGB':
                    img_to_save = img_to_save.convert('RGB')
                img_to_save.save(filepath, 'JPEG', quality=jpeg_quality, optimize=True)
                saved_files['jpg'] = str(filepath)

            elif fmt_lower == 'png':
                filepath = output_path / f"{base_filename}.png"
                image.save(filepath, 'PNG', optimize=True)
                saved_files['png'] = str(filepath)

            elif fmt_lower == 'webp':
                filepath = output_path / f"{base_filename}.webp"
                image.save(filepath, 'WEBP', quality=jpeg_quality, method=6)
                saved_files['webp'] = str(filepath)

            elif fmt_lower == 'bmp':
                filepath = output_path / f"{base_filename}.bmp"
                # Convert to RGB for BMP
                img_to_save = image
                if img_to_save.mode in ('RGBA', 'P'):
                    bg = Image.new('RGB', img_to_save.size, (255, 255, 255))
                    if img_to_save.mode == 'RGBA':
                        bg.paste(img_to_save, mask=img_to_save.split()[3])
                    else:
                        bg.paste(img_to_save)
                    img_to_save = bg
                img_to_save.save(filepath, 'BMP')
                saved_files['bmp'] = str(filepath)

            elif fmt_lower in ('tiff', 'tif'):
                filepath = output_path / f"{base_filename}.tiff"
                image.save(filepath, 'TIFF', compression='tiff_lzw')
                saved_files['tiff'] = str(filepath)

            elif fmt_lower == 'gif':
                filepath = output_path / f"{base_filename}.gif"
                # Convert to palette mode for GIF
                img_to_save = image
                if img_to_save.mode == 'RGBA':
                    # Create white background
                    bg = Image.new('RGB', img_to_save.size, (255, 255, 255))
                    bg.paste(img_to_save, mask=img_to_save.split()[3])
                    img_to_save = bg
                img_to_save = img_to_save.convert('P', palette=Image.ADAPTIVE, colors=256)
                img_to_save.save(filepath, 'GIF')
                saved_files['gif'] = str(filepath)

        except Exception as e:
            print(f"Warning: Failed to save {fmt_lower}: {e}")
            continue

    return saved_files
