"""Reactor blueprints: capture the current grid layout and re-apply it later.

Storage: browser localStorage on the web build, ``blueprints.json`` next to
the project root on native.  A blueprint is a plain dict:

    {"name": "Design 1", "width": 12, "height": 10,
     "cells": [[x, y, "Component Name"], ...]}
"""
from __future__ import annotations

import json
import sys

_WEB = sys.platform == "emscripten"
_KEY = "rev_reactor_blueprints"

if not _WEB:
    from pathlib import Path

    _FILE = Path(__file__).resolve().parent.parent / "blueprints.json"


def _read_raw() -> str | None:
    try:
        if _WEB:
            from js import localStorage  # type: ignore

            value = localStorage.getItem(_KEY)
            return None if value is None else str(value)
        if _FILE.exists():
            return _FILE.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


def _write_raw(text: str) -> bool:
    try:
        if _WEB:
            from js import localStorage  # type: ignore

            localStorage.setItem(_KEY, text)
            return True
        _FILE.write_text(text, encoding="utf-8")
        return True
    except Exception:
        return False


def load_blueprints() -> list[dict]:
    raw = _read_raw()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    out: list[dict] = []
    if isinstance(data, list):
        for bp in data:
            if isinstance(bp, dict) and isinstance(bp.get("cells"), list):
                out.append(bp)
    return out


def save_blueprints(blueprints: list[dict]) -> bool:
    return _write_raw(json.dumps(blueprints))


def capture_blueprint(sim, name: str) -> dict | None:
    """Snapshot every placed component. Returns None if the grid is empty."""
    grid = sim.grid
    if grid is None:
        return None
    cells = []
    for gx, gy, _gz, comp in grid.iter_cells():
        if comp is not None:
            cells.append([int(gx), int(gy), comp.stats.name])
    if not cells:
        return None
    return {
        "name": name,
        "width": int(getattr(grid, "width", 0)),
        "height": int(getattr(grid, "height", 0)),
        "cells": cells,
    }


def apply_blueprint(sim, blueprint: dict) -> tuple[int, int, int]:
    """Place blueprint components into EMPTY cells, paying normal costs.

    Returns (placed, unaffordable, skipped) where skipped covers occupied or
    out-of-range cells and components that no longer exist in the shop.
    """
    from game.simulation import ReactorComponent

    grid = sim.grid
    if grid is None:
        return 0, 0, 0
    lookup = {c.name: c for c in sim.shop_components}
    placed = unaffordable = skipped = 0
    for entry in blueprint.get("cells", []):
        try:
            x, y, name = int(entry[0]), int(entry[1]), str(entry[2])
        except Exception:
            skipped += 1
            continue
        stats = lookup.get(name)
        if stats is None:
            skipped += 1
            continue
        try:
            if grid.get(x, y, 0) is not None:
                skipped += 1
                continue
        except Exception:
            skipped += 1
            continue
        cost = sim.get_component_cost(stats)
        if sim.store.money < cost:
            unaffordable += 1
            continue
        if sim.place_component(x, y, ReactorComponent(stats=stats), recompute_capacities=False):
            sim.store.money -= cost
            placed += 1
        else:
            skipped += 1
    sim.recompute_max_capacities()
    return placed, unaffordable, skipped
