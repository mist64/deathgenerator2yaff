#!/bin/bash
# Show all fonts grouped by pixel-size, rendering German text with umlauts

# German test sentence with umlauts
TEST_TEXT="Katzen mögen Fisch."

# Get all YAFF files and extract their pixel-size
for yaff in yaff/*.yaff; do
    if [ -f "$yaff" ]; then
        filename=$(basename "$yaff")
        # Extract pixel-size from the YAFF file
        pixel_size=$(grep "^pixel-size:" "$yaff" | head -1 | awk '{print $2}')
        if [ -n "$pixel_size" ]; then
            echo "${pixel_size}|${filename}|${yaff}"
        fi
    fi
done | sort -n | while IFS='|' read -r size filename filepath; do
    echo "----------------------------------------"
    echo "Size: ${size} - ${filename}"
    echo "----------------------------------------"

    # Try to render German text with monobit-banner
    if command -v monobit-banner &> /dev/null; then
        monobit-banner -f "$filepath" "$TEST_TEXT" 2>/dev/null | sed -e 's/@/█/g' 2>/dev/null || echo "[Could not render]"
    else
        echo "[monobit-banner not available]"
    fi

    echo ""
done
