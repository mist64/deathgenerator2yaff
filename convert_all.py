#!/usr/bin/env python3
"""Convert all games to YAFF format."""

import os
import subprocess
import sys

def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_all.py <input_dir> <output_dir>")
        print("Example: python convert_all.py games yaff")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    script_path = 'deathgenerator2yaff.py'
    python_path = sys.executable  # Use current Python interpreter

    # Get all game directories
    game_dirs = []
    for item in sorted(os.listdir(input_dir)):
        game_path = os.path.join(input_dir, item)
        if os.path.isdir(game_path):
            json_file = os.path.join(game_path, f"{item}.json")
            if os.path.exists(json_file):
                game_dirs.append(game_path)

    print(f"Found {len(game_dirs)} games to convert\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for game_dir in game_dirs:
        game_name = os.path.basename(game_dir)
        print(f"Processing {game_name}...")

        try:
            result = subprocess.run(
                [python_path, script_path, game_dir, output_dir],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Count generated and skipped files
                output = result.stdout
                if 'Generated' in output:
                    success_count += 1
                    print(f"  ✓ {game_name}")
                if 'SKIPPED' in output:
                    skip_count += output.count('SKIPPED')
            else:
                error_count += 1
                print(f"  ✗ {game_name}: {result.stderr.strip()}")

        except subprocess.TimeoutExpired:
            error_count += 1
            print(f"  ✗ {game_name}: Timeout")
        except Exception as e:
            error_count += 1
            print(f"  ✗ {game_name}: {str(e)}")

    print(f"\nConversion complete!")
    print(f"  Success: {success_count} games")
    print(f"  Skipped fonts: {skip_count}")
    print(f"  Errors: {error_count}")

if __name__ == '__main__':
    main()
