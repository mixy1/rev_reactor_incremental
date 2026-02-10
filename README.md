# Rev Reactor

A reverse-engineered reimplementation of a Unity WebGL reactor idle game, built with Python and raylib.

## Project Structure

```
rev_reactor/
├── pyproject.toml           # Python package metadata + dependencies
├── uv.lock                  # uv-resolved lockfile
├── implementation/          # Python reimplementation
│   ├── src/
│   │   ├── main.py          # Entry point, render loop, input handling
│   │   ├── raylib_compat.py # raylib Python bindings compatibility layer
│   │   ├── assets.py        # Asset loading (sprites, textures)
│   │   └── game/
│   │       ├── catalog.py   # Component type catalog (from JSON + binary RE)
│   │       ├── grid.py      # Reactor grid (placement, neighbors, scrolling)
│   │       ├── layout.py    # UI layout constants
│   │       ├── save.py      # Save/load system
│   │       ├── simulation.py # Core simulation (tick pipeline, power/heat)
│   │       ├── store.py     # Resource store (money, power, heat)
│   │       ├── types.py     # Data types (ComponentTypeStats, PlacedComponent)
│   │       ├── ui.py        # UI rendering (upgrades, prestige, tooltips)
│   │       └── upgrades.py  # Upgrade manager
│   ├── layout.json          # UI layout data extracted from binary
├── decompilation/           # RE artifacts and tools
│   ├── build/               # Original game binaries (gitignored)
│   ├── recovered/           # Extracted assets, metadata, scripts
│   └── tools/               # Il2CppDumper, binaryen, etc. (gitignored)
├── documentation/
│   ├── knowledge-base/      # RE findings, binary analysis notes
│   └── plans/               # Project plan and milestones
├── ghidra_scripts/          # Ghidra analysis scripts
└── AGENTS.md                # AI agent working conventions
```

## Running

```bash
uv sync
uv run rev-reactor
```

Requires Python 3.10+.

## Development Helpers

```bash
uv run python scripts/make_sprite_sheet.py
uv run python scripts/split_sprite_sheet.py
uv run pytest
uv run ruff check .
```

## Reverse Engineering

The original game is a Unity WebGL build. Decompilation was performed with:
- **Ghidra** — WASM binary analysis (`Build.wasm`)
- **Il2CppDumper** — Metadata extraction (`global-metadata.dat`)
- **UnityPy** — Asset bundle extraction (`Build.data`, `Build.data.unityfs`)

Key RE documentation lives in `documentation/knowledge-base/` — see `INDEX.md` for a full listing.
