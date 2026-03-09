# Utility functions for Part Drawing Generator

import tkinter as tk


def sanitize_filename(name: str) -> str:
    """
    Remove or replace characters that are invalid in Windows/Unix filenames.

    Args:
        name: The filename to sanitize

    Returns:
        A sanitized filename safe for use on all platforms
    """
    # Characters invalid on Windows: < > : " / \ | ? *
    for c in '<>:"/\\|?*':
        name = name.replace(c, '_')
    return name.strip()


# Unicode symbols with ASCII fallbacks
UNICODE_SYMBOLS = {
    'section': ('◈', '*'),      # Section header icon
    'left': ('◀', '<'),         # Left arrow
    'right': ('▶', '>'),        # Right arrow
    'center': ('◆', '#'),       # Center alignment
    'bullet': ('●', '*'),       # Bullet point
    'arrow': ('→', '->'),       # Arrow
    'warning': ('⚠', '!'),      # Warning
}

_unicode_supported = None


def can_render_unicode() -> bool:
    """
    Check if the system can render unicode symbols.
    Result is cached after first check.
    """
    global _unicode_supported
    if _unicode_supported is not None:
        return _unicode_supported

    try:
        # Try to create a temporary label with unicode
        root = tk._default_root
        if root is None:
            # No Tk root yet, assume unicode works
            _unicode_supported = True
            return True

        test_label = tk.Label(root, text='◈◆◀▶')
        # If we get here without error, unicode likely works
        test_label.destroy()
        _unicode_supported = True
    except Exception:
        _unicode_supported = False

    return _unicode_supported


def get_symbol(name: str) -> str:
    """
    Get a symbol by name, with automatic fallback to ASCII if needed.

    Args:
        name: Symbol name (section, left, right, center, bullet, arrow, warning)

    Returns:
        Unicode symbol if supported, ASCII fallback otherwise
    """
    if name not in UNICODE_SYMBOLS:
        return name

    unicode_char, ascii_fallback = UNICODE_SYMBOLS[name]

    if can_render_unicode():
        return unicode_char
    return ascii_fallback
