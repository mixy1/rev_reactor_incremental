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

# Use an available Python interpreter without requiring uv.
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Error: python interpreter not found in PATH"
    exit 1
fi
echo "Using Python interpreter: $PYTHON_BIN"

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
echo -n "$(git rev-parse HEAD)" > "$DIST/version.txt"
cp web/mixy1.gif "$DIST/"

MIN_CHANGELOG_COMMITS=120
if git rev-parse --is-shallow-repository >/dev/null 2>&1; then
    IS_SHALLOW="$(git rev-parse --is-shallow-repository)"
else
    IS_SHALLOW="false"
fi

if [ "$IS_SHALLOW" = "true" ]; then
    CURRENT_COMMITS="$(git rev-list --count HEAD 2>/dev/null || echo 0)"
    if [ "${CURRENT_COMMITS:-0}" -lt "$MIN_CHANGELOG_COMMITS" ]; then
        DEEPEN_BY=$((MIN_CHANGELOG_COMMITS - CURRENT_COMMITS + 32))
        echo "Repository is shallow ($CURRENT_COMMITS commits); deepening history by $DEEPEN_BY..."
        if git fetch --deepen "$DEEPEN_BY" origin >/dev/null 2>&1; then
            UPDATED_COMMITS="$(git rev-list --count HEAD 2>/dev/null || echo "$CURRENT_COMMITS")"
            echo "  History deepened to $UPDATED_COMMITS commits"
        else
            echo "Warning: failed to deepen git history; changelog may be truncated"
        fi
    fi
fi

echo "Generating changelog.json from git log..."
"$PYTHON_BIN" -c '
import json
import subprocess

proc = subprocess.run(
    ["git", "log", "--max-count=300", "--pretty=format:%cI%x09%s"],
    capture_output=True,
    text=True,
    check=True,
)
entries = []
for line in proc.stdout.splitlines():
    if not line.strip():
        continue
    if "\t" in line:
        ts, message = line.split("\t", 1)
    else:
        ts, message = "", line.strip()
    entries.append({"ts": ts, "message": message})
print(json.dumps(entries, indent=2))
' > "$DIST/changelog.json"
CHANGELOG_COUNT=$("$PYTHON_BIN" -c "import json; print(len(json.load(open('$DIST/changelog.json'))))")
echo "  $CHANGELOG_COUNT changelog entries"

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
(
    shopt -s nullglob
    cd "$DIST/assets/sprites"
    for f in *.png; do
        printf '%s\n' "$f"
    done
) | "$PYTHON_BIN" -c "
import sys, json
names = [line.strip() for line in sys.stdin if line.strip()]
print(json.dumps(sorted(names), indent=2))
" > "$DIST/manifest.json"
SPRITE_COUNT=$("$PYTHON_BIN" -c "import json; print(len(json.load(open('$DIST/manifest.json'))))")
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
