# Size Limits Module for Part Drawing Generator
# Provides save functions for file size constraints

import io
import os
from PIL import Image
from typing import Tuple, Optional


# ============================================================================
# SIZE-CONSTRAINED IMAGE SAVING FUNCTIONS
# ============================================================================

def save_image_with_size_limit(
    image,
    output_path: str,
    format: str,
    max_size_bytes: int,
    initial_quality: int = 95,
    min_quality: int = 10,
    allow_resize: bool = False,
    min_scale: float = 0.1
) -> Tuple[bool, int, Optional[str]]:
    """
    Save image with file size constraint using quality reduction and optional dimension scaling.

    Args:
        image: PIL Image object
        output_path: Path to save the file
        format: Output format (jpg, png, webp, etc.)
        max_size_bytes: Maximum file size in bytes
        initial_quality: Starting quality for lossy formats (default 95)
        min_quality: Minimum acceptable quality (default 10)
        allow_resize: If True, scale down dimensions when quality alone can't meet limit
        min_scale: Minimum scale factor (default 0.1 = 10% of original size)

    Returns:
        Tuple of (success: bool, final_size_bytes: int, error_message: str or None)
    """
    fmt_lower = format.lower()

    # Try saving with quality reduction first
    if fmt_lower == 'bmp':
        result = _save_bmp_with_size_limit(image, output_path, max_size_bytes)
    elif fmt_lower in ('jpg', 'jpeg', 'webp'):
        result = _save_lossy_with_size_limit(image, output_path, fmt_lower, max_size_bytes, initial_quality, min_quality)
    elif fmt_lower == 'png':
        result = _save_png_with_size_limit(image, output_path, max_size_bytes)
    elif fmt_lower in ('tiff', 'tif'):
        result = _save_tiff_with_size_limit(image, output_path, max_size_bytes)
    elif fmt_lower == 'gif':
        result = _save_gif_with_size_limit(image, output_path, max_size_bytes)
    elif fmt_lower == 'pdf':
        result = _save_pdf_with_size_limit(image, output_path, max_size_bytes, initial_quality, min_quality)
    else:
        return (False, 0, f"Size limits not supported for format: {format}")

    # If successful or resize not allowed, return result
    if result[0] or not allow_resize:
        return result

    # Quality reduction failed - try dimension scaling
    return _save_with_dimension_scaling(
        image, output_path, fmt_lower, max_size_bytes,
        initial_quality, min_quality, min_scale
    )


def _save_with_dimension_scaling(
    image, output_path: str, format: str, max_size_bytes: int,
    initial_quality: int, min_quality: int, min_scale: float
) -> Tuple[bool, int, Optional[str]]:
    """
    Scale down image dimensions to meet file size limit using binary search.

    Uses binary search to find the largest scale factor that produces a file
    under the size limit, maximizing output quality.
    """
    original_size = image.size

    # Helper function to get file size at a given scale
    def get_size_at_scale(scale: float) -> Tuple[int, bytes]:
        new_width = int(original_size[0] * scale)
        new_height = int(original_size[1] * scale)

        if new_width < 10 or new_height < 10:
            return (float('inf'), b'')

        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()

        if format in ('jpg', 'jpeg'):
            img_to_save = _prepare_for_jpeg(resized)
            img_to_save.save(buffer, 'JPEG', quality=initial_quality, optimize=True)
        elif format == 'webp':
            resized.save(buffer, 'WEBP', quality=initial_quality)
        elif format == 'png':
            resized.save(buffer, 'PNG', optimize=True)
        elif format in ('tiff', 'tif'):
            resized.save(buffer, 'TIFF', compression='tiff_lzw')
        elif format == 'gif':
            img_to_save = _prepare_for_gif(resized)
            img_to_save.save(buffer, 'GIF')
        elif format == 'bmp':
            img_to_save = _prepare_for_bmp(resized)
            img_to_save.save(buffer, 'BMP')
        elif format == 'pdf':
            img_to_save = _prepare_for_jpeg(resized)
            jpeg_buffer = io.BytesIO()
            img_to_save.save(jpeg_buffer, 'JPEG', quality=initial_quality, optimize=True)
            jpeg_buffer.seek(0)
            compressed = Image.open(jpeg_buffer)
            compressed.save(buffer, 'PDF', resolution=300)

        return (buffer.tell(), buffer.getvalue())

    # Binary search for optimal scale (find largest scale that fits)
    low_scale = min_scale
    high_scale = 1.0
    best_data = None
    best_size = None
    best_scale = None

    # First check if we even need to scale
    size_at_full, data_at_full = get_size_at_scale(1.0)
    if size_at_full <= max_size_bytes:
        with open(output_path, 'wb') as f:
            f.write(data_at_full)
        return (True, size_at_full, None)

    # Check if minimum scale can achieve the target
    size_at_min, _ = get_size_at_scale(min_scale)
    if size_at_min > max_size_bytes:
        min_pct = int(min_scale * 100)
        return (False, size_at_min,
                f"Cannot achieve {max_size_bytes//1024}KB even at {min_pct}% scale. "
                f"Minimum size: {size_at_min//1024}KB. Original: {original_size[0]}x{original_size[1]}")

    # Binary search for the largest scale that fits
    iterations = 0
    max_iterations = 20  # Prevent infinite loops

    while iterations < max_iterations:
        iterations += 1
        mid_scale = (low_scale + high_scale) / 2

        # Stop when we've narrowed down to within 1% scale difference
        if high_scale - low_scale < 0.01:
            break

        size_at_mid, data_at_mid = get_size_at_scale(mid_scale)

        if size_at_mid <= max_size_bytes:
            # This scale works - try larger
            best_data = data_at_mid
            best_size = size_at_mid
            best_scale = mid_scale
            low_scale = mid_scale
        else:
            # Too big - try smaller
            high_scale = mid_scale

    # If we found a working scale in the search, use it
    # Otherwise, do one more try at the low_scale which should work
    if best_data is None:
        best_size, best_data = get_size_at_scale(low_scale)
        best_scale = low_scale

    if best_data and best_size <= max_size_bytes:
        with open(output_path, 'wb') as f:
            f.write(best_data)
        scale_pct = int(best_scale * 100)
        new_w = int(original_size[0] * best_scale)
        new_h = int(original_size[1] * best_scale)
        return (True, best_size, f"Resized to {scale_pct}% ({new_w}x{new_h})")

    # Shouldn't reach here, but handle gracefully
    return (False, best_size or 0,
            f"Cannot achieve {max_size_bytes//1024}KB. Best: {(best_size or 0)//1024}KB")


# ============================================================================
# IMAGE PREPARATION HELPERS
# ============================================================================

def _prepare_for_jpeg(image) -> Image.Image:
    """Prepare an image for JPEG format (convert to RGB)."""
    if image.mode in ('RGBA', 'P'):
        bg = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'RGBA':
            bg.paste(image, mask=image.split()[3])
        else:
            bg.paste(image)
        return bg
    elif image.mode != 'RGB':
        return image.convert('RGB')
    return image


def _prepare_for_bmp(image) -> Image.Image:
    """Prepare an image for BMP format (convert to RGB)."""
    return _prepare_for_jpeg(image)  # Same requirements


def _prepare_for_gif(image) -> Image.Image:
    """Prepare an image for GIF format (convert to palette mode)."""
    img = image
    if img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    return img.convert('P', palette=Image.ADAPTIVE, colors=256)


# ============================================================================
# FORMAT-SPECIFIC SAVE FUNCTIONS
# ============================================================================

def _save_bmp_with_size_limit(image, output_path: str, max_size_bytes: int) -> Tuple[bool, int, Optional[str]]:
    """BMP has no compression. Saves file even if over limit."""
    img = _prepare_for_bmp(image)

    # Save the BMP
    img.save(output_path, 'BMP')
    actual_size = os.path.getsize(output_path)

    if actual_size <= max_size_bytes:
        return (True, actual_size, None)
    else:
        return (False, actual_size,
                f"BMP saved at {actual_size//1024}KB (limit: {max_size_bytes//1024}KB). "
                f"BMP has no compression - enable resize or use JPG/WebP.")


def _save_lossy_with_size_limit(image, output_path: str, format: str, max_size_bytes: int,
                                 initial_quality: int, min_quality: int) -> Tuple[bool, int, Optional[str]]:
    """
    Binary search for optimal quality for JPG/WebP.

    Finds the highest quality setting that produces a file under the size limit.
    """
    img = _prepare_for_jpeg(image) if format in ('jpg', 'jpeg') else image

    # First check if we need to reduce quality at all
    buffer = io.BytesIO()
    if format in ('jpg', 'jpeg'):
        img.save(buffer, 'JPEG', quality=initial_quality, optimize=True)
    else:
        img.save(buffer, 'WEBP', quality=initial_quality)

    if buffer.tell() <= max_size_bytes:
        # Already under limit at initial quality
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
        return (True, buffer.tell(), None)

    low, high = min_quality, initial_quality
    best_data = None
    best_quality = None

    # Binary search for optimal quality
    while low <= high:
        mid = (low + high) // 2
        buffer = io.BytesIO()

        if format in ('jpg', 'jpeg'):
            img.save(buffer, 'JPEG', quality=mid, optimize=True)
        else:  # webp
            img.save(buffer, 'WEBP', quality=mid)

        size = buffer.tell()

        if size <= max_size_bytes:
            best_data = buffer.getvalue()
            best_quality = mid
            low = mid + 1  # Try higher quality
        else:
            high = mid - 1  # Try lower quality

    if best_data:
        with open(output_path, 'wb') as f:
            f.write(best_data)
        return (True, len(best_data), None)
    else:
        # Even minimum quality exceeds limit - save at minimum quality anyway
        buffer = io.BytesIO()
        if format in ('jpg', 'jpeg'):
            img.save(buffer, 'JPEG', quality=min_quality, optimize=True)
        else:
            img.save(buffer, 'WEBP', quality=min_quality)
        min_size = buffer.tell()

        # Save the file anyway
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())

        return (False, min_size,
                f"Saved at {min_size//1024}KB (limit: {max_size_bytes//1024}KB, quality: {min_quality}). "
                f"Enable resize to meet size limit.")


def _save_png_with_size_limit(image, output_path: str, max_size_bytes: int) -> Tuple[bool, int, Optional[str]]:
    """Try PNG with maximum compression. Saves file even if over limit."""
    buffer = io.BytesIO()
    image.save(buffer, 'PNG', optimize=True)
    size = buffer.tell()

    # Always save the file
    with open(output_path, 'wb') as f:
        f.write(buffer.getvalue())

    if size <= max_size_bytes:
        return (True, size, None)
    else:
        # File saved but over limit - return success=False to indicate limit not met
        return (False, size,
                f"PNG saved at {size//1024}KB (limit: {max_size_bytes//1024}KB). "
                f"PNG is lossless - enable resize or use JPG/WebP for smaller files.")


def _save_tiff_with_size_limit(image, output_path: str, max_size_bytes: int) -> Tuple[bool, int, Optional[str]]:
    """Try TIFF with LZW compression. Saves file even if over limit."""
    buffer = io.BytesIO()
    image.save(buffer, 'TIFF', compression='tiff_lzw')
    size = buffer.tell()

    # Always save the file
    with open(output_path, 'wb') as f:
        f.write(buffer.getvalue())

    if size <= max_size_bytes:
        return (True, size, None)
    else:
        return (False, size,
                f"TIFF saved at {size//1024}KB (limit: {max_size_bytes//1024}KB). "
                f"Enable resize or use JPG/WebP for smaller files.")


def _save_gif_with_size_limit(image, output_path: str, max_size_bytes: int) -> Tuple[bool, int, Optional[str]]:
    """Try GIF with palette optimization. Saves file even if over limit."""
    img = _prepare_for_gif(image)

    buffer = io.BytesIO()
    img.save(buffer, 'GIF')
    size = buffer.tell()

    # Always save the file
    with open(output_path, 'wb') as f:
        f.write(buffer.getvalue())

    if size <= max_size_bytes:
        return (True, size, None)
    else:
        return (False, size,
                f"GIF saved at {size//1024}KB (limit: {max_size_bytes//1024}KB). "
                f"Enable resize or use JPG/WebP for smaller files.")


def _save_pdf_with_size_limit(image, output_path: str, max_size_bytes: int,
                               initial_quality: int, min_quality: int) -> Tuple[bool, int, Optional[str]]:
    """Save PDF with JPEG compression, adjusting quality to meet size limit."""
    img = _prepare_for_jpeg(image)

    low, high = min_quality, initial_quality
    best_quality = None

    # Binary search for quality that meets PDF size limit
    while low <= high:
        mid = (low + high) // 2

        # Compress as JPEG
        jpeg_buffer = io.BytesIO()
        img.save(jpeg_buffer, 'JPEG', quality=mid, optimize=True)
        jpeg_buffer.seek(0)

        # Create PDF from JPEG
        compressed_img = Image.open(jpeg_buffer)
        pdf_buffer = io.BytesIO()
        compressed_img.save(pdf_buffer, 'PDF', resolution=300)
        pdf_size = pdf_buffer.tell()

        if pdf_size <= max_size_bytes:
            best_quality = mid
            low = mid + 1  # Try higher quality
        else:
            high = mid - 1  # Try lower quality

    if best_quality is not None:
        # Save with the best quality found
        jpeg_buffer = io.BytesIO()
        img.save(jpeg_buffer, 'JPEG', quality=best_quality, optimize=True)
        jpeg_buffer.seek(0)
        compressed_img = Image.open(jpeg_buffer)
        compressed_img.save(output_path, 'PDF', resolution=300)
        actual_size = os.path.getsize(output_path)
        return (True, actual_size, None)
    else:
        # Even minimum quality exceeds limit - save at minimum quality anyway
        jpeg_buffer = io.BytesIO()
        img.save(jpeg_buffer, 'JPEG', quality=min_quality, optimize=True)
        jpeg_buffer.seek(0)
        compressed_img = Image.open(jpeg_buffer)
        compressed_img.save(output_path, 'PDF', resolution=300)
        actual_size = os.path.getsize(output_path)
        return (False, actual_size,
                f"PDF saved at {actual_size//1024}KB (limit: {max_size_bytes//1024}KB, quality: {min_quality}). "
                f"Enable resize to meet size limit.")
