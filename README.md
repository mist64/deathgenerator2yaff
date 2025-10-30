# Death Generator to YAFF Converter

Convert [Death Generator](https://deathgenerator.com) pixel fonts from JSON+PNG format to [YAFF (Yet Another Font Format)](https://github.com/robhagemans/monobit/blob/master/doc/YAFF.md) format.

## Overview

This tool converts pixel fonts from the Death Generator project into the human-readable and well-documented YAFF format. Some Death Generator fonts are multi-color or contain outlines and shadows, so this tool tries to reconstruct the core bitmap font. For some fonts, it has hard-coded hints how to convert them.

**Pre-converted fonts included**: This repository includes 290 pre-converted YAFF files in the `yaff/` directory, converted from the Death Generator source repository at commit `8c12133` (2024-10-30).

## Features

- **Automatic font type detection**: Identifies monochrome solid, outlined, shadowed, chromatic (multi-color) fonts
- **Character coverage analysis**: Automatically labels fonts with character range support (ASCII, Latin-1, Cyrillic, Greek, Japanese, etc.)
- **Dimension-based naming**: Generates descriptive filenames based on font height/width and character coverage
- **Metadata integration**: Includes game title, source, year, and platform information from the Death Generator registry

## Requirements

- Python 3.7+
- Pillow (for image processing)
- monobit (for YAFF output validation, optional)

## Installation

```bash
# Clone the repository
git clone https://github.com/mist64/deathgenerator2yaff.git
cd deathgenerator2yaff

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Convert a single game

```bash
python deathgenerator2yaff.py <game_dir> <output_dir>
```

Example:
```bash
python deathgenerator2yaff.py ~/SierraDeathGenerator/games/win95 yaff/
```

This will process the game in `games/win95/` and generate YAFF files in the `yaff/` directory.

### Convert all games

```bash
python convert_all.py <input_dir> <output_dir>
```

Example:
```bash
python convert_all.py ~/SierraDeathGenerator/games yaff/
```

This will process all games in the `games/` directory and generate YAFF files in `yaff/`.

### View the generated fonts

You can use `monobit-banner` from the [monobit](https://github.com/robhagemans/monobit) package to display the generated YAFF fonts:

```bash
# Install monobit
pip install monobit

# Display text using a font
monobit-banner -f yaff/win95_ascii_latin1_13.yaff "Hello World"

# Example with character substitution for better visibility
monobit-banner -f yaff/goldeneye007_ascii_15.yaff "MISSION COMPLETE" | sed -e 's/@/█/g'
```

## Output Format

YAFF files are named using this pattern:
```
{game}[-{subfont}][_coverage_labels]_{height}[x{width}].yaff
```

Examples:
- `win95_ascii_16.yaff` - Windows 95 font, ASCII coverage, 16px height, proportional
- `goldeneye007_ascii_15.yaff` - GoldenEye 007 font, 15px monospace
- `wargroove_ascii_latin1_latinext_cyrillic_greek_kana_14.yaff` - Wargroove with extensive Unicode support

### Coverage Labels

Fonts are automatically labeled based on character coverage:
- `_ascii` - 90+ printable ASCII characters (U+0020 to U+007E)
- `_latin1` - 20+ Latin-1 Extended characters (U+00A0 to U+00FF)
- `_latinext` - 10+ Latin Extended A/B characters (U+0100 to U+024F)
- `_cyrillic` - 10+ Cyrillic characters (U+0400 to U+04FF)
- `_greek` - 5+ Greek characters (U+0370 to U+03FF)
- `_kana` - 10+ Hiragana or Katakana characters
- `_bopomofo` - 5+ Bopomofo characters (U+3100 to U+312F)
- `_boxdraw` - 5+ Box Drawing characters (U+2500 to U+257F)
- `_symbols` - 10+ various symbol ranges
- `_upper` - Uppercase-only fonts (no lowercase)

## Credits

- Death Generator fonts extracted from classic video games
- Converter tool created for the [Death Generator](https://deathgenerator.com) project
- YAFF format by [monobit](https://github.com/robhagemans/monobit)

## License

This converter tool is dedicated to the Public Domain under the CC0 1.0 Universal license.

**Note on font data**: The converted YAFF fonts in the `yaff/` directory are derived from the Death Generator project. The original font images are copyright their respective game publishers and are used under fair use. The YAFF conversions are provided for educational and preservation purposes. Please respect the original copyright holders.
