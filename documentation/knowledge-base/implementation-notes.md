# Implementation Notes (Prototype)

This is a minimal Python + raylib prototype that uses **original sprite assets** from the Unity export.

## Location

- Code: `implementation/src`
- Assets: `decompilation/recovered/recovered_assets`
- Packaging: `pyproject.toml` + `uv.lock` at repo root

## Run (local)

1. Sync dependencies with `uv`.
2. Run:

```
uv sync
uv run rev-reactor
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

## Web crash note (2026-02-12)

- Added iframe watchdog architecture: `web/index.html` is now a host page and `web/game.html` runs the game runtime.
- Child frame emits `postMessage` heartbeats and the host can reload a genuinely stalled iframe.
- Save persistence remains in web localStorage (`rev_reactor_save`), so iframe restarts do not clear saved progress.
- Updated iframe sandbox mode to `sandbox="allow-scripts"` and moved save/load/theme state sync to a parent↔child `postMessage` bridge (`RevReactorHostBridge`) so web save persistence still works without `allow-same-origin`.

## Web lifecycle and efficiency (2026-08-10)

- Saves now include a wall-clock timestamp. Loading or reopening applies deterministic catch-up for elapsed time, capped at four hours and 10,000 simulation ticks so a stale save cannot lock up Pyodide. Legacy saves begin timestamp-based catch-up after their next save.
- Hidden tabs stop both simulation and rendering work. On visibility return, or after a long browser stall, elapsed time is consumed once by catch-up; paused games and the reactor-view panel do not advance.
- The iframe watchdog now uses a 12-second timeout, a 60-second startup/resume grace period, and a request/response probe before restarting the runtime. Heartbeats run every two seconds and immediately on visibility return, avoiding false reloads after ordinary tab switches.
- Web rendering is paced at 30 FPS while active or animated, 10 FPS while idle, and zero frames while hidden. Repeated sprite tinting and per-frame command strings are cached/deduplicated.
- Simulation hot paths now cache upgrade bonuses, component multipliers, grid topology, clean preview values, help wrapping, and store-page results. A like-for-like stable 304-component native benchmark improved from roughly 4,936 to 21,232 ticks/second (4.3×).
- Regression coverage includes five Python lifecycle/cache tests and two Node tests for hidden-tab timing and renderer wake-up behavior.

## Save compatibility note (2026-02-13)

- Options panel now exposes **Export Old** and **Export New** buttons.
- `Export Old` emits original Reactor Idle encrypted save text (AES-256-CBC with the game's PasswordDeriveBytes-compatible key derivation), bounded to legacy schema.
- `Export New` emits unrestricted base64-JSON (full reimplementation state, no legacy bounds).
- Import remains backward-compatible with all three formats: raw JSON, base64-JSON, and original encrypted text.
- Original `ProtiumDepleted` now round-trips through import/export (`depleted_protium_count`).
- In sandboxed iframe mode (`sandbox="allow-scripts"`), exports now route through the host page via `postMessage` (`rev-reactor-download`) so file downloads still work without relaxing iframe sandbox flags.
- Legacy component index mapping now follows `ComponentTypes` field order (fixes old-export misloads such as Ultimate Reflector/Extreme Capacitor becoming coolants).
- Legacy export/import now convert Y coordinates between runtime grid space and original save space (vertical axis inversion fix).
