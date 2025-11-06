#!/usr/bin/env python3
"""
Generate a PNG showcasing all YAFF fonts with demo text in an ultra-compact layout.
"""

import os
import subprocess
import sys
from PIL import Image, ImageDraw

def get_demo_text_for_font(font_name):
    """Get appropriate demo text based on font's character coverage."""
    name_lower = font_name.lower()

    # Build demo text by combining sections based on character coverage
    sections = []

    # Check for ASCII coverage (always show if present, or if uppercase-only)
    has_ascii = 'ascii' in name_lower or 'latin' in name_lower
    is_uppercase = '_upper_' in name_lower or name_lower.endswith('_upper')

    # Start with ASCII section if present
    if has_ascii or is_uppercase:
        if is_uppercase:
            sections.append("THE QUICK BROWN FOX")
        else:
            sections.append("Quick Brown Fox")

    # Add Latin-1 section (4 characters with diacritics)
    if 'latin1' in name_lower and not is_uppercase:
        sections.append("ñäéö")

    # Add Latin Extended section (4 characters)
    if 'latinext' in name_lower:
        sections.append("ŁŚŻš")

    # Add Cyrillic section (4 characters)
    if 'cyrillic' in name_lower:
        if is_uppercase:
            sections.append("БЫАГ")
        else:
            sections.append("быаг")

    # Add Greek section (4 characters)
    if 'greek' in name_lower:
        sections.append("Γαβδ")

    # Add Kana section (4 characters)
    if 'kana' in name_lower or name_lower.startswith('mm2_kana'):
        sections.append("いろは")

    # Add Bopomofo section (4 characters)
    if 'bopomofo' in name_lower:
        sections.append("ㄅㄆㄇㄈ")

    # Add Box Drawing section (4 characters)
    if 'boxdraw' in name_lower:
        sections.append("┌┬┐│")

    # Add Symbols section (4 characters)
    if 'symbols' in name_lower or 'symbol' in name_lower:
        sections.append("→★♦♠")

    # If we built sections, join them with " | "
    if sections:
        return " | ".join(sections)

    # Fallback for fonts with no recognized coverage labels
    if is_uppercase:
        return "THE QUICK BROWN FOX"
    return "Quick Brown Fox"

def render_font_with_monobit(yaff_path, text):
    """Use monobit-banner to render text with a font."""
    try:
        result = subprocess.run(
            ['monobit-banner', '-f', yaff_path, text],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception as e:
        return None

def ascii_to_image(ascii_text, font_name):
    """Convert ASCII art to PIL Image with ultra-thin spacing."""
    if not ascii_text or not ascii_text.strip():
        return None

    lines = ascii_text.rstrip('\n').split('\n')
    if not lines:
        return None

    # Calculate dimensions (1 pixel per character, ultra compact)
    height = len(lines)
    width = max(len(line) for line in lines) if lines else 0

    if width == 0 or height == 0:
        return None

    # Create image: white background
    img = Image.new('RGB', (width, height), 'white')
    pixels = img.load()

    # Draw pixels (black for █ or @, white for spaces/dots)
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char in ('█', '@', '#', '*'):
                pixels[x, y] = (0, 0, 0)  # Black

    return img

def find_smallest_variable_font(yaff_dir):
    return os.path.join(yaff_dir, 'hso_ascii_7.yaff')

def get_alphabet_width(yaff_path):
    """Calculate the width of rendering 'The Quick Brown Fox' with this font."""
    name = os.path.basename(yaff_path).replace('.yaff', '')
    name_lower = name.lower()
    is_uppercase = '_upper_' in name_lower or name_lower.endswith('_upper')

    if is_uppercase:
        text_to_measure = "THE QUICK BROWN FOX"
    else:
        text_to_measure = "Quick Brown Fox"

    ascii_art = render_font_with_monobit(yaff_path, text_to_measure)
    if ascii_art:
        lines = ascii_art.rstrip('\n').split('\n')
        if lines:
            return max(len(line) for line in lines)
    return 0

def extract_font_info(yaff_path):
    """Extract font height, whether it's monospace, and alphabet width from YAFF file."""
    try:
        # Parse filename FIRST (this is the canonical size)
        name = os.path.basename(yaff_path).replace('.yaff', '')
        parts = name.split('_')
        height = None

        for part in reversed(parts):
            # Look for patterns like "16x8" or just "16"
            if 'x' in part:
                try:
                    height = int(part.split('x')[0])
                    break
                except:
                    pass
            elif part.isdigit():
                height = int(part)
                break

        # Only use pixel-size from file as fallback if filename parsing failed
        if height is None:
            with open(yaff_path, 'r', encoding='utf-8') as f:
                content = f.read(2000)

            for line in content.split('\n'):
                if line.startswith('pixel-size:'):
                    try:
                        height = int(line.split(':')[1].strip())
                        break
                    except:
                        pass

        if height is None:
            height = 13  # Default fallback

        # Check if monospace - look for width in filename
        name_lower = name.lower()
        is_monospace = 'x' in name_lower.split('_')[-1]  # e.g., "8x8"

        # Get alphabet width for sorting
        alphabet_width = get_alphabet_width(yaff_path)

        return height, is_monospace, alphabet_width
    except:
        return 13, False, 0

def create_font_showcase(yaff_dir, output_path, custom_demo_text=None):
    """Create a PNG showcasing all fonts with two-column layout."""
    yaff_files = [f for f in os.listdir(yaff_dir) if f.endswith('.yaff')]

    if not yaff_files:
        print("No YAFF files found!")
        return

    print(f"Found {len(yaff_files)} fonts")

    # Categorize and sort fonts
    print("Categorizing fonts and measuring alphabet widths...")
    font_info = []
    for yaff_file in yaff_files:
        yaff_path = os.path.join(yaff_dir, yaff_file)
        height, is_monospace, alphabet_width = extract_font_info(yaff_path)
        font_info.append((yaff_file, height, is_monospace, alphabet_width))
        print(f"  {yaff_file}: height={height}, mono={is_monospace}, width={alphabet_width}")

    # Sort: variable width first (is_monospace=False), then by alphabet width, then by name
    font_info.sort(key=lambda x: (x[2], x[3], x[0]))
    yaff_files = [f[0] for f in font_info]

    print(f"Sorted: variable-width fonts first, then monospace, by alphabet width")

    # Find label font
    label_font_path = find_smallest_variable_font(yaff_dir)
    print(f"Using label font: {os.path.basename(label_font_path)}")

    font_images = []
    label_images = []
    max_label_width = 0
    max_font_width = 0

    for yaff_file in yaff_files:
        yaff_path = os.path.join(yaff_dir, yaff_file)
        font_name = yaff_file.replace('.yaff', '')

        # Render font name label with small font
        label_ascii = render_font_with_monobit(label_font_path, font_name)
        if label_ascii:
            label_img = ascii_to_image(label_ascii, font_name)
        else:
            label_img = None

        # Get appropriate demo text for this font
        if custom_demo_text:
            demo_text = custom_demo_text
        else:
            demo_text = get_demo_text_for_font(font_name)

        # Render with monobit
        ascii_art = render_font_with_monobit(yaff_path, demo_text)

        if ascii_art:
            # Convert to image
            font_img = ascii_to_image(ascii_art, font_name)
            if font_img:
                font_images.append((font_name, font_img))
                label_images.append(label_img)
                if label_img:
                    max_label_width = max(max_label_width, label_img.width)
                max_font_width = max(max_font_width, font_img.width)
                print(f"✓ {font_name}: {font_img.width}x{font_img.height}")
            else:
                print(f"✗ {font_name}: Failed to convert ASCII")
        else:
            print(f"✗ {font_name}: Failed to render")

    if not font_images:
        print("No fonts could be rendered!")
        return

    print(f"\nCreating two-column showcase with {len(font_images)} fonts...")

    # Add spacing between columns
    column_spacing = 4
    label_col_width = 200

    # Calculate dimensions
    total_width = label_col_width + column_spacing + max_font_width

    # Calculate total height (use max of label and font height for each row, 1px spacing)
    row_heights = []
    for i, (font_name, font_img) in enumerate(font_images):
        label_img = label_images[i]
        label_height = label_img.height if label_img else 0
        row_height = max(font_img.height, label_height)
        row_heights.append(row_height)

    total_height = sum(row_heights) + len(row_heights)  # +1px spacing per row

    # Create final image
    showcase = Image.new('RGB', (total_width, total_height), 'white')

    # Paste each font with its label
    y_offset = 0
    for i, (font_name, font_img) in enumerate(font_images):
        label_img = label_images[i]
        row_height = row_heights[i]

        # Paste label (vertically centered in row)
        if label_img:
            if label_img.width > label_col_width:
                label_img = label_img.crop((0, 0, label_col_width, label_img.height))
            label_y = y_offset + (row_height - label_img.height) // 2
            showcase.paste(label_img, (0, label_y))

        # Paste font sample (vertically centered in row)
        font_y = y_offset + (row_height - font_img.height) // 2
        showcase.paste(font_img, (label_col_width + column_spacing, font_y))

        y_offset += row_height + 1

    # Save
    showcase.save(output_path)
    print(f"\n✓ Saved to {output_path}")
    print(f"  Dimensions: {showcase.width}x{showcase.height}")
    print(f"  Fonts: {len(font_images)}")

def main():
    yaff_dir = 'yaff'
    output_path = 'font_showcase.png'
    custom_demo_text = None

    if len(sys.argv) > 1:
        custom_demo_text = ' '.join(sys.argv[1:])

    if not os.path.exists(yaff_dir):
        print(f"Error: {yaff_dir} directory not found!")
        sys.exit(1)

    create_font_showcase(yaff_dir, output_path, custom_demo_text)

if __name__ == '__main__':
    main()
