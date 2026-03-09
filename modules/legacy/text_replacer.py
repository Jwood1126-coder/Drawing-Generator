"""
Text Replacer Module

Clears highlighted regions and overlays new text.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from .highlight_detector import Region, RegionMapping, LabelPosition


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def find_system_font(font_name: str = "arial") -> str:
    """
    Find a system font file.

    Args:
        font_name: Name of the font (without extension)

    Returns:
        Path to the font file
    """
    # Common font locations on Windows
    font_dirs = [
        "C:/Windows/Fonts",
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"),
    ]

    font_variants = [
        f"{font_name}.ttf",
        f"{font_name.lower()}.ttf",
        f"{font_name.upper()}.ttf",
        f"{font_name.capitalize()}.ttf",
        f"{font_name}bd.ttf",  # Bold variant
    ]

    for font_dir in font_dirs:
        for variant in font_variants:
            font_path = os.path.join(font_dir, variant)
            if os.path.exists(font_path):
                return font_path

    # Fallback fonts
    fallbacks = ["arial.ttf", "calibri.ttf", "verdana.ttf", "tahoma.ttf"]
    for font_dir in font_dirs:
        for fallback in fallbacks:
            font_path = os.path.join(font_dir, fallback)
            if os.path.exists(font_path):
                return font_path

    # If nothing found, return None (will use default)
    return None


def get_font(size: int, font_path: Optional[str] = None, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Get a PIL font object.

    Args:
        size: Font size in points
        font_path: Optional path to specific font file
        bold: Whether to use bold variant

    Returns:
        PIL ImageFont object
    """
    if font_path and os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)

    # Try to find Arial (or similar)
    font_name = "arialbd" if bold else "arial"
    system_font = find_system_font(font_name)

    if system_font:
        return ImageFont.truetype(system_font, size)

    # Last resort: default font (may look different)
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()


def calculate_font_size(
    text: str,
    max_width: int,
    max_height: int,
    start_size: int = 24,
    min_size: int = 8,
    font_path: Optional[str] = None
) -> int:
    """
    Calculate the largest font size that fits text within bounds.

    Args:
        text: Text to fit
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        start_size: Starting font size to try
        min_size: Minimum acceptable font size
        font_path: Optional path to font file

    Returns:
        Optimal font size
    """
    for size in range(start_size, min_size - 1, -1):
        font = get_font(size, font_path)
        # Get text bounding box
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if text_width <= max_width and text_height <= max_height:
            return size

    return min_size


def replace_region_text(
    image: Image.Image,
    region: Region,
    text: str,
    background_color: str = "#FFFFFF",
    text_color: str = "#000000",
    font_path: Optional[str] = None,
    padding: int = 2
) -> Image.Image:
    """
    Replace text in a single region.

    Args:
        image: PIL Image to modify (will be modified in place)
        region: Region object defining the area
        text: New text to place
        background_color: Color to fill region background
        text_color: Color for text
        font_path: Optional path to font file
        padding: Padding inside region

    Returns:
        Modified image (same object)
    """
    draw = ImageDraw.Draw(image)

    # Clear the region with background color
    bg_rgb = hex_to_rgb(background_color)
    draw.rectangle(
        [region.x, region.y, region.x + region.width, region.y + region.height],
        fill=bg_rgb
    )

    if not text:
        return image

    # Calculate available space
    available_width = region.width - (padding * 2)
    available_height = region.height - (padding * 2)

    # Calculate optimal font size
    font_size = calculate_font_size(
        text,
        available_width,
        available_height,
        start_size=region.font_size,
        font_path=font_path
    )

    font = get_font(font_size, font_path)
    text_rgb = hex_to_rgb(text_color)

    # Get text dimensions
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate position based on alignment
    if region.align == "center":
        x = region.x + (region.width - text_width) // 2
    elif region.align == "right":
        x = region.x + region.width - text_width - padding
    else:  # left
        x = region.x + padding

    # Vertical centering
    y = region.y + (region.height - text_height) // 2 - bbox[1]

    # Draw the text
    draw.text((x, y), text, font=font, fill=text_rgb)

    return image


def remove_label_markers(
    image: Image.Image,
    label_positions: Dict[str, LabelPosition],
    background_color: str = "#FFFFFF"
) -> Image.Image:
    """
    Remove letter label markers (A, B, C, etc.) from an image.

    Args:
        image: PIL Image to modify (will be modified in place)
        label_positions: Dictionary of label positions to remove
        background_color: Color to fill over labels

    Returns:
        Modified image (same object)
    """
    draw = ImageDraw.Draw(image)
    bg_rgb = hex_to_rgb(background_color)

    for label, pos in label_positions.items():
        # Draw filled rectangle over the label
        draw.rectangle(
            [pos.x, pos.y, pos.x + pos.width, pos.y + pos.height],
            fill=bg_rgb
        )

    return image


def replace_all_regions(
    image: Image.Image,
    mapping: RegionMapping,
    data: Dict[str, str],
    font_path: Optional[str] = None,
    remove_labels: bool = False
) -> Image.Image:
    """
    Replace text in all regions defined in the mapping.

    Args:
        image: PIL Image to modify
        mapping: RegionMapping with region definitions
        data: Dictionary mapping labels to text values
        font_path: Optional path to font file
        remove_labels: Whether to remove letter label markers (A, B, C, etc.)

    Returns:
        Modified image (new copy)
    """
    # Work on a copy
    result = image.copy()

    # Remove letter labels if requested and positions are defined
    if remove_labels and mapping.label_positions:
        remove_label_markers(
            result,
            mapping.label_positions,
            background_color=mapping.background_color
        )

    for label, region in mapping.regions.items():
        text = data.get(label, "")
        replace_region_text(
            result,
            region,
            text,
            background_color=mapping.background_color,
            text_color=mapping.text_color,
            font_path=font_path
        )

    return result
