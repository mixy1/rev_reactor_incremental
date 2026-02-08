#!/usr/bin/env python3
"""Assemble component sprites into a reference sprite sheet for candy theme generation.

Outputs:
  sprites_reference_sheet.png           — clean sheet (for splitting later)
  sprites_reference_sheet_annotated.png — with gridlines + labels (for Gemini)
  sprites_sheet_map.json                — maps filename -> {col, row, orig_w, orig_h}
"""

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SPRITE_DIR = Path(__file__).resolve().parent.parent / "decompilation" / "recovered" / "recovered_assets" / "sprites"
OUT_DIR = Path(__file__).resolve().parent.parent / "scripts"

CELL = 32
COLS = 16

# UI sprites to skip — these don't get candy-themed
UI_SPRITES = {
    "AltGrid.png", "BarBackground.png", "Block.png", "GenericTile.png",
    "GridBacker.png", "GridFrame.png", "GridTile.png", "InputFieldBackground.png",
    "MainGrid.png", "MainUpgrades.png", "Pixel.png", "SideGrid.png", "TopBanner.png",
    # Buttons
    "ButtonBACK.png", "ButtonBACKClicked.png", "ButtonBACKHover.png",
    "ButtonBIG.png", "ButtonBIGClicked.png", "ButtonBIGHover.png",
    "ButtonMED.png", "ButtonMEDClicked.png", "ButtonMEDHover.png",
    "ButtonNOREPLACE.png", "ButtonNOREPLACEClicked.png", "ButtonNOREPLACEHover.png",
    "ButtonPAUSE.png", "ButtonPAUSEClicked.png", "ButtonPAUSEHover.png",
    "ButtonPLAY.png", "ButtonPLAYClicked.png", "ButtonPLAYHover.png",
    "ButtonREPLACE.png", "ButtonREPLACEClicked.png", "ButtonREPLACEHover.png",
    "ButtonSMALL.png", "ButtonSMALLClicked.png", "ButtonSMALLHover.png",
    "IconButton.png", "IconButtonLocked.png", "IconClickedButton.png", "IconHoverButton.png",
    # Tab buttons
    "Arcane.png", "ArcaneClicked.png", "ArcaneHover.png",
    "Experimental.png", "ExperimentalClicked.png", "ExperimentalHover.png",
    "Heat.png", "HeatClicked.png", "HeatHover.png",
    "Power.png", "PowerClicked.png", "PowerHover.png",
    # Generic UI icons
    "GenericHeat.png", "GenericInfinity.png", "GenericPlus.png", "GenericPower.png",
}


def main():
    # Collect component sprites (anything not in UI set, max 32x32)
    sprites = []
    for f in sorted(os.listdir(SPRITE_DIR)):
        if not f.endswith(".png") or f in UI_SPRITES:
            continue
        img = Image.open(SPRITE_DIR / f)
        if img.width > CELL or img.height > CELL:
            print(f"  Skipping {f} ({img.width}x{img.height}) — too large for {CELL}x{CELL} cell")
            continue
        sprites.append((f, img))

    print(f"Component sprites: {len(sprites)}")

    rows = (len(sprites) + COLS - 1) // COLS
    sheet_w = COLS * CELL
    sheet_h = rows * CELL

    # Build clean sheet
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    sheet_map = {}

    for idx, (name, img) in enumerate(sprites):
        col = idx % COLS
        row = idx // COLS
        # Center sprite in cell
        ox = col * CELL + (CELL - img.width) // 2
        oy = row * CELL + (CELL - img.height) // 2
        sheet.paste(img, (ox, oy), img if img.mode == "RGBA" else None)
        sheet_map[name] = {
            "col": col,
            "row": row,
            "orig_w": img.width,
            "orig_h": img.height,
        }

    clean_path = OUT_DIR / "sprites_reference_sheet.png"
    sheet.save(clean_path)
    print(f"Clean sheet: {clean_path} ({sheet_w}x{sheet_h})")

    # Build annotated sheet (2x scale for readability)
    SCALE = 2
    ann_w = sheet_w * SCALE
    ann_h = sheet_h * SCALE + rows * 12  # extra space for labels
    annotated = Image.new("RGBA", (ann_w, ann_h), (30, 30, 30, 255))

    # Paste scaled sheet
    sheet_scaled = sheet.resize((sheet_w * SCALE, sheet_h * SCALE), Image.NEAREST)
    annotated.paste(sheet_scaled, (0, 0), sheet_scaled)

    draw = ImageDraw.Draw(annotated)

    # Draw grid lines
    for c in range(COLS + 1):
        x = c * CELL * SCALE
        draw.line([(x, 0), (x, sheet_h * SCALE)], fill=(80, 80, 80, 180), width=1)
    for r in range(rows + 1):
        y = r * CELL * SCALE
        draw.line([(0, y), (sheet_w * SCALE, y)], fill=(80, 80, 80, 180), width=1)

    # Add labels below the sheet
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except (OSError, IOError):
        font = ImageFont.load_default()

    label_y_base = sheet_h * SCALE + 2
    for idx, (name, _img) in enumerate(sprites):
        col = idx % COLS
        row = idx // COLS
        label = name.replace(".png", "")
        # Write label rotated or as short text under the grid
        lx = col * CELL * SCALE + 2
        ly = label_y_base + row * 12
        draw.text((lx, ly), label[:6], fill=(200, 200, 200), font=font)

    ann_path = OUT_DIR / "sprites_reference_sheet_annotated.png"
    annotated.save(ann_path)
    print(f"Annotated sheet: {ann_path} ({ann_w}x{ann_h})")

    # Save map
    map_path = OUT_DIR / "sprites_sheet_map.json"
    with open(map_path, "w") as f:
        json.dump(sheet_map, f, indent=2)
    print(f"Sheet map: {map_path} ({len(sheet_map)} entries)")


if __name__ == "__main__":
    main()
