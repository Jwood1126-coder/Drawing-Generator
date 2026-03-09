"""
Batch Processor Module

Orchestrates the full pipeline for generating multiple part drawings.
Supports both legacy highlight-based detection and PDF form fields.
"""

import os
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
from tqdm import tqdm

from .pdf_converter import get_image_from_template
from .highlight_detector import RegionMapping, load_or_detect_regions
from .excel_reader import iterate_parts
from .text_replacer import replace_all_regions
from .form_field_reader import (
    has_form_fields,
    read_form_fields,
    render_pdf_with_fields_filled,
    convert_fields_to_regions
)


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string for use as a filename.

    Args:
        name: Original string

    Returns:
        Safe filename string
    """
    # Replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


def process_single_part(
    template_image: Image.Image,
    mapping: RegionMapping,
    part_number: str,
    data: dict,
    output_dir: Path,
    output_format: str = "png",
    font_path: Optional[str] = None,
    remove_labels: bool = False
) -> str:
    """
    Process a single part and save the output image.

    Args:
        template_image: Base template image
        mapping: Region mapping
        part_number: Part number for filename
        data: Data dictionary for this part
        output_dir: Output directory
        output_format: Image format (png, jpg, webp)
        font_path: Optional path to font file
        remove_labels: Whether to remove letter label markers (A, B, C, etc.)

    Returns:
        Path to saved file
    """
    # Generate the image
    result_image = replace_all_regions(
        template_image,
        mapping,
        data,
        font_path=font_path,
        remove_labels=remove_labels
    )

    # Save the image
    filename = f"{sanitize_filename(part_number)}.{output_format}"
    output_path = output_dir / filename

    # Configure save options based on format
    save_kwargs = {}
    if output_format == "png":
        save_kwargs["optimize"] = True
    elif output_format in ("jpg", "jpeg"):
        save_kwargs["quality"] = 95
        save_kwargs["optimize"] = True
        # Convert to RGB if necessary (JPEG doesn't support alpha)
        if result_image.mode in ('RGBA', 'P'):
            result_image = result_image.convert('RGB')
    elif output_format == "webp":
        save_kwargs["quality"] = 95
        save_kwargs["method"] = 6  # Best compression

    result_image.save(output_path, **save_kwargs)

    return str(output_path)


def process_single_part_formfields(
    template_path: str,
    part_number: str,
    data: dict,
    output_dir: Path,
    output_format: str = "png",
    dpi: int = 300
) -> str:
    """
    Process a single part using PDF form fields.

    Args:
        template_path: Path to template PDF with form fields
        part_number: Part number for filename
        data: Data dictionary for this part
        output_dir: Output directory
        output_format: Image format (png, jpg, webp)
        dpi: DPI for rendering

    Returns:
        Path to saved file
    """
    # Render PDF with filled form fields
    result_image = render_pdf_with_fields_filled(
        template_path,
        data,
        dpi=dpi
    )

    # Save the image
    filename = f"{sanitize_filename(part_number)}.{output_format}"
    output_path = output_dir / filename

    # Configure save options based on format
    save_kwargs = {}
    if output_format == "png":
        save_kwargs["optimize"] = True
    elif output_format in ("jpg", "jpeg"):
        save_kwargs["quality"] = 95
        save_kwargs["optimize"] = True
        # Convert to RGB if necessary (JPEG doesn't support alpha)
        if result_image.mode in ('RGBA', 'P'):
            result_image = result_image.convert('RGB')
    elif output_format == "webp":
        save_kwargs["quality"] = 95
        save_kwargs["method"] = 6  # Best compression

    result_image.save(output_path, **save_kwargs)

    return str(output_path)


def batch_process(
    template_path: str,
    excel_path: str,
    output_dir: str,
    mapping_path: Optional[str] = None,
    output_format: str = "png",
    font_path: Optional[str] = None,
    dpi: int = 300,
    parallel: bool = False,
    max_workers: int = 4,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    column_overrides: Optional[dict] = None,
    remove_labels: bool = False,
    use_form_fields: Optional[bool] = None
) -> dict:
    """
    Process all parts from an Excel file.

    Args:
        template_path: Path to template PDF or image
        excel_path: Path to Excel data file
        output_dir: Directory for output images
        mapping_path: Optional path to region mapping JSON
        output_format: Image format (png, jpg, webp)
        font_path: Optional path to font file
        dpi: DPI for PDF conversion
        parallel: Whether to use parallel processing
        max_workers: Number of parallel workers
        progress_callback: Optional callback(current, total, part_number)
        column_overrides: Manual mapping of column name patterns to labels
        remove_labels: Whether to remove letter label markers (A, B, C, etc.)
        use_form_fields: Whether to use PDF form fields (auto-detected if None)

    Returns:
        Dictionary with results:
        {
            "success_count": int,
            "error_count": int,
            "errors": [(part_number, error_message), ...],
            "output_files": [path, ...],
            "mode": "form_fields" or "legacy"
        }
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Check if template is a PDF with form fields
    is_pdf = template_path.lower().endswith('.pdf')
    has_fields = False

    if is_pdf and use_form_fields is not False:
        try:
            has_fields = has_form_fields(template_path)
            if has_fields:
                print(f"PDF form fields detected in: {template_path}")
        except Exception as e:
            print(f"Could not check for form fields: {e}")

    # Decide which mode to use
    use_formfields_mode = (use_form_fields is True) or (use_form_fields is None and has_fields)

    if use_formfields_mode and has_fields:
        return batch_process_formfields(
            template_path=template_path,
            excel_path=excel_path,
            output_dir=output_dir,
            output_format=output_format,
            dpi=dpi,
            parallel=parallel,
            max_workers=max_workers,
            progress_callback=progress_callback,
            column_overrides=column_overrides
        )

    # Legacy mode: Load template image
    print(f"Loading template: {template_path}")
    template_image = get_image_from_template(template_path, dpi=dpi)

    # Load or detect region mapping
    if mapping_path and Path(mapping_path).exists():
        print(f"Loading mapping: {mapping_path}")
        mapping = RegionMapping.load(mapping_path)
    else:
        print("Auto-detecting regions...")
        mapping = load_or_detect_regions(template_image)
        # Save for future use
        auto_mapping_path = output_path / "mapping.json"
        mapping.save(str(auto_mapping_path))
        print(f"Mapping saved to: {auto_mapping_path}")

    print(f"Found {len(mapping.regions)} regions: {', '.join(mapping.regions.keys())}")

    # Collect all parts
    parts = list(iterate_parts(excel_path, column_overrides=column_overrides))
    total = len(parts)
    print(f"Processing {total} parts...")

    results = {
        "success_count": 0,
        "error_count": 0,
        "errors": [],
        "output_files": [],
        "mode": "legacy"
    }

    if parallel and total > 1:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for part_number, data in parts:
                future = executor.submit(
                    process_single_part,
                    template_image,
                    mapping,
                    part_number,
                    data,
                    output_path,
                    output_format,
                    font_path,
                    remove_labels
                )
                futures[future] = part_number

            with tqdm(total=total, desc="Generating images") as pbar:
                for future in as_completed(futures):
                    part_number = futures[future]
                    try:
                        output_file = future.result()
                        results["success_count"] += 1
                        results["output_files"].append(output_file)
                    except Exception as e:
                        results["error_count"] += 1
                        results["errors"].append((part_number, str(e)))

                    pbar.update(1)
                    if progress_callback:
                        progress_callback(
                            results["success_count"] + results["error_count"],
                            total,
                            part_number
                        )
    else:
        # Sequential processing with progress bar
        with tqdm(parts, desc="Generating images") as pbar:
            for i, (part_number, data) in enumerate(pbar):
                pbar.set_postfix(part=part_number)
                try:
                    output_file = process_single_part(
                        template_image,
                        mapping,
                        part_number,
                        data,
                        output_path,
                        output_format,
                        font_path,
                        remove_labels
                    )
                    results["success_count"] += 1
                    results["output_files"].append(output_file)
                except Exception as e:
                    results["error_count"] += 1
                    results["errors"].append((part_number, str(e)))

                if progress_callback:
                    progress_callback(i + 1, total, part_number)

    # Print summary
    print(f"\nCompleted: {results['success_count']} successful, {results['error_count']} errors")

    if results["errors"]:
        print("\nErrors:")
        for part_number, error in results["errors"][:10]:  # Show first 10
            print(f"  {part_number}: {error}")
        if len(results["errors"]) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")

    return results


def batch_process_formfields(
    template_path: str,
    excel_path: str,
    output_dir: str,
    output_format: str = "png",
    dpi: int = 300,
    parallel: bool = False,
    max_workers: int = 4,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    column_overrides: Optional[dict] = None
) -> dict:
    """
    Process all parts from an Excel file using PDF form fields.

    Args:
        template_path: Path to template PDF with form fields
        excel_path: Path to Excel data file
        output_dir: Directory for output images
        output_format: Image format (png, jpg, webp)
        dpi: DPI for PDF rendering
        parallel: Whether to use parallel processing
        max_workers: Number of parallel workers
        progress_callback: Optional callback(current, total, part_number)
        column_overrides: Manual mapping of column name patterns to labels

    Returns:
        Dictionary with results
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get form field info
    fields = read_form_fields(template_path)
    field_names = list(fields.keys())
    print(f"Found {len(fields)} form fields: {', '.join(field_names)}")

    # Collect all parts
    parts = list(iterate_parts(excel_path, column_overrides=column_overrides))
    total = len(parts)
    print(f"Processing {total} parts using form fields...")

    results = {
        "success_count": 0,
        "error_count": 0,
        "errors": [],
        "output_files": [],
        "mode": "form_fields",
        "fields": field_names
    }

    if parallel and total > 1:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for part_number, data in parts:
                future = executor.submit(
                    process_single_part_formfields,
                    template_path,
                    part_number,
                    data,
                    output_path,
                    output_format,
                    dpi
                )
                futures[future] = part_number

            with tqdm(total=total, desc="Generating images") as pbar:
                for future in as_completed(futures):
                    part_number = futures[future]
                    try:
                        output_file = future.result()
                        results["success_count"] += 1
                        results["output_files"].append(output_file)
                    except Exception as e:
                        results["error_count"] += 1
                        results["errors"].append((part_number, str(e)))

                    pbar.update(1)
                    if progress_callback:
                        progress_callback(
                            results["success_count"] + results["error_count"],
                            total,
                            part_number
                        )
    else:
        # Sequential processing with progress bar
        with tqdm(parts, desc="Generating images") as pbar:
            for i, (part_number, data) in enumerate(pbar):
                pbar.set_postfix(part=part_number)
                try:
                    output_file = process_single_part_formfields(
                        template_path,
                        part_number,
                        data,
                        output_path,
                        output_format,
                        dpi
                    )
                    results["success_count"] += 1
                    results["output_files"].append(output_file)
                except Exception as e:
                    results["error_count"] += 1
                    results["errors"].append((part_number, str(e)))

                if progress_callback:
                    progress_callback(i + 1, total, part_number)

    # Print summary
    print(f"\nCompleted: {results['success_count']} successful, {results['error_count']} errors")

    if results["errors"]:
        print("\nErrors:")
        for part_number, error in results["errors"][:10]:  # Show first 10
            print(f"  {part_number}: {error}")
        if len(results["errors"]) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")

    return results
