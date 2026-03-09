"""Generate a custom icon matching the in-app stacked layers icon."""
from PIL import Image, ImageDraw
import os


def hex_to_rgba(hex_color, alpha=255):
    """Convert hex color to RGBA tuple."""
    h = hex_color.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def create_icon():
    # Use Obsidian theme colors (the default)
    bg_primary = "#0a0a0c"
    accent = "#00ff88"        # front layer (brightest)
    accent_hover = "#00dd77"  # middle layer
    accent_dim = "#00aa55"    # back layer (dimmest)

    sizes = [256, 128, 64, 48, 32, 16]
    images = []

    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        s = size / 256  # scale factor

        # Background: rounded dark square
        pad = int(8 * s)
        bg_r = int(48 * s)
        draw.rounded_rectangle(
            [pad, pad, size - pad, size - pad],
            radius=bg_r,
            fill=hex_to_rgba(bg_primary)
        )

        # Subtle border
        draw.rounded_rectangle(
            [pad, pad, size - pad, size - pad],
            radius=bg_r,
            outline=hex_to_rgba(accent_dim, 60),
            width=max(1, int(2 * s))
        )

        # Three stacked rounded rectangles - matching the title bar icon layout
        # The in-app icon: back at (12,0), mid at (6,6), front at (0,12)
        # Scaled up for the icon with more visual impact

        rect_w = int(120 * s)
        rect_h = int(90 * s)
        rect_r = int(14 * s)

        # Center the stack in the icon
        base_x = int(50 * s)
        base_y = int(55 * s)

        layers = [
            # (offset_x, offset_y, color, alpha)
            (int(50 * s), int(0 * s),  accent_dim,   200),   # back - dimmest, offset right
            (int(25 * s), int(30 * s), accent_hover,  220),   # middle
            (int(0 * s),  int(60 * s), accent,        255),   # front - brightest, offset down
        ]

        for ox, oy, color, alpha in layers:
            x1 = base_x + ox
            y1 = base_y + oy
            x2 = x1 + rect_w
            y2 = y1 + rect_h

            # Draw shadow for depth
            if alpha == 255:  # front layer only
                shadow_offset = max(1, int(3 * s))
                draw.rounded_rectangle(
                    [x1 + shadow_offset, y1 + shadow_offset,
                     x2 + shadow_offset, y2 + shadow_offset],
                    radius=rect_r,
                    fill=(0, 0, 0, 60)
                )

            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=rect_r,
                fill=hex_to_rgba(color, alpha)
            )

            # Subtle inner highlight on each layer
            highlight_inset = max(1, int(4 * s))
            draw.rounded_rectangle(
                [x1 + highlight_inset, y1 + highlight_inset,
                 x2 - highlight_inset, y1 + highlight_inset + max(1, int(3 * s))],
                radius=max(1, int(2 * s)),
                fill=(255, 255, 255, 30)
            )

        images.append(img)

    # Save as .ico with all sizes
    out_path = os.path.join(os.path.dirname(__file__), "app_icon.ico")
    images[0].save(
        out_path,
        format='ICO',
        sizes=[(sz, sz) for sz in sizes],
        append_images=images[1:]
    )
    print(f"Icon saved to: {out_path}")
    return out_path


if __name__ == "__main__":
    create_icon()
