#!/usr/bin/env python3
"""
Convert Death Generator JSON font definition + PNG sprite sheet to YAFF format.

Usage: python deathgenerator2yaff.py <game_dir> <output_dir>
Example: python deathgenerator2yaff.py games/win95 yaff
"""

import sys
import os
import json
import re
from PIL import Image
from collections import OrderedDict

# Font type detection overrides
# Map game name to forced font type ('monochrome_solid', 'outlined', 'shadowed',
# 'chromatic_outlined', 'chromatic_shadowed', 'antialiased', 'unknown')
FONT_TYPE_OVERRIDES = {
    # Fonts with detection issues - override to correct type
    # Note: 'antialiased' and 'unknown' keep all pixels without shadow/outline removal
    'sttngafu': 'chromatic_shadowed_bright',  # Light text on dark background, treat bright pixels as ink
    'mw': 'antialiased',  # Red text with black shadow - keep all pixels
    'nesticle': 'shadowed',  # Gray text with black shadow - remove shadow
    'ft2': 'chromatic_shadowed',  # White text with dark gray shadow - remove dark pixels
    'estsk': 'chromatic_bright',  # Tan text with dark brown outline - keep dark pixels, remove highlights
    'goldeneye007': 'antialiased',  # Gray text - shadow removal filters out everything
    'wof-red': 'chromatic_bright',  # Black text with red highlights - keep dark pixels, remove highlights
    'quake': 'shadowed',  # Grayscale text with dark shadow - remove dark pixels
    'psh': 'chromatic_shadowed_bright',  # Orange text with black shadow - bright pixels are text
    'scnes': 'chromatic_shadowed_bright',  # Brown text with black shadow - bright pixels are text
    'wof': 'chromatic_bright',  # INVERTED: Black pixels are text (no actual yellow in PNG)
    'ff8': 'chromatic_shadowed_bright',  # Light gray text with dark gray shadow - bright pixels are text
    'fft': 'antialiased',  # Brown text with dark brown shadow - both dark, keep all
    'karnovr': 'chromatic_bright',  # Black background with yellow highlights - inverted, keep dark
    'pokesnap': 'chromatic_shadowed_bright',  # White text with shadows - bright pixels are text
    'rr': 'chromatic_bright',  # Mid blue text - keep only brighter pixels
    'smrpg': 'chromatic_outlined',  # Beige text with dark outline - remove outline
    'swatkats': 'chromatic_outlined',  # Bright blue text with dark outline - remove dark outline
    'smurfs3': 'antialiased',  # White/gray anti-aliased text with black outline - keep all pixels
    'sth2i': 'antialiased',  # White outline with black fill - keep both
    'wea': 'chromatic_bright',  # INVERTED: Bright text on dark background
}

# Special character mappings for Windows codepage to Unicode
CP1252_TO_UNICODE = {
    145: 0x2018,  # LEFT SINGLE QUOTATION MARK
    146: 0x2019,  # RIGHT SINGLE QUOTATION MARK
    # Add more Windows-1252 specific mappings if needed
}

# Cache for game metadata from generators.js
_GAME_METADATA_CACHE = None

def load_game_metadata():
    """Load game metadata from js/generators.js"""
    global _GAME_METADATA_CACHE

    if _GAME_METADATA_CACHE is not None:
        return _GAME_METADATA_CACHE

    _GAME_METADATA_CACHE = {}

    try:
        generators_path = os.path.join(os.path.dirname(__file__), '..', 'js', 'generators.js')
        with open(generators_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse each game entry
        # Pattern: 'game_id':{ ... }
        game_pattern = r"'(\w+)':\s*\{([^}]+)\}"
        game_matches = re.findall(game_pattern, content, re.DOTALL)

        for game_id, game_block in game_matches:
            metadata = {}

            # Extract title
            title_match = re.search(r"'title':\s*'([^']+)'", game_block)
            if title_match:
                metadata['title'] = title_match.group(1)

            # Extract year
            year_match = re.search(r"'year':\s*(\d+)", game_block)
            if year_match:
                metadata['year'] = int(year_match.group(1))

            # Extract source (publisher/developer)
            source_match = re.search(r"'source':\s*'([^']+)'", game_block)
            if source_match:
                metadata['source'] = source_match.group(1)

            # Extract platform
            platform_match = re.search(r"'platform':\s*'([^']+)'", game_block)
            if platform_match:
                metadata['platform'] = platform_match.group(1)

            if metadata:
                _GAME_METADATA_CACHE[game_id] = metadata

    except Exception as e:
        print(f"Warning: Could not load game metadata from generators.js: {e}", file=sys.stderr)

    return _GAME_METADATA_CACHE

def get_unicode_codepoint(decimal_code):
    """Convert decimal character code to Unicode codepoint."""
    if decimal_code in CP1252_TO_UNICODE:
        return CP1252_TO_UNICODE[decimal_code]
    # For ASCII and Latin-1, the values are the same
    return decimal_code

def detect_spatial_pattern(image, x, y, w, h):
    """
    Analyze spatial distribution of bright vs dark pixels to distinguish:
    - Shadow: bright/dark pixels offset in one direction
    - Outline: bright pixels surround dark on all sides

    Returns: 'shadow', 'outline', or 'unknown'
    """
    # Convert to RGBA
    if image.mode != 'RGBA':
        img_rgba = image.convert('RGBA')
    else:
        img_rgba = image

    # Collect pixel positions by brightness
    bright_positions = []
    dark_positions = []

    for py in range(y, min(y + h, img_rgba.size[1])):
        for px in range(x, min(x + w, img_rgba.size[0])):
            try:
                r, g, b, a = img_rgba.getpixel((px, py))
                if a > 100:  # Opaque enough
                    brightness = max(r, g, b)
                    local_x = px - x
                    local_y = py - y

                    if brightness > 150:
                        bright_positions.append((local_x, local_y))
                    elif brightness < 100:
                        dark_positions.append((local_x, local_y))
            except:
                pass

    if not bright_positions or not dark_positions:
        return 'unknown'

    # Calculate average positions
    bright_avg_x = sum(x for x, y in bright_positions) / len(bright_positions)
    bright_avg_y = sum(y for x, y in bright_positions) / len(bright_positions)
    dark_avg_x = sum(x for x, y in dark_positions) / len(dark_positions)
    dark_avg_y = sum(y for x, y in dark_positions) / len(dark_positions)

    # Calculate offset vector
    offset_x = bright_avg_x - dark_avg_x
    offset_y = bright_avg_y - dark_avg_y
    offset_magnitude = (offset_x ** 2 + offset_y ** 2) ** 0.5

    # Check distribution on each side
    # Count pixels in each quadrant relative to center
    center_x = w / 2
    center_y = h / 2

    # For outline: bright pixels should be distributed around dark (on multiple sides)
    # For shadow: bright pixels should be consistently offset in one direction

    if offset_magnitude > 0.8:  # Clear directional offset
        return 'shadow'
    elif offset_magnitude < 0.3:  # Minimal offset, surrounds character
        return 'outline'
    else:
        return 'unknown'

def analyze_font_pattern(image, font_data, height):
    """
    Analyze font color pattern to detect: outlined, antialiased, shadowed, multi-color.
    Also detects if font is monospace (fixed-width).

    Returns: dict with 'type', 'is_monospace', and metrics
    """
    # Get default values
    defaults = font_data.get('default', {})
    default_y = defaults.get('y', 0)
    default_h = defaults.get('h', height)
    default_w = defaults.get('w', None)

    # Check if monospace and collect dimensions
    metadata_keys = {'height', 'origin', 'scale', 'wrap-width', 'dynamic-size', 'border',
                     'overlays', 'hooks', 'subfonts', 'notes', 'case-fold', 'null-character',
                     'default', 'explicit-origins', 'us-font-aliases', 'soviet-font-aliases'}

    widths = []
    heights = []
    is_monospace = False

    # Collect all widths and heights
    for key, value in font_data.items():
        if key not in metadata_keys and isinstance(value, dict):
            if 'w' in value:
                widths.append(value['w'])
            elif default_w is not None:
                widths.append(default_w)

            if 'h' in value:
                heights.append(value['h'])
            else:
                heights.append(default_h)

    # Determine monospace
    if default_w is not None:
        is_monospace = True
    elif widths and len(set(widths)) == 1:
        is_monospace = True

    # Calculate max dimensions
    max_width = max(widths) if widths else default_w if default_w else height
    max_height = max(heights) if heights else height

    # Find a sample character to analyze
    metadata_keys = {'height', 'origin', 'scale', 'wrap-width', 'dynamic-size', 'border',
                     'overlays', 'hooks', 'subfonts', 'notes', 'case-fold', 'null-character',
                     'default', 'explicit-origins', 'us-font-aliases', 'soviet-font-aliases'}

    sample_chars = ['65', '97', '48']  # A, a, 0
    char_data = None

    for char_code in sample_chars:
        if char_code in font_data and isinstance(font_data[char_code], dict) and 'x' in font_data[char_code]:
            char_data = font_data[char_code]
            break

    if not char_data:
        # Find any character
        for key, val in font_data.items():
            if key not in metadata_keys and isinstance(val, dict) and 'x' in val:
                char_data = val
                break

    if not char_data:
        return {
            'type': 'unknown',
            'skip': False,
            'is_monospace': is_monospace,
            'max_width': max_width,
            'max_height': max_height
        }

    # Get dimensions
    x = char_data['x']
    y = char_data.get('y', default_y)
    if 'w' in char_data:
        w = char_data['w']
    elif default_w is not None:
        w = default_w
    else:
        w = height
    h = char_data.get('h', default_h)

    # Convert to RGBA
    if image.mode != 'RGBA':
        img_rgba = image.convert('RGBA')
    else:
        img_rgba = image

    # Collect pixels
    pixels = []
    for py in range(y, min(y + h, img_rgba.size[1])):
        for px in range(x, min(x + w, img_rgba.size[0])):
            try:
                r, g, b, a = img_rgba.getpixel((px, py))
                if a > 10:  # Not fully transparent
                    pixels.append((r, g, b, a))
            except:
                pass

    if not pixels:
        return {'type': 'unknown', 'skip': False}

    # Analyze colors
    colors = set((r, g, b) for r, g, b, a in pixels)

    # Categorize pixels
    white_pixels = sum(1 for r, g, b, a in pixels if r > 200 and g > 200 and b > 200 and a > 200)
    black_pixels = sum(1 for r, g, b, a in pixels if r < 50 and g < 50 and b < 50 and a > 200)
    gray_pixels = sum(1 for r, g, b, a in pixels if 50 <= r <= 200 and 50 <= g <= 200 and 50 <= b <= 200 and abs(r-g) < 30 and abs(g-b) < 30 and a > 200)
    semi_transparent = sum(1 for r, g, b, a in pixels if 10 < a < 240)
    colored_pixels = len(pixels) - white_pixels - black_pixels - gray_pixels

    total = len(pixels)

    # Classification
    # Check if colors are actually chromatic (not just grayscale variations)
    chromatic_pixels = 0
    for r, g, b, a in pixels:
        if a > 200:
            # Check if this is a chromatic color (RGB channels differ significantly)
            max_diff = max(abs(r-g), abs(g-b), abs(r-b))
            if max_diff > 40:  # Significant color difference between channels
                chromatic_pixels += 1

    # Check if this is a single-hue font (chromatic outlined/shadowed)
    # All pixels should have the same dominant color channel
    if chromatic_pixels > total * 0.1:
        # Find dominant channel for each pixel
        dominant_channels = []
        for r, g, b, a in pixels:
            if a > 200:
                max_val = max(r, g, b)
                if max_val > 0:
                    if r == max_val:
                        dominant_channels.append('R')
                    elif g == max_val:
                        dominant_channels.append('G')
                    else:
                        dominant_channels.append('B')

        # If >80% have same dominant channel, it's single-hue
        if dominant_channels:
            from collections import Counter
            channel_counts = Counter(dominant_channels)
            most_common_channel, count = channel_counts.most_common(1)[0]

            if count / len(dominant_channels) > 0.8:
                # Single-hue chromatic font (e.g., red with dark red outline)
                # Treat like outlined/shadowed font

                # Find bright vs dark pixels
                bright_pixels = sum(1 for r, g, b, a in pixels if a > 200 and max(r, g, b) > 150)
                dark_pixels = sum(1 for r, g, b, a in pixels if a > 200 and max(r, g, b) <= 150)

                if bright_pixels > 0 and dark_pixels > 0:
                    dark_ratio = dark_pixels / total

                    # Use spatial analysis to distinguish shadow from outline
                    spatial_pattern = detect_spatial_pattern(image, x, y, w, h)

                    if spatial_pattern == 'shadow':
                        # Spatial analysis confirms shadow pattern
                        return {
                            'type': 'chromatic_shadowed',
                            'skip': False,
                            'dark_ratio': dark_ratio,
                            'remove_shadow': True,
                            'dominant_channel': most_common_channel,
                            'is_monospace': is_monospace,
                            'max_width': max_width,
                            'max_height': max_height
                        }
                    elif spatial_pattern == 'outline':
                        # Spatial analysis confirms outline pattern
                        return {
                            'type': 'chromatic_outlined',
                            'skip': False,
                            'bright_ratio': bright_pixels / total,
                            'dark_ratio': dark_ratio,
                            'remove_outline': True,
                            'dominant_channel': most_common_channel,
                            'is_monospace': is_monospace,
                            'max_width': max_width,
                            'max_height': max_height
                        }
                    else:
                        # Fallback to ratio-based heuristic if spatial is unclear
                        if dark_ratio < 0.3:
                            # Small amount of dark = shadow
                            return {
                                'type': 'chromatic_shadowed',
                                'skip': False,
                                'dark_ratio': dark_ratio,
                                'remove_shadow': True,
                                'dominant_channel': most_common_channel,
                                'is_monospace': is_monospace,
                                'max_width': max_width,
                                'max_height': max_height
                            }
                        else:
                            # Significant dark = outline
                            return {
                                'type': 'chromatic_outlined',
                                'skip': False,
                                'bright_ratio': bright_pixels / total,
                                'dark_ratio': dark_ratio,
                                'remove_outline': True,
                                'dominant_channel': most_common_channel,
                                'is_monospace': is_monospace,
                                'max_width': max_width,
                                'max_height': max_height
                            }

        # Multi-hue - truly multi-color, skip
        return {
            'type': 'multi_color',
            'skip': True,
            'unique_colors': len(colors),
            'is_monospace': is_monospace,
            'max_width': max_width,
            'max_height': max_height
        }

    # Outlined (white + black, both significant)
    if white_pixels > 0 and black_pixels > 0:
        white_ratio = white_pixels / total
        black_ratio = black_pixels / total
        if 0.2 < white_ratio and 0.2 < black_ratio:
            return {
                'type': 'outlined',
                'skip': False,
                'white_ratio': white_ratio,
                'black_ratio': black_ratio,
                'remove_outline': True,
                'is_monospace': is_monospace,
                'max_width': max_width,
                'max_height': max_height
            }

    # Shadowed (small amount of black + main color)
    if black_pixels > 0 and len(colors) >= 2:
        black_ratio = black_pixels / total
        if black_ratio < 0.3:
            return {
                'type': 'shadowed',
                'skip': False,
                'black_ratio': black_ratio,
                'remove_shadow': True,
                'is_monospace': is_monospace,
                'max_width': max_width,
                'max_height': max_height
            }

    # Antialiased (grayscale or semi-transparent)
    if semi_transparent > 0 or gray_pixels > total * 0.2:
        return {
            'type': 'antialiased',
            'skip': False,
            'is_monospace': is_monospace,
            'max_width': max_width,
            'max_height': max_height
        }

    # Monochrome solid
    if len(colors) == 1:
        return {
            'type': 'monochrome_solid',
            'skip': False,
            'is_monospace': is_monospace,
            'max_width': max_width,
            'max_height': max_height
        }

    return {
        'type': 'unknown',
        'skip': False,
        'is_monospace': is_monospace,
        'max_width': max_width,
        'max_height': max_height
    }

def extract_glyph_pixels(image, x, y, width, height, threshold=128, pattern=None):
    """
    Extract a glyph from the sprite sheet and convert to YAFF format.

    Returns a list of strings, each representing a row of pixels.
    '@' = inked pixel (opaque), '.' = uninked pixel (transparent/white)

    pattern: Optional dict with 'remove_outline' or 'remove_shadow' flags
    """
    if width == 0 or height == 0:
        return ["-"]  # Empty glyph notation

    # Convert to RGBA to handle all image modes consistently
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    rows = []
    for py in range(height):
        row = ""
        for px in range(width):
            pixel_x = x + px
            pixel_y = y + py

            # Get pixel in RGBA format
            try:
                r, g, b, a = image.getpixel((pixel_x, pixel_y))

                # Apply pattern-specific filtering
                is_inked = False

                if pattern and pattern.get('remove_outline'):
                    # For outlined fonts
                    if a > threshold:
                        if pattern['type'] == 'chromatic_outlined':
                            # Chromatic outlined: bright pixels are foreground, dark are outline
                            if max(r, g, b) > 150:
                                is_inked = True
                            else:
                                is_inked = False
                        else:
                            # White/black outlined: only white pixels are foreground
                            if r > 200 and g > 200 and b > 200:
                                is_inked = True
                            elif r < 50 and g < 50 and b < 50:
                                is_inked = False
                            else:
                                # Other colors, keep
                                is_inked = True

                elif pattern and pattern.get('remove_shadow'):
                    # For shadowed fonts
                    if a > threshold:
                        if pattern['type'] == 'chromatic_shadowed_bright':
                            # Chromatic shadowed (bright foreground variant): bright pixels are text
                            brightness = max(r, g, b)
                            if brightness > 150:
                                is_inked = True
                            else:
                                is_inked = False
                        elif pattern['type'] == 'chromatic_shadowed':
                            # Chromatic shadowed: Need to determine which is foreground
                            # Check dark_ratio: if high, dark is likely foreground
                            dark_ratio = pattern.get('dark_ratio', 0)
                            brightness = max(r, g, b)

                            if dark_ratio >= 0.4:
                                # High dark ratio: dark pixels are foreground (like khcom)
                                if brightness < 100:
                                    is_inked = True
                                else:
                                    is_inked = False
                            else:
                                # Low dark ratio: bright pixels are foreground
                                if brightness > 150:
                                    is_inked = True
                                else:
                                    is_inked = False
                        else:
                            # Grayscale shadowed: non-black = main glyph
                            if r < 50 and g < 50 and b < 50:
                                is_inked = False
                            else:
                                is_inked = True

                elif pattern and pattern['type'] == 'chromatic_bright':
                    # Chromatic bright: remove very bright pixels (highlights/shine)
                    # Keep mid-tone and darker pixels as the main text
                    # Note: "is_inked = True" means this pixel is PART OF the glyph (the text)
                    if a > threshold:
                        brightness = max(r, g, b)
                        if brightness > 180:
                            is_inked = False  # Very bright pixels are highlights (removed)
                        else:
                            is_inked = True  # Mid/dark pixels ARE the text

                else:
                    # Default: any opaque pixel is inked
                    if a > threshold:
                        is_inked = True

                row += "@" if is_inked else "."

            except:
                row += "."  # Default to uninked if error

        rows.append(row)

    return rows

def analyze_character_coverage(font_data):
    """
    Analyze which character ranges are present in the font.
    Returns list of labels to add to filename.
    """
    metadata_keys = {'height', 'origin', 'scale', 'wrap-width', 'dynamic-size', 'border',
                     'overlays', 'hooks', 'subfonts', 'notes', 'case-fold', 'null-character',
                     'default', 'explicit-origins', 'us-font-aliases', 'soviet-font-aliases'}

    # Collect all codepoints
    codepoints = set()
    for key, value in font_data.items():
        if key not in metadata_keys and isinstance(value, dict):
            try:
                decimal_code = int(key)
                unicode_code = get_unicode_codepoint(decimal_code)
                codepoints.add(unicode_code)
            except ValueError:
                continue

    if not codepoints:
        return []

    # Analyze character ranges
    has_uppercase = any(0x41 <= cp <= 0x5A for cp in codepoints)
    has_lowercase = any(0x61 <= cp <= 0x7A for cp in codepoints)
    ascii_count = sum(1 for cp in codepoints if 0x20 <= cp <= 0x7E)
    latin1_extended_count = sum(1 for cp in codepoints if 0xA0 <= cp <= 0xFF)
    latin_extended_count = sum(1 for cp in codepoints if 0x0100 <= cp <= 0x024F)
    cyrillic_count = sum(1 for cp in codepoints if 0x0400 <= cp <= 0x04FF)
    greek_count = sum(1 for cp in codepoints if 0x0370 <= cp <= 0x03FF)
    hiragana_count = sum(1 for cp in codepoints if 0x3040 <= cp <= 0x309F)
    katakana_count = sum(1 for cp in codepoints if 0x30A0 <= cp <= 0x30FF)
    kana_count = hiragana_count + katakana_count
    bopomofo_count = sum(1 for cp in codepoints if 0x3100 <= cp <= 0x312F)
    boxdraw_count = sum(1 for cp in codepoints if 0x2500 <= cp <= 0x257F)
    # Symbols: Mathematical Operators + Misc Technical + Arrows + Geometric Shapes
    symbols_count = sum(1 for cp in codepoints if
                       (0x2190 <= cp <= 0x21FF) or  # Arrows
                       (0x2200 <= cp <= 0x22FF) or  # Mathematical Operators
                       (0x2300 <= cp <= 0x23FF) or  # Miscellaneous Technical
                       (0x25A0 <= cp <= 0x25FF))    # Geometric Shapes

    # Determine labels
    labels = []

    # ASCII coverage first (90+ out of 95 printable ASCII chars)
    if ascii_count >= 90:
        labels.append('ascii')

    # Extended script labels
    if latin1_extended_count >= 20:
        labels.append('latin1')
    if latin_extended_count >= 20:
        labels.append('latinext')
    if cyrillic_count >= 10:
        labels.append('cyrillic')
    if greek_count >= 5:
        labels.append('greek')
    if kana_count >= 10:
        labels.append('kana')
    if bopomofo_count >= 10:
        labels.append('bopomofo')

    # Special character sets
    if boxdraw_count >= 20:
        labels.append('boxdraw')
    if symbols_count >= 10:
        labels.append('symbols')

    # Case label last
    if has_uppercase and not has_lowercase:
        labels.append('upper')

    return labels

def generate_font_section(image, font_data, font_name, height, pattern=None):
    """Generate YAFF glyph definitions for a single font."""
    yaff_lines = []

    # Collect character definitions (skip metadata keys)
    metadata_keys = {'height', 'origin', 'scale', 'wrap-width', 'dynamic-size', 'border',
                     'overlays', 'hooks', 'subfonts', 'notes', 'case-fold', 'null-character',
                     'default', 'explicit-origins', 'us-font-aliases', 'soviet-font-aliases'}

    # Get default values if present
    defaults = font_data.get('default', {})
    default_y = defaults.get('y', 0)
    default_h = defaults.get('h', height)
    default_w = defaults.get('w', None)  # Default width for fixed-width fonts

    chars = []
    for key, value in font_data.items():
        if key not in metadata_keys and isinstance(value, dict) and 'x' in value:
            try:
                decimal_code = int(key)
                chars.append((decimal_code, value))
            except ValueError:
                continue

    if not chars:
        return [], 0

    # Sort by character code
    chars.sort(key=lambda x: x[0])

    # Generate glyphs
    for decimal_code, char_data in chars:
        x = char_data['x']
        # Use character's y if specified, otherwise use default
        y = char_data.get('y', default_y)

        # Use character's w if specified, otherwise use default, fallback to height for square glyphs
        if 'w' in char_data:
            w = char_data['w']
        elif default_w is not None:
            w = default_w
        else:
            # Fallback for fonts with neither per-char nor default width
            w = height

        # Use character's h if specified, otherwise use default
        h = char_data.get('h', default_h)

        # Calculate shift-up for baseline alignment
        # shift-up is the distance from baseline to bottom of glyph
        # For characters shorter than font height, calculate the upward shift needed
        shift_up = None
        if h < height:
            # Character is shorter than font height - needs shift-up for baseline alignment
            shift_up = height - h

        # Get Unicode codepoint
        unicode_code = get_unicode_codepoint(decimal_code)

        # Generate labels
        yaff_lines.append(f"# Character: {chr(unicode_code) if 32 <= unicode_code <= 126 else f'U+{unicode_code:04X}'}")
        yaff_lines.append(f"u+{unicode_code:04x}:")

        # Extract and write glyph pixels (with pattern for outline/shadow removal)
        glyph_rows = extract_glyph_pixels(image, x, y, w, h, pattern=pattern)
        for row in glyph_rows:
            yaff_lines.append(f"    {row}")

        # Add per-glyph metrics if needed
        metrics_added = False
        if shift_up is not None:
            if not metrics_added:
                yaff_lines.append("")
                metrics_added = True
            yaff_lines.append(f"    shift-up: {shift_up}")

        if 'right-bearing' in char_data:
            if not metrics_added:
                yaff_lines.append("")
                metrics_added = True
            yaff_lines.append(f"    right-bearing: {char_data['right-bearing']}")

        yaff_lines.append("")

    return yaff_lines, len(chars)

def write_single_yaff(output_path, image, font_data, font_name, family_name, height, json_filename, png_filename, pattern=None, game_id=None):
    """Write a single YAFF file for one font."""
    yaff_lines = []

    # Load game metadata
    game_metadata_db = load_game_metadata()
    game_metadata = game_metadata_db.get(game_id, {}) if game_id else {}
    game_title = game_metadata.get('title', font_name)

    # Header
    yaff_lines.append("# YAFF font file")
    yaff_lines.append(f"# Converted from {json_filename} and {png_filename}")
    if game_metadata:
        yaff_lines.append(f"# Source game: {game_title}")
        if 'year' in game_metadata:
            yaff_lines.append(f"# Year: {game_metadata['year']}")
        if 'source' in game_metadata:
            yaff_lines.append(f"# Publisher: {game_metadata['source']}")
        if 'platform' in game_metadata:
            yaff_lines.append(f"# Platform: {game_metadata['platform']}")
    if pattern and pattern.get('type'):
        yaff_lines.append(f"# Font type: {pattern['type']}")
    yaff_lines.append("")

    # Global properties
    yaff_lines.append("yaff: 1.0")
    yaff_lines.append(f"name: {game_title}")
    yaff_lines.append(f"family: {family_name}")
    yaff_lines.append("encoding: unicode")
    if game_metadata.get('source'):
        yaff_lines.append(f"copyright: {game_metadata['source']}")
    yaff_lines.append("")

    # Metrics
    yaff_lines.append(f"# Global metrics")
    if height:
        yaff_lines.append(f"pixel-size: {height}")
    yaff_lines.append("")

    # Glyph definitions
    yaff_lines.append("# Glyph definitions")
    yaff_lines.append("")

    glyphs, char_count = generate_font_section(image, font_data, font_name, height, pattern)
    yaff_lines.extend(glyphs)

    # Write YAFF file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(yaff_lines))

    return char_count

def generate_yaff(json_path, png_path, output_dir):
    """Generate YAFF file(s) from JSON definition and PNG sprite sheet."""

    # Load JSON definition
    with open(json_path, 'r') as f:
        font_data = json.load(f, object_pairs_hook=OrderedDict)

    # Load PNG sprite sheet
    image = Image.open(png_path)

    # Extract metadata
    height = font_data.get('height', 13)

    # Determine base names from directory
    game_name = os.path.basename(os.path.dirname(json_path))
    base_font_name = game_name.replace('_', ' ').title()

    json_filename = os.path.basename(json_path)
    png_filename = os.path.basename(png_path)

    # Analyze main font pattern
    pattern = analyze_font_pattern(image, font_data, height)

    # Apply override if present
    if game_name in FONT_TYPE_OVERRIDES:
        override_type = FONT_TYPE_OVERRIDES[game_name]
        original_type = pattern['type']
        pattern['type'] = override_type
        # Set or clear shadow/outline removal flags based on override type
        if override_type in ['antialiased', 'unknown', 'chromatic_bright']:
            pattern['remove_shadow'] = False
            pattern['remove_outline'] = False
        elif override_type in ['shadowed', 'chromatic_shadowed', 'chromatic_shadowed_bright']:
            pattern['remove_shadow'] = True
            pattern['remove_outline'] = False
        elif override_type in ['outlined', 'chromatic_outlined']:
            pattern['remove_shadow'] = False
            pattern['remove_outline'] = True
        # Preserve other pattern data (monospace, dimensions, etc.)
        print(f"Font type override: {original_type} -> {override_type}")

    # Skip multi-color fonts
    if pattern.get('skip'):
        print(f"SKIPPED {game_name}: {pattern['type']} font (multi-color not supported)")
        return

    # Report detected pattern
    is_monospace = pattern.get('is_monospace', False)
    max_width = pattern.get('max_width', height)
    max_height = pattern.get('max_height', height)

    if pattern.get('type'):
        print(f"Detected: {pattern['type']} font", end='')
        if is_monospace:
            print(f" ({max_height}x{max_width})", end='')
        else:
            print(f" (max {max_height}px)", end='')
        if pattern.get('remove_outline'):
            if pattern['type'] == 'chromatic_outlined':
                ch = pattern.get('dominant_channel', '?')
                print(f" (removing dark {ch} outline, {int(pattern.get('dark_ratio', 0) * 100)}% dark)")
            else:
                print(" (removing black outline)")
        elif pattern.get('remove_shadow'):
            if pattern['type'] == 'chromatic_shadowed':
                ch = pattern.get('dominant_channel', '?')
                print(f" (removing dark {ch} shadow, {int(pattern.get('dark_ratio', 0) * 100)}% dark)")
            else:
                print(f" (removing shadow, {int(pattern.get('dark_ratio', pattern.get('black_ratio', 0)) * 100)}% black)")
        else:
            print()

    # Check if there are subfonts
    subfonts = font_data.get('subfonts', {})
    has_subfonts = len(subfonts) > 0

    generated_files = []
    total_chars = 0

    # Analyze character coverage for labeling
    coverage_labels = analyze_character_coverage(font_data)

    # Build label suffix from coverage
    label_suffix = ""
    if coverage_labels:
        label_suffix = "_" + "_".join(coverage_labels)

    # Determine filename suffix based on dimensions
    if is_monospace:
        # Monospace: heightxwidth format
        dim_suffix = f"_{max_height}x{max_width}"
    else:
        # Proportional: just max height
        dim_suffix = f"_{max_height}"

    # Process main font
    main_output = os.path.join(output_dir, f"{game_name}{label_suffix}{dim_suffix}.yaff")
    main_count = write_single_yaff(
        main_output, image, font_data,
        f"{base_font_name} Font", game_name, height,
        json_filename, png_filename, pattern, game_name
    )
    generated_files.append(main_output)
    total_chars += main_count
    print(f"Generated {os.path.basename(main_output)}: {main_count} characters")

    # Process subfonts if present - each gets its own file
    if has_subfonts:
        for subfont_name, subfont_data in subfonts.items():
            subfont_height = subfont_data.get('height', height)

            # Analyze subfont pattern (may differ from main font)
            subfont_pattern = analyze_font_pattern(image, subfont_data, subfont_height)

            # Apply override if present (use game-subfont key)
            subfont_key = f"{game_name}-{subfont_name}"
            if subfont_key in FONT_TYPE_OVERRIDES:
                override_type = FONT_TYPE_OVERRIDES[subfont_key]
                original_type = subfont_pattern['type']
                subfont_pattern['type'] = override_type
                # Clear shadow/outline removal flags for antialiased/unknown types
                if override_type in ['antialiased', 'unknown']:
                    subfont_pattern['remove_shadow'] = False
                    subfont_pattern['remove_outline'] = False
                print(f"Font type override ({subfont_name}): {original_type} -> {override_type}")

            # Skip multi-color subfonts
            if subfont_pattern.get('skip'):
                print(f"SKIPPED {game_name}-{subfont_name}: {subfont_pattern['type']} font (multi-color)")
                continue

            # Analyze character coverage for subfont
            subfont_coverage_labels = analyze_character_coverage(subfont_data)

            # Build label suffix from coverage
            subfont_label_suffix = ""
            if subfont_coverage_labels:
                subfont_label_suffix = "_" + "_".join(subfont_coverage_labels)

            # Determine suffix based on dimensions
            subfont_is_mono = subfont_pattern.get('is_monospace', False)
            subfont_max_width = subfont_pattern.get('max_width', subfont_height)
            subfont_max_height = subfont_pattern.get('max_height', subfont_height)

            if subfont_is_mono:
                subfont_dim_suffix = f"_{subfont_max_height}x{subfont_max_width}"
            else:
                subfont_dim_suffix = f"_{subfont_max_height}"

            subfont_output = os.path.join(output_dir, f"{game_name}-{subfont_name}{subfont_label_suffix}{subfont_dim_suffix}.yaff")

            subfont_count = write_single_yaff(
                subfont_output, image, subfont_data,
                f"{base_font_name} {subfont_name.title()}",
                f"{game_name}-{subfont_name}",
                subfont_height,
                json_filename, png_filename, subfont_pattern, game_name
            )

            generated_files.append(subfont_output)
            total_chars += subfont_count
            print(f"Generated {os.path.basename(subfont_output)}: {subfont_count} characters")

    print(f"\nTotal: {len(generated_files)} file(s), {total_chars} characters")

def main():
    if len(sys.argv) < 3:
        print("Usage: python deathgenerator2yaff.py <game_dir> <output_dir>")
        print("Example: python deathgenerator2yaff.py games/win95 yaff")
        sys.exit(1)

    game_dir = sys.argv[1]
    output_dir = sys.argv[2]
    game_name = os.path.basename(os.path.normpath(game_dir))

    json_path = os.path.join(game_dir, f"{game_name}.json")
    png_path = os.path.join(game_dir, f"{game_name}-font.png")

    # Check files exist
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        sys.exit(1)

    if not os.path.exists(png_path):
        print(f"Error: {png_path} not found")
        sys.exit(1)

    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)
    generate_yaff(json_path, png_path, output_dir)

if __name__ == '__main__':
    main()

# This code was written by Claude Code.