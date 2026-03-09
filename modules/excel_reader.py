"""
Excel Data Reader Module

Reads Excel files and extracts data mapped to region labels.
"""

import re
from pathlib import Path
from typing import Dict, List, Iterator, Any, Optional

import pandas as pd


def extract_label_from_column(column_name: str) -> Optional[str]:
    """
    Extract the label (A, B, C, etc.) from a column header.

    Examples:
        "Part# (A)" -> "A"
        "Long Description (B)" -> "B"
        "Side 2 Drill (C)" -> "C"
        "Column Name" -> None (no label found)

    Args:
        column_name: The column header string

    Returns:
        The extracted label or None if no label pattern found
    """
    # Look for pattern like "(A)", "(B)", etc. at end of string
    match = re.search(r'\(([A-Za-z])\)\s*$', column_name)
    if match:
        return match.group(1).upper()

    # Also check for label patterns that may have been garbled by encoding issues
    # e.g., "Side 2 Drill ©" should map to "C" based on position
    # Look for any single letter in parentheses or special chars that might be labels
    match = re.search(r'[(\[{]([A-Za-z])[)\]}]\s*$', column_name)
    if match:
        return match.group(1).upper()

    return None


def create_column_override(excel_path: str, overrides: Dict[str, str]) -> None:
    """
    Apply manual column-to-label overrides for columns with encoding issues.

    Args:
        excel_path: Path to Excel file (for reference)
        overrides: Dict mapping column names (partial match) to labels
                   e.g., {"Side 2 Drill": "C"}
    """
    # This is a helper for cases where column names have encoding issues
    pass


def read_excel_data(
    excel_path: str,
    sheet_name: int | str = 0,
    column_overrides: Optional[Dict[str, str]] = None
) -> tuple[Dict[str, str], List[Dict[str, Any]]]:
    """
    Read Excel file and extract data with label mappings.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index (default: first sheet)
        column_overrides: Manual mapping of column name patterns to labels
                          e.g., {"Side 2 Drill": "C"} - matches columns containing this text

    Returns:
        Tuple of:
        - Column mapping: {label: column_name}
        - List of row data: [{label: value, ...}, ...]

    Raises:
        FileNotFoundError: If Excel file doesn't exist
        ValueError: If no valid label columns found
    """
    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Read Excel file - use dtype=str to preserve leading/trailing zeros
    df = pd.read_excel(excel_path, sheet_name=sheet_name, dtype=str)
    # Replace NaN with empty string
    df = df.fillna('')

    # Build column-to-label mapping
    column_mapping = {}  # label -> column_name
    for col in df.columns:
        label = extract_label_from_column(col)
        if label:
            column_mapping[label] = col

    # Apply manual overrides for columns with encoding issues
    if column_overrides:
        for pattern, label in column_overrides.items():
            for col in df.columns:
                if pattern.lower() in col.lower() and label not in column_mapping:
                    column_mapping[label] = col
                    break

    if not column_mapping:
        raise ValueError(
            "No valid label columns found in Excel file.\n"
            "Column headers should include labels like: 'Part# (A)', 'Description (B)', etc."
        )

    # Convert each row to a label-value dictionary
    # Since we read with dtype=str, values are already strings preserving leading/trailing zeros
    rows = []
    for _, row in df.iterrows():
        row_data = {}
        for label, col_name in column_mapping.items():
            value = row[col_name]
            # Value is already a string from dtype=str, just use it directly
            row_data[label] = str(value) if value else ""
        rows.append(row_data)

    return column_mapping, rows


def iterate_parts(
    excel_path: str,
    sheet_name: int | str = 0,
    part_number_label: str = "A",
    column_overrides: Optional[Dict[str, str]] = None
) -> Iterator[tuple[str, Dict[str, str]]]:
    """
    Iterate through Excel rows, yielding (part_number, data) tuples.

    This is a convenience generator for batch processing.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index
        part_number_label: Label for the part number column (default: "A")
        column_overrides: Manual mapping of column name patterns to labels

    Yields:
        Tuples of (part_number, row_data_dict)
    """
    _, rows = read_excel_data(excel_path, sheet_name, column_overrides)

    for row_data in rows:
        part_number = row_data.get(part_number_label, "UNKNOWN")
        yield part_number, row_data


def get_column_info(excel_path: str, sheet_name: int | str = 0) -> None:
    """
    Print column information for debugging/setup.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name, dtype=str)

    print(f"\nExcel file: {excel_path}")
    print(f"Total rows: {len(df)}")
    print(f"\nColumns found:")

    for col in df.columns:
        label = extract_label_from_column(col)
        sample = df[col].iloc[0] if len(df) > 0 else "N/A"
        label_str = f"[{label}]" if label else "[no label]"
        print(f"  {label_str:10} {col}")
        print(f"            Sample: {sample}")
