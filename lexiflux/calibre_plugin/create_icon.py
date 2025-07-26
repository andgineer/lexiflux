"""Create a simple icon for the Calibre plugin."""

import os

from PIL import Image, ImageDraw


def create_plugin_icon():
    """Create a simple icon for the plugin."""
    # Create directory if it doesn't exist
    os.makedirs("images", exist_ok=True)

    # Create a 48x48 image with a blue gradient background
    size = 48
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    for y in range(size):
        color_value = int(100 + (155 * y / size))
        draw.rectangle([(0, y), (size, y + 1)], fill=(0, 100, color_value, 255))

    # Draw a simple upload arrow
    arrow_color = (255, 255, 255, 255)

    # Arrow shaft
    shaft_width = 4
    shaft_left = (size - shaft_width) // 2
    shaft_top = size // 3
    shaft_bottom = size * 2 // 3
    draw.rectangle(
        [shaft_left, shaft_top, shaft_left + shaft_width, shaft_bottom],
        fill=arrow_color,
    )

    # Arrow head
    arrow_size = 12
    arrow_top = size // 4
    arrow_points = [
        (size // 2, arrow_top),  # Top point
        (size // 2 - arrow_size // 2, arrow_top + arrow_size // 2),  # Left
        (size // 2 - arrow_size // 4, arrow_top + arrow_size // 2),  # Left inner
        (size // 2 - arrow_size // 4, shaft_top + 2),  # Left shaft connection
        (size // 2 + arrow_size // 4, shaft_top + 2),  # Right shaft connection
        (size // 2 + arrow_size // 4, arrow_top + arrow_size // 2),  # Right inner
        (size // 2 + arrow_size // 2, arrow_top + arrow_size // 2),  # Right
    ]
    draw.polygon(arrow_points, fill=arrow_color)

    # Save the icon
    img.save("images/icon.png", "PNG")
    print("Icon created at images/icon.png")


if __name__ == "__main__":
    create_plugin_icon()
