#!/usr/bin/env python3
"""Split a candy-themed sprite sheet back into individual sprite files.

Reads:
  sprites_sheet_map.json        — cell positions and original dimensions
  <input sheet>                 — the candy-themed sprite sheet (CLI arg or default)

Outputs:
  decompilation/recovered/recovered_assets/sprites_candy/*.png
  — Component sprites from the sheet, plus UI sprites copied from originals.

Usage:
  python split_sprite_sheet.py [candy_sheet.png]
"""

import json
import os
import shutil
import sys
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SPRITE_DIR = PROJECT_ROOT / "decompilation" / "recovered" / "recovered_assets" / "sprites"
CANDY_DIR = PROJECT_ROOT / "decompilation" / "recovered" / "recovered_assets" / "sprites_candy"
MAP_PATH = SCRIPT_DIR / "sprites_sheet_map.json"

CELL = 32


def main():
    # Determine input sheet
    if len(sys.argv) > 1:
        sheet_path = Path(sys.argv[1])
    else:
        sheet_path = SCRIPT_DIR / "sprites_candy_sheet.png"

    if not sheet_path.exists():
        print(f"Error: Sheet not found at {sheet_path}")
        print("Usage: python split_sprite_sheet.py <candy_sheet.png>")
        sys.exit(1)

    if not MAP_PATH.exists():
        print(f"Error: Sheet map not found at {MAP_PATH}")
        print("Run make_sprite_sheet.py first.")
        sys.exit(1)

    with open(MAP_PATH) as f:
        sheet_map = json.load(f)

    sheet = Image.open(sheet_path).convert("RGBA")
    print(f"Input sheet: {sheet_path} ({sheet.width}x{sheet.height})")

    # Create output directory
    CANDY_DIR.mkdir(parents=True, exist_ok=True)

    # Split component sprites from the sheet
    split_count = 0
    for name, info in sheet_map.items():
        col, row = info["col"], info["row"]
        orig_w, orig_h = info["orig_w"], info["orig_h"]

        # Crop the cell
        cx = col * CELL
        cy = row * CELL
        cell = sheet.crop((cx, cy, cx + CELL, cy + CELL))

        # Extract centered region at original dimensions
        ox = (CELL - orig_w) // 2
        oy = (CELL - orig_h) // 2
        sprite = cell.crop((ox, oy, ox + orig_w, oy + orig_h))

        sprite.save(CANDY_DIR / name)
        split_count += 1

    print(f"Split {split_count} component sprites from sheet")

    # Copy all non-component sprites (UI, buttons, etc.) from originals
    copy_count = 0
    for f in sorted(os.listdir(SPRITE_DIR)):
        if not f.endswith(".png"):
            continue
        if f not in sheet_map and not (CANDY_DIR / f).exists():
            shutil.copy2(SPRITE_DIR / f, CANDY_DIR / f)
            copy_count += 1

    print(f"Copied {copy_count} UI sprites from originals")
    print(f"Total sprites in {CANDY_DIR.name}/: {len(list(CANDY_DIR.glob('*.png')))}")

    # Verify all original sprites are present
    originals = set(f for f in os.listdir(SPRITE_DIR) if f.endswith(".png"))
    candy = set(f for f in os.listdir(CANDY_DIR) if f.endswith(".png"))
    missing = originals - candy
    if missing:
        print(f"WARNING: {len(missing)} sprites missing: {sorted(missing)[:10]}")
    else:
        print("All sprites accounted for.")


if __name__ == "__main__":
    main()
