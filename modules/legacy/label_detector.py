"""
Label Detector Module

Detects and manages letter label positions on template images.
These are the A, B, C, etc. markers that identify data regions.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

import cv2
import numpy as np
from PIL import Image

from .highlight_detector import pil_to_cv2


@dataclass
class LabelPosition:
    """Position of a letter label on the template."""
    label: str
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'LabelPosition':
        return cls(**data)


def detect_letter_labels(
    image: Image.Image,
    search_letters: str = "ABCDEFGHI",
    min_area: int = 100,
    max_area: int = 5000
) -> Dict[str, LabelPosition]:
    """
    Detect single letter labels on an image using template matching.

    This function looks for isolated single letters (A, B, C, etc.) that
    serve as reference markers on engineering drawings.

    Args:
        image: PIL Image to analyze
        search_letters: String of letters to search for
        min_area: Minimum contour area for valid text
        max_area: Maximum contour area for valid text

    Returns:
        Dictionary mapping letter to LabelPosition
    """
    # Convert to OpenCV format
    cv_image = pil_to_cv2(image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    # Use adaptive thresholding to find text
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # Find contours
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # Filter contours by size (looking for letter-sized regions)
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area <= area <= max_area:
            x, y, w, h = cv2.boundingRect(contour)
            # Letters are roughly square-ish or taller than wide
            aspect = h / w if w > 0 else 0
            if 0.5 <= aspect <= 3.0:
                candidates.append((x, y, w, h, area))

    # Note: Full OCR detection would require pytesseract
    # For now, return empty - labels should be manually specified
    return {}


def create_label_positions_from_mapping(
    data_regions: Dict[str, dict],
    label_offsets: Optional[Dict[str, Tuple[int, int]]] = None
) -> Dict[str, LabelPosition]:
    """
    Create label positions based on data region positions and offsets.

    Many templates place labels at consistent offsets from data regions.
    This function calculates those positions.

    Args:
        data_regions: Dictionary of data region definitions
        label_offsets: Optional per-label offset overrides (dx, dy from region)

    Returns:
        Dictionary of LabelPosition objects
    """
    labels = {}

    # Default: labels are typically to the right of regions
    default_offset = (10, 0)  # 10 pixels to the right

    for label, region in data_regions.items():
        if label_offsets and label in label_offsets:
            dx, dy = label_offsets[label]
        else:
            dx, dy = default_offset

        # Create label position to the right of the region
        labels[label] = LabelPosition(
            label=label,
            x=region['x'] + region['width'] + dx,
            y=region['y'] + dy,
            width=40,  # Typical label width
            height=region['height']
        )

    return labels


def save_label_positions(
    positions: Dict[str, LabelPosition],
    path: str
):
    """Save label positions to JSON file."""
    data = {k: v.to_dict() for k, v in positions.items()}
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_label_positions(path: str) -> Dict[str, LabelPosition]:
    """Load label positions from JSON file."""
    with open(path, 'r') as f:
        data = json.load(f)
    return {k: LabelPosition.from_dict(v) for k, v in data.items()}


def remove_labels_from_image(
    image: Image.Image,
    label_positions: Dict[str, LabelPosition],
    background_color: Tuple[int, int, int] = (255, 255, 255)
) -> Image.Image:
    """
    Remove letter labels from an image by covering them with background color.

    Args:
        image: PIL Image to modify
        label_positions: Dictionary of label positions to remove
        background_color: RGB color to fill over labels

    Returns:
        Modified image (new copy)
    """
    from PIL import ImageDraw

    result = image.copy()
    draw = ImageDraw.Draw(result)

    for label, pos in label_positions.items():
        # Draw filled rectangle over the label
        draw.rectangle(
            [pos.x, pos.y, pos.x + pos.width, pos.y + pos.height],
            fill=background_color
        )

    return result
