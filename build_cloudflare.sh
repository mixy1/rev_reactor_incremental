#!/bin/bash
# build_cloudflare.sh — Build static site for Cloudflare Pages deployment.
#
# Produces a flat dist/ directory with everything the site needs:
#   dist/
#     index.html, style.css, renderer.js, input.js, loader.js
#     manifest.json, mixy1.gif
#     assets/sprites/*.png
#     src/*.py, src/game/*.py, src/game/*.json
#     layout.json (optional)
#
# Cloudflare Pages config:
#   Build command: bash build_cloudflare.sh
#   Build output directory: dist

set -euo pipefail
cd "$(dirname "$0")"

DIST="dist"
SPRITES_SRC="decompilation/recovered/recovered_assets/sprites"
SPRITES_CANDY_SRC="decompilation/recovered/recovered_assets/sprites_decayed"
SRC_DIR="implementation/src"

echo "=== Building for Cloudflare Pages ==="

# Clean previous build
rm -rf "$DIST"
mkdir -p "$DIST/assets/sprites" "$DIST/src/game"

# 1. Copy web static files
echo "Copying web files..."
cp web/index.html "$DIST/"
cp web/style.css "$DIST/"
cp web/renderer.js "$DIST/"
cp web/input.js "$DIST/"
cp web/loader.js "$DIST/"
cp web/changelog.js "$DIST/"
# Generate changelog from git log (same format as old changelog.txt)
git log --format="%ad	%s" --date=format:"%Y-%m-%d %H:%M:%S" > "$DIST/changelog.txt"
cp web/mixy1.gif "$DIST/"

# 2. Patch index.html: change src-base to 'src/' for flat structure
echo "Patching src-base for production..."
sed -i 's|content="../implementation/src/"|content="src/"|' "$DIST/index.html"

# 3. Copy sprite assets and generate manifest
echo "Copying sprites..."
if [ -d "$SPRITES_SRC" ]; then
    cp "$SPRITES_SRC"/*.png "$DIST/assets/sprites/"
else
    echo "Warning: sprites not found at $SPRITES_SRC"
fi

# 3b. Copy candy sprite assets (if available)
if [ -d "$SPRITES_CANDY_SRC" ]; then
    echo "Copying candy sprites..."
    mkdir -p "$DIST/assets/sprites_decayed"
    cp "$SPRITES_CANDY_SRC"/*.png "$DIST/assets/sprites_decayed/"
    CANDY_COUNT=$(ls "$DIST/assets/sprites_decayed"/*.png 2>/dev/null | wc -l)
    echo "  $CANDY_COUNT candy sprites"
else
    echo "Note: Candy sprites not found (theme toggle will be inactive)"
fi

echo "Generating manifest.json..."
(cd "$DIST/assets/sprites" && ls *.png 2>/dev/null) | python3 -c "
import sys, json
names = [line.strip() for line in sys.stdin if line.strip()]
print(json.dumps(sorted(names), indent=2))
" > "$DIST/manifest.json"
SPRITE_COUNT=$(python3 -c "import json; print(len(json.load(open('$DIST/manifest.json'))))")
echo "  $SPRITE_COUNT sprites"

# 4. Copy Python source files
echo "Copying Python sources..."
for f in raylib_compat.py main.py assets.py; do
    cp "$SRC_DIR/$f" "$DIST/src/"
done
for f in __init__.py types.py store.py simulation.py catalog.py upgrades.py layout.py grid.py save.py ui.py; do
    cp "$SRC_DIR/game/$f" "$DIST/src/game/"
done

# 5. Copy data files
echo "Copying data files..."
for f in upgrade_data.json component_types.json stringliterals_web.json; do
    if [ -f "$SRC_DIR/game/$f" ]; then
        cp "$SRC_DIR/game/$f" "$DIST/src/game/"
    fi
done

# 6. Copy layout.json (optional)
if [ -f "implementation/layout.json" ]; then
    cp "implementation/layout.json" "$DIST/layout.json"
fi

# Summary
TOTAL=$(find "$DIST" -type f | wc -l)
echo ""
echo "Build complete: $TOTAL files in $DIST/"
echo "  Sprites: $SPRITE_COUNT"
echo "  Ready for Cloudflare Pages (output directory: dist)"
