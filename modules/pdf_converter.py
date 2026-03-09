"""
PDF to Image Converter Module

Converts PDF templates to high-resolution images for processing.
Uses PyMuPDF (fitz) as primary method, falls back to pdf2image if available.
"""

import os
from pathlib import Path
from PIL import Image

# Try PyMuPDF first (no external dependencies)
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Fallback to pdf2image
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


def convert_pdf_to_image(pdf_path: str, dpi: int = 300) -> Image.Image:
    """
    Convert a PDF file to a PIL Image.

    Args:
        pdf_path: Path to the PDF file
        dpi: Resolution for conversion (default 300 for high quality)

    Returns:
        PIL Image object of the first page

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        RuntimeError: If no PDF conversion library is available
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Check if it's already an image file
    image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'}
    if pdf_path.suffix.lower() in image_extensions:
        return Image.open(pdf_path).convert('RGB')

    # Try PyMuPDF first (preferred - no external dependencies)
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(str(pdf_path))
            page = doc[0]  # First page

            # Calculate zoom factor for desired DPI (PDF default is 72 DPI)
            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)

            # Render page to pixmap
            pix = page.get_pixmap(matrix=matrix)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            return img
        except Exception as e:
            if PDF2IMAGE_AVAILABLE:
                pass  # Fall through to pdf2image
            else:
                raise RuntimeError(f"PyMuPDF failed to convert PDF: {e}") from e

    # Fallback to pdf2image
    if PDF2IMAGE_AVAILABLE:
        try:
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=1,
                last_page=1
            )

            if not images:
                raise RuntimeError(f"No pages found in PDF: {pdf_path}")

            return images[0]

        except Exception as e:
            if "poppler" in str(e).lower() or "pdftoppm" in str(e).lower():
                raise RuntimeError(
                    "Poppler is not installed or not in PATH.\n"
                    "Windows: Download from https://github.com/osber/poppler-windows/releases\n"
                    "         Extract and add the 'bin' folder to your PATH environment variable."
                ) from e
            raise

    # No conversion method available
    raise RuntimeError(
        "No PDF conversion library available.\n"
        "Install PyMuPDF: pip install PyMuPDF\n"
        "Or install pdf2image + Poppler"
    )


def get_image_from_template(template_path: str, dpi: int = 300) -> Image.Image:
    """
    Get a PIL Image from a template file (PDF or image).

    This is the main entry point for loading templates.

    Args:
        template_path: Path to template PDF or image file
        dpi: Resolution for PDF conversion

    Returns:
        PIL Image object ready for processing
    """
    return convert_pdf_to_image(template_path, dpi)
