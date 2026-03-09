"""
Form Field Reader Module

Reads PDF form fields and extracts their positions for text replacement.
Uses PyMuPDF (fitz) to read fillable form fields directly from PDFs.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FormField:
    """Represents a PDF form field."""
    name: str
    x: int
    y: int
    width: int
    height: int
    field_type: str  # "text", "checkbox", etc.
    page: int = 0


def read_form_fields(pdf_path: str, page_number: int = 0) -> Dict[str, FormField]:
    """
    Read all form fields from a PDF file.

    Args:
        pdf_path: Path to the PDF file
        page_number: Page to read fields from (0-indexed)

    Returns:
        Dictionary mapping field names to FormField objects
    """
    fields = {}

    doc = fitz.open(pdf_path)

    if page_number >= len(doc):
        doc.close()
        raise ValueError(f"Page {page_number} does not exist in PDF (has {len(doc)} pages)")

    page = doc[page_number]

    # Get all widgets (form fields) on the page
    for widget in page.widgets():
        if widget.field_name:
            # Get the rectangle (position) of the field
            rect = widget.rect

            # Determine field type
            field_type_map = {
                fitz.PDF_WIDGET_TYPE_TEXT: "text",
                fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
                fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "radio",
                fitz.PDF_WIDGET_TYPE_COMBOBOX: "combobox",
                fitz.PDF_WIDGET_TYPE_LISTBOX: "listbox",
                fitz.PDF_WIDGET_TYPE_BUTTON: "button",
                fitz.PDF_WIDGET_TYPE_SIGNATURE: "signature",
            }
            field_type = field_type_map.get(widget.field_type, "unknown")

            field = FormField(
                name=widget.field_name,
                x=int(rect.x0),
                y=int(rect.y0),
                width=int(rect.width),
                height=int(rect.height),
                field_type=field_type,
                page=page_number
            )

            fields[widget.field_name] = field

    doc.close()
    return fields


def get_form_field_info(pdf_path: str) -> dict:
    """
    Get summary information about form fields in a PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with field counts and names
    """
    doc = fitz.open(pdf_path)

    info = {
        "page_count": len(doc),
        "fields_by_page": {},
        "total_fields": 0,
        "field_names": []
    }

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_fields = []

        for widget in page.widgets():
            if widget.field_name:
                page_fields.append(widget.field_name)
                info["field_names"].append(widget.field_name)

        info["fields_by_page"][page_num] = page_fields
        info["total_fields"] += len(page_fields)

    doc.close()
    return info


def fill_form_fields(
    pdf_path: str,
    data: Dict[str, str],
    output_path: Optional[str] = None
) -> str:
    """
    Fill form fields in a PDF with data.

    Args:
        pdf_path: Path to the input PDF
        data: Dictionary mapping field names to values
        output_path: Path for output PDF (if None, modifies in place)

    Returns:
        Path to the output PDF
    """
    doc = fitz.open(pdf_path)

    for page in doc:
        for widget in page.widgets():
            if widget.field_name and widget.field_name in data:
                widget.field_value = str(data[widget.field_name])
                widget.update()

    if output_path is None:
        output_path = pdf_path

    doc.save(output_path)
    doc.close()

    return output_path


def render_pdf_with_fields_filled(
    pdf_path: str,
    data: Dict[str, str],
    dpi: int = 300,
    page_number: int = 0
) -> "Image":
    """
    Fill form fields and render PDF to image.

    Args:
        pdf_path: Path to the PDF file
        data: Dictionary mapping field names to values
        dpi: Resolution for rendering
        page_number: Page to render

    Returns:
        PIL Image of the rendered page
    """
    from PIL import Image
    import io

    doc = fitz.open(pdf_path)

    if page_number >= len(doc):
        doc.close()
        raise ValueError(f"Page {page_number} does not exist")

    # Fill the form fields
    for page in doc:
        for widget in page.widgets():
            if widget.field_name and widget.field_name in data:
                widget.field_value = str(data[widget.field_name])
                widget.update()

    # Render the page
    page = doc[page_number]
    zoom = dpi / 72  # 72 is the default PDF DPI
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Convert to PIL Image
    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))

    doc.close()
    return image


def convert_fields_to_regions(fields: Dict[str, FormField], dpi: int = 300) -> dict:
    """
    Convert form fields to region mapping format compatible with existing code.

    The PDF coordinates are at 72 DPI, so we need to scale them.

    Args:
        fields: Dictionary of FormField objects
        dpi: Target DPI for the output image

    Returns:
        Dictionary in RegionMapping format
    """
    scale = dpi / 72  # PDF default is 72 DPI

    regions = {}
    for name, field in fields.items():
        # Only include text fields
        if field.field_type == "text":
            regions[name] = {
                "label": name,
                "x": int(field.x * scale),
                "y": int(field.y * scale),
                "width": int(field.width * scale),
                "height": int(field.height * scale),
                "font_size": max(12, int(field.height * scale * 0.7)),  # Estimate font size
                "align": "left"
            }

    return {
        "regions": regions,
        "background_color": "#FFFFFF",
        "text_color": "#000000",
        "include_labels": False
    }


def has_form_fields(pdf_path: str) -> bool:
    """
    Check if a PDF has any form fields.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        True if the PDF has form fields, False otherwise
    """
    doc = fitz.open(pdf_path)
    has_fields = False

    for page in doc:
        if list(page.widgets()):
            has_fields = True
            break

    doc.close()
    return has_fields
