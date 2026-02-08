# Implementation Notes (Prototype)

This is a minimal Python + raylib prototype that uses **original sprite assets** from the Unity export.

## Location

- Code: `implementation/src`
- Assets: `decompilation/recovered/recovered_assets`

## Run (local)

1. Install dependencies from `implementation/requirements.txt` (either `raylib` or `pyray` works; the code tries both).
2. Run:

```
python implementation/src/main.py
```

## Asset path override

If you relocate assets, set:

```
REV_REACTOR_ASSETS_DIR=/path/to/recovered_assets
```

## Current scope

- Draws the grid using the original `AltGrid.png` sprite.
- Renders original `Heat.png` and `Power.png` icons with simple bars.
- Supports a **reference overlay** to align layout (toggle with **F1**; cycle with **F2/F3**).
- Simulation step is a placeholder that uses validated stat names but **not** original values yet.
- A `ResourceStore` now holds money/power/heat/exotic counters and last‑tick deltas.
- The grid tracks cell occupancy and exposes neighbor helpers (matches wasm neighbor offsets).
- Left‑click places a placeholder component on the grid and draws its original sprite.
- Store panel now renders a grid of **IconButton** slots (48x52) derived from recovered sprites; icons are populated from recovered component sprite names.
- Store catalog is seeded from `decompilation/recovered/recovered_mono/monobehaviour_index.csv` and filtered by component sprite names.
- `implementation/layout.json` controls layout constants for aligning to reference screenshots.
- `decompilation/tools/extract_ui_layout.py` regenerates `implementation/layout.json` from Unity RectTransforms (Build.data).

Next: decode serialized component stats from recovered MonoBehaviour blobs and wire the store list + prices to those values.

## Web crash note (2026-02-08)

- Renderer minidump for `https://nuclear.mixy.one` shows Windows fail-fast `0xC0000409` with parameter `0xD` (`int 0x29` in `ntdll`), not a Python traceback.
- Initial mitigation applied: upgraded web runtime from `pyodide v0.27.0` to `v0.29.3` in `web/index.html` and `dist/index.html`.
