"""
Blue Highlight Detector Module

Detects cyan/blue highlighted regions in template images using OpenCV.
Provides calibration mode for labeling regions and saving mappings.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

import cv2
import numpy as np
from PIL import Image


@dataclass
class Region:
    """Represents a detected highlight region."""
    label: str
    x: int
    y: int
    width: int
    height: int
    font_size: int = 14
    align: str = "left"  # left, center, right

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Region':
        return cls(**data)


@dataclass
class LabelPosition:
    """Position of a letter label marker on the template."""
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


@dataclass
class RegionMapping:
    """Collection of regions for a template."""
    regions: Dict[str, Region]
    background_color: str = "#FFFFFF"
    text_color: str = "#000000"
    label_positions: Optional[Dict[str, LabelPosition]] = None

    def save(self, path: str):
        """Save mapping to JSON file."""
        data = {
            "regions": {k: v.to_dict() for k, v in self.regions.items()},
            "background_color": self.background_color,
            "text_color": self.text_color
        }
        if self.label_positions:
            data["label_positions"] = {k: v.to_dict() for k, v in self.label_positions.items()}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'RegionMapping':
        """Load mapping from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)

        regions = {k: Region.from_dict(v) for k, v in data["regions"].items()}

        # Load label positions if present
        label_positions = None
        if "label_positions" in data:
            label_positions = {k: LabelPosition.from_dict(v) for k, v in data["label_positions"].items()}

        return cls(
            regions=regions,
            background_color=data.get("background_color", "#FFFFFF"),
            text_color=data.get("text_color", "#000000"),
            label_positions=label_positions
        )


def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV format (BGR)."""
    rgb = np.array(pil_image)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def detect_blue_highlights(
    image: Image.Image,
    hue_range: Tuple[int, int] = (90, 100),
    sat_range: Tuple[int, int] = (50, 255),
    val_range: Tuple[int, int] = (200, 255),
    min_area: int = 500
) -> List[Tuple[int, int, int, int]]:
    """
    Detect cyan/blue highlighted regions in an image.

    Args:
        image: PIL Image to analyze
        hue_range: HSV hue range for blue/cyan (0-180 in OpenCV)
        sat_range: HSV saturation range
        val_range: HSV value (brightness) range
        min_area: Minimum pixel area for a valid region

    Returns:
        List of bounding boxes as (x, y, width, height) tuples,
        sorted by position (top-to-bottom, left-to-right)
    """
    # Convert to OpenCV format
    cv_image = pil_to_cv2(image)
    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

    # Create mask for cyan/blue highlights
    lower = np.array([hue_range[0], sat_range[0], val_range[0]])
    upper = np.array([hue_range[1], sat_range[1], val_range[1]])
    mask = cv2.inRange(hsv, lower, upper)

    # Clean up mask with morphological operations
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Extract bounding boxes
    boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(contour)
            boxes.append((x, y, w, h))

    # Sort by position: top-to-bottom, then left-to-right
    # Group by approximate y-position (within 50 pixels = same row)
    boxes.sort(key=lambda b: (b[1] // 50, b[0]))

    return boxes


def estimate_font_size(height: int) -> int:
    """Estimate appropriate font size based on region height."""
    # Roughly 70% of height for font size
    return max(8, int(height * 0.7))


def calibrate_regions(
    image: Image.Image,
    output_path: Optional[str] = None,
    **detection_kwargs
) -> RegionMapping:
    """
    Detect regions and interactively label them.

    Args:
        image: PIL Image to analyze
        output_path: Optional path to save the mapping JSON
        **detection_kwargs: Arguments passed to detect_blue_highlights

    Returns:
        RegionMapping with labeled regions
    """
    boxes = detect_blue_highlights(image, **detection_kwargs)

    if not boxes:
        print("No blue highlighted regions detected!")
        print("Try adjusting the HSV ranges for detection.")
        return RegionMapping(regions={})

    print(f"\nDetected {len(boxes)} highlighted regions.")
    print("Please label each region (e.g., A, B, C, etc.)")
    print("Press Enter to skip a region, or 'q' to quit.\n")

    regions = {}

    # Create a preview image with numbered boxes
    cv_image = pil_to_cv2(image)
    preview = cv_image.copy()

    for i, (x, y, w, h) in enumerate(boxes):
        # Draw rectangle and number on preview
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(preview, str(i + 1), (x + 5, y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # Save preview image
    preview_path = "calibration_preview.png"
    cv2.imwrite(preview_path, preview)
    print(f"Preview saved to: {preview_path}")
    print("Open this image to see numbered regions.\n")

    for i, (x, y, w, h) in enumerate(boxes):
        print(f"Region {i + 1}: position=({x}, {y}), size=({w}x{h})")

        label = input(f"  Enter label for region {i + 1} (or Enter to skip, 'q' to quit): ").strip().upper()

        if label == 'Q':
            break
        elif label == '':
            continue
        else:
            regions[label] = Region(
                label=label,
                x=x,
                y=y,
                width=w,
                height=h,
                font_size=estimate_font_size(h),
                align="left"
            )

    mapping = RegionMapping(regions=regions)

    if output_path:
        mapping.save(output_path)
        print(f"\nMapping saved to: {output_path}")

    return mapping


def load_or_detect_regions(
    image: Image.Image,
    mapping_path: Optional[str] = None,
    **detection_kwargs
) -> RegionMapping:
    """
    Load existing mapping or detect regions.

    Args:
        image: PIL Image (used if detection needed)
        mapping_path: Path to existing mapping JSON (optional)
        **detection_kwargs: Arguments for detection if needed

    Returns:
        RegionMapping object
    """
    if mapping_path and Path(mapping_path).exists():
        return RegionMapping.load(mapping_path)

    # Auto-detect and create basic mapping with default labels
    boxes = detect_blue_highlights(image, **detection_kwargs)
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    regions = {}
    for i, (x, y, w, h) in enumerate(boxes):
        if i < len(labels):
            label = labels[i]
            regions[label] = Region(
                label=label,
                x=x,
                y=y,
                width=w,
                height=h,
                font_size=estimate_font_size(h),
                align="left"
            )

    return RegionMapping(regions=regions)


def expand_regions_for_labels(
    regions: Dict[str, Region],
    right_padding: int = 60,
    image_width: Optional[int] = None
) -> Dict[str, Region]:
    """
    Expand region widths to cover adjacent letter labels.

    The letter labels (A, B, C, etc.) on templates are typically
    printed to the right of the highlighted data areas. This function
    expands the region widths to cover those labels.

    Args:
        regions: Dictionary of Region objects
        right_padding: Pixels to add to the right of each region
        image_width: Optional image width to prevent overflow

    Returns:
        New dictionary with expanded regions
    """
    expanded = {}
    for label, region in regions.items():
        new_width = region.width + right_padding

        # Prevent overflow if image width is known
        if image_width and (region.x + new_width) > image_width:
            new_width = image_width - region.x - 5

        expanded[label] = Region(
            label=region.label,
            x=region.x,
            y=region.y,
            width=new_width,
            height=region.height,
            font_size=region.font_size,
            align=region.align
        )

    return expanded
