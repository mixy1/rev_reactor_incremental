from __future__ import annotations

import sys
from dataclasses import dataclass, field
import json
import math
import re
from typing import Optional

_WEB = sys.platform == "emscripten"

from raylib_compat import (
    Color,
    Rectangle,
    Texture2D,
    begin_scissor_mode,
    draw_rectangle,
    draw_rectangle_lines,
    draw_text,
    draw_texture_ex,
    draw_texture_pro,
    end_scissor_mode,
    get_time,
    get_mouse_wheel_move,
    is_key_down,
    is_key_pressed,
    is_mouse_button_down,
    is_mouse_button_pressed,
    KEY_ESCAPE,
    KEY_SHIFT,
    MOUSE_BUTTON_LEFT,
    MOUSE_BUTTON_MIDDLE,
    MOUSE_BUTTON_RIGHT,
    measure_text,
    Vector2,
)

from game.layout import Layout
from game.types import ComponentTypeStats
from game.simulation import ReactorComponent, Simulation
from game.upgrades import UpgradeManager, UpgradeType


# ── Blueprint helpers (inlined so the web bundle needs no new file) ──
# Blueprints live on the simulation (sim.blueprints) and are written as part of
# the normal game save by game/save.py. Saving or deleting one sets
# sim.blueprints_dirty so the main loop writes the save straight away.


def _bp_list(sim) -> list:
    """The simulation's blueprint list (created if missing)."""
    bps = getattr(sim, "blueprints", None)
    if not isinstance(bps, list):
        bps = []
        try:
            sim.blueprints = bps
        except AttributeError:
            pass
    return bps


def _bp_mark_dirty(sim) -> None:
    try:
        sim.blueprints_dirty = True
    except AttributeError:
        pass


def _bp_cell_rect(grid, x: int, y: int) -> tuple[int, int, int, int]:
    """Exact on-screen rect of cell (x, y). Neighbouring cells share edges even
    when the zoomed cell size is fractional."""
    if hasattr(grid, "cell_rect"):
        return grid.cell_rect(x, y)
    px, py = grid.cell_to_screen(x, y)
    nx, ny = grid.cell_to_screen(x + 1, y + 1)
    return int(px), int(py), int(nx - px), int(ny - py)


def _bp_in_rect(x: int, y: int, rect) -> bool:
    return rect is None or (rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3])


def _bp_capture(sim, name: str, rect=None) -> Optional[dict]:
    """Snapshot placed components (only those inside rect, if given)."""
    grid = sim.grid
    if grid is None:
        return None
    cells = [
        [int(gx), int(gy), comp.stats.name]
        for gx, gy, _gz, comp in grid.iter_cells()
        if comp is not None and _bp_in_rect(gx, gy, rect)
    ]
    if not cells:
        return None
    return {"name": name, "cells": cells}


def _bp_bounds(bp: dict) -> tuple[int, int, int, int]:
    xs, ys = [], []
    for entry in bp.get("cells", []):
        try:
            xs.append(int(entry[0]))
            ys.append(int(entry[1]))
        except Exception:
            continue
    if not xs:
        return 0, 0, 0, 0
    return min(xs), min(ys), max(xs), max(ys)


# Vertical nudge (px) for the banner thumbnail so it looks centred in the banner art.
_BP_THUMB_Y_OFFSET = 6
# How much shorter (px) the thumbnail's max height is than the old square size.
_BP_THUMB_H_SHRINK = 4
# Colour of the "needs force" outline (the save selection's outline, in red).
_BP_FORCE_OUTLINE_COLOR = (255, 60, 60)

_BP_MOUSE_BUTTONS = (MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE)


def _bp_discover_key_codes() -> tuple[tuple, tuple]:
    """(own, extra): own = every KEY_* constant raylib_compat defines (so this
    works whatever numbering or type the web/native build uses); extra = a wide
    integer range covering raylib (32-348) and browser keyCodes (8-222)."""
    import raylib_compat as _rc

    own, seen = [], set()
    for name, val in vars(_rc).items():
        if name.startswith("KEY_") and not isinstance(val, bool) and isinstance(val, (int, str)) and val:
            if val not in seen:
                seen.add(val)
                own.append(val)
    extra = []
    if isinstance(getattr(_rc, "KEY_ESCAPE", 256), int):
        extra = [k for k in range(8, 349) if k not in seen]
    return tuple(own), tuple(extra)


_BP_OWN_KEYS, _BP_EXTRA_KEYS = _bp_discover_key_codes()


def _bp_safe(fn, arg) -> bool:
    """Call an input query; only a real True (or non-zero int) counts. Errors and
    odd return types (e.g. JS proxies on the web build) count as False."""
    try:
        v = fn(arg)
    except Exception:
        return False
    return v is True or (type(v) is int and v != 0)


def _bp_wheel() -> float:
    try:
        w = get_mouse_wheel_move()
        return float(w) if isinstance(w, (int, float)) else 0.0
    except Exception:
        return 0.0


def _bp_anchor_offset(bp: dict, cx: int, cy: int, grid=None) -> tuple[int, int]:
    """Shift that puts the blueprint's centre cell under grid cell (cx, cy),
    snapped to the nearest position where every part is inside the grid.
    (A blueprint larger than the grid can't fit and is left unclamped.)"""
    minx, miny, maxx, maxy = _bp_bounds(bp)
    cols, rows = maxx - minx + 1, maxy - miny + 1
    ox = cx - (minx + cols // 2)
    oy = cy - (miny + rows // 2)
    gw = getattr(grid, "width", None)
    gh = getattr(grid, "height", None)
    if gw is not None and cols <= gw:
        ox = max(-minx, min(ox, gw - 1 - maxx))
    if gh is not None and rows <= gh:
        oy = max(-miny, min(oy, gh - 1 - maxy))
    return ox, oy


def _bp_total_cost(sim, bp: dict) -> float:
    lookup = {c.name: c for c in sim.shop_components}
    total = 0.0
    for entry in bp.get("cells", []):
        try:
            stats = lookup.get(str(entry[2]))
        except Exception:
            continue
        if stats is not None:
            total += sim.get_component_cost(stats)
    return total


def _bp_targets(sim, bp: dict, ox: int, oy: int, force: bool = False) -> list:
    """Resolve each blueprint cell (shifted by ox, oy) to (stats, x, y, reason).

    reason:
      "ok"      empty cell, or a depleted component that will be swapped out
      "same"    a live component of the right type is already there; blocks
                placement unless Shift is held, then it is left alone
      "forced"  live component of a DIFFERENT type, sold because Shift is held
      "blocked" occupied by a live component, off the grid, or unknown part
      "broke"   placeable, but not enough money (refunds from sold parts count)
    """
    grid = sim.grid
    lookup = {c.name: c for c in sim.shop_components}
    gw = getattr(grid, "width", None)
    gh = getattr(grid, "height", None)
    spent = 0.0
    out = []
    for entry in bp.get("cells", []):
        try:
            x, y, name = int(entry[0]) + ox, int(entry[1]) + oy, str(entry[2])
        except Exception:
            continue
        stats = lookup.get(name)
        reason = "ok"
        refund = 0.0
        if stats is None:
            reason = "blocked"
        elif gw is not None and gh is not None and not (0 <= x < gw and 0 <= y < gh):
            reason = "blocked"
        else:
            existing = None
            try:
                existing = grid.get(x, y, 0)
            except Exception:
                reason = "blocked"
            if reason == "ok" and existing is not None:
                if getattr(existing, "depleted", False):
                    refund = Simulation.sell_value(existing)
                elif existing.stats.name == stats.name:
                    reason = "same"  # already correct: never sold, costs nothing
                elif force:
                    reason = "forced"
                    refund = Simulation.sell_value(existing)
                else:
                    reason = "blocked"
        if reason in ("ok", "forced"):
            net = sim.get_component_cost(stats) - refund
            if sim.store.money - spent < net:
                reason = "broke"
            else:
                spent += net
        out.append((stats, x, y, reason))
    return out


@dataclass
class Ui:
    btn_big: Texture2D
    btn_big_hover: Texture2D
    btn_big_pressed: Texture2D
    btn_med: Texture2D
    btn_med_hover: Texture2D
    btn_med_pressed: Texture2D
    btn_small: Texture2D
    btn_small_hover: Texture2D
    btn_small_pressed: Texture2D
    heat_icon: Optional[Texture2D] = None
    power_icon: Optional[Texture2D] = None
    button_small_base: Optional[Texture2D] = None
    button_small_hover: Optional[Texture2D] = None
    button_small_pressed: Optional[Texture2D] = None
    icon_button: Optional[Texture2D] = None
    icon_button_hover: Optional[Texture2D] = None
    icon_button_pressed: Optional[Texture2D] = None
    icon_button_locked: Optional[Texture2D] = None
    store_block: Optional[Texture2D] = None
    top_banner: Optional[Texture2D] = None
    store_tab_power: Optional[Texture2D] = None
    store_tab_power_hover: Optional[Texture2D] = None
    store_tab_power_pressed: Optional[Texture2D] = None
    store_tab_heat: Optional[Texture2D] = None
    store_tab_heat_hover: Optional[Texture2D] = None
    store_tab_heat_pressed: Optional[Texture2D] = None
    store_tab_experimental: Optional[Texture2D] = None
    store_tab_experimental_hover: Optional[Texture2D] = None
    store_tab_experimental_pressed: Optional[Texture2D] = None
    store_tab_arcane: Optional[Texture2D] = None
    store_tab_arcane_hover: Optional[Texture2D] = None
    store_tab_arcane_pressed: Optional[Texture2D] = None
    upgrade_sprites: Optional[dict] = None  # icon_path -> Texture2D
    save_dir: object = None  # Truthy to enable export/import buttons
    component_sprites: Optional[dict] = None  # sprite_name -> Texture2D
    help_scroll_y: float = 0.0  # scroll offset for help panel
    help_drag_active: bool = False  # drag-to-scroll state
    help_drag_last_y: float = 0.0
    # Blueprint panel state
    blueprints: list = field(default_factory=list)
    blueprint_index: int = 0
    blueprints_loaded: bool = False
    blueprint_confirm_delete: bool = False
    blueprint_placing: bool = False
    blueprint_selecting: bool = False  # drag-select an area to save
    blueprint_sel_rect: Optional[tuple] = None  # (x0, y0, x1, y1) inclusive cells
    blueprint_sel_anchor: Optional[tuple] = None
    blueprint_sel_dragging: bool = False
    _bp_force_outline: Optional[tuple] = None  # (x0, y0, x1, y1) from the ghost, drawn in draw()
    _bp_rmb_latch: bool = False  # right-click blocked until released (after a cancel)
    _bp_preview_open: bool = False  # enlarged blueprint view is showing
    _bp_input_latch: bool = False  # after closing it: swallow input until mouse released
    _bp_watch_mouse: frozenset = frozenset()  # buttons down at the last check
    _bp_watch_keys: frozenset = frozenset()  # keys down at the last check
    _bp_watch_wheel: float = 0.0
    _bp_input_blocked: bool = False  # this frame's input-gate result
    _bp_delete_rect: Optional[tuple] = None  # Delete/"Sure?" button rect from last panel draw
    blueprint_status: str = ""
    blueprint_status_until: float = 0.0

    def _bp_say(self, text: str) -> None:
        self.blueprint_status = text
        self.blueprint_status_until = get_time() + 3.5

    def _bp_sync(self, sim: Simulation) -> None:
        """Point at the simulation's blueprint list (it is replaced on load/import)."""
        self.blueprints = _bp_list(sim)

    def _bp_current(self) -> Optional[dict]:
        if not self.blueprints:
            return None
        self.blueprint_index = max(0, min(self.blueprint_index, len(self.blueprints) - 1))
        return self.blueprints[self.blueprint_index]

    def _bp_sprite_lookup(self, sim: Simulation) -> dict:
        return {c.name: c.sprite_name for c in sim.shop_components}

    def blueprint_blocks_right_click(self) -> bool:
        """Call each frame before right-click selling/deselecting.

        Right-click while placing or selecting cancels that mode, and right-click
        then stays blocked until the button is released, so the press that
        cancelled can't go on to sell the component under the cursor. Safe to
        call more than once per frame."""
        down = is_mouse_button_down(MOUSE_BUTTON_RIGHT)
        if self._bp_rmb_latch and not down:
            self._bp_rmb_latch = False
        if (self.blueprint_placing or self.blueprint_selecting) and (
            down or is_mouse_button_pressed(MOUSE_BUTTON_RIGHT)
        ):
            self.cancel_blueprint_modes()
            self._bp_rmb_latch = True
        return self._bp_rmb_latch

    def _bp_handle_input(self, sim: Simulation, mouse_x: float, mouse_y: float) -> None:
        """Blueprint input: right-click / Esc cancel and drag-selection."""
        self.blueprint_blocks_right_click()
        if sim.view_mode != "reactor" or not (self.blueprint_selecting or self.blueprint_placing):
            return
        if is_key_pressed(KEY_ESCAPE):
            self.cancel_blueprint_modes()
            return
        self.update_blueprint_selection(
            sim, mouse_x, mouse_y,
            is_mouse_button_down(MOUSE_BUTTON_LEFT),
            is_mouse_button_pressed(MOUSE_BUTTON_LEFT),
        )

    def _bp_input_snapshot(self) -> tuple[frozenset, frozenset]:
        mouse = frozenset(b for b in _BP_MOUSE_BUTTONS if _bp_safe(is_mouse_button_down, b))
        keys = frozenset(k for k in _BP_OWN_KEYS + _BP_EXTRA_KEYS if _bp_safe(is_key_down, k))
        return mouse, keys

    def _bp_watch_begin(self) -> None:
        """Baseline for new-input detection: anything already held (e.g. the
        click that opened the preview) is ignored until released."""
        self._bp_watch_mouse, self._bp_watch_keys = self._bp_input_snapshot()
        self._bp_watch_wheel = _bp_wheel()

    def _bp_watch_new_input(self) -> tuple[frozenset, bool, bool]:
        """New presses since the last check: (new mouse buttons, any new key, wheel).
        A press counts only as an up->down change (or the build's own one-frame
        "pressed" signal for a button/key that wasn't already held)."""
        mouse, keys = self._bp_input_snapshot()
        prev_mouse, prev_keys = self._bp_watch_mouse, self._bp_watch_keys
        new_mouse = set(mouse - prev_mouse)
        for b in _BP_MOUSE_BUTTONS:
            if b not in prev_mouse and _bp_safe(is_mouse_button_pressed, b):
                new_mouse.add(b)
        new_key = bool(keys - prev_keys) or any(
            k not in prev_keys and _bp_safe(is_key_pressed, k) for k in _BP_OWN_KEYS
        )
        w = _bp_wheel()
        wheel = w != 0.0 and w != self._bp_watch_wheel
        self._bp_watch_mouse, self._bp_watch_keys, self._bp_watch_wheel = mouse, keys, w
        return frozenset(new_mouse), new_key, wheel

    def cancel_blueprint_modes(self) -> None:
        """Leave placement and selection modes, clear any selection, and drop a
        pending delete confirmation."""
        self.blueprint_confirm_delete = False
        self.blueprint_placing = False
        self.blueprint_selecting = False
        self.blueprint_sel_rect = None
        self.blueprint_sel_anchor = None
        self.blueprint_sel_dragging = False

    def update_blueprint_selection(
        self, sim: Simulation, mouse_x: float, mouse_y: float, mouse_down: bool, mouse_pressed: bool
    ) -> None:
        """Click-and-drag rectangle selection on the grid (while saving)."""
        if not self.blueprint_selecting or sim.grid is None:
            return
        grid = sim.grid
        if mouse_pressed:
            cell = grid.screen_to_cell(int(mouse_x), int(mouse_y))
            if cell is not None:  # presses on the banner/buttons are ignored
                self.blueprint_sel_anchor = (cell[0], cell[1])
                self.blueprint_sel_dragging = True
                self.blueprint_sel_rect = (cell[0], cell[1], cell[0], cell[1])
        elif self.blueprint_sel_dragging and mouse_down:
            cell = grid.screen_to_cell_unbounded(int(mouse_x), int(mouse_y))
            if cell is not None and self.blueprint_sel_anchor is not None:
                cx, cy = cell
                gw = getattr(grid, "width", None)
                gh = getattr(grid, "height", None)
                if gw is not None:
                    cx = max(0, min(cx, gw - 1))
                if gh is not None:
                    cy = max(0, min(cy, gh - 1))
                ax, ay = self.blueprint_sel_anchor
                self.blueprint_sel_rect = (min(ax, cx), min(ay, cy), max(ax, cx), max(ay, cy))
        if self.blueprint_sel_dragging and not mouse_down:
            self.blueprint_sel_dragging = False

    def draw_blueprint_selection(self, sim: Simulation) -> None:
        """Blue translucent selection rectangle (caller clips to the grid viewport)."""
        if not self.blueprint_selecting or self.blueprint_sel_rect is None or sim.grid is None:
            return
        grid = sim.grid
        x0, y0, x1, y1 = self.blueprint_sel_rect
        try:
            px, py = grid.cell_to_screen(x0, y0)
            ex, ey = grid.cell_to_screen(x1 + 1, y1 + 1)
        except Exception:
            return
        w, h = ex - px, ey - py
        draw_rectangle(int(px), int(py), int(w), int(h), Color(70, 140, 255, 80))
        draw_rectangle_lines(int(px), int(py), int(w), int(h), Color(120, 190, 255, 255))
        if w > 4 and h > 4:
            draw_rectangle_lines(int(px) + 1, int(py) + 1, int(w) - 2, int(h) - 2, Color(120, 190, 255, 255))

    def _bp_count_in_rect(self, sim: Simulation, rect) -> int:
        if sim.grid is None or rect is None:
            return 0
        return sum(1 for gx, gy, _gz, c in sim.grid.iter_cells() if c is not None and _bp_in_rect(gx, gy, rect))

    def _bp_cost_in_rect(self, sim: Simulation, rect) -> float:
        """Current buy price of every component inside the selection."""
        if sim.grid is None or rect is None:
            return 0.0
        return sum(
            sim.get_component_cost(c.stats)
            for gx, gy, _gz, c in sim.grid.iter_cells()
            if c is not None and _bp_in_rect(gx, gy, rect)
        )

    def draw_blueprint_ghost(self, sim: Simulation, mouse_x: float, mouse_y: float) -> None:
        """Translucent preview of the selected blueprint under the cursor.
        Green = placeable (empty or depleted cell), grey = already correct,
        blue = different live component that Shift will sell, amber = can't afford, red = blocked / out of range.
        A red outline around the whole blueprint means a normal click won't place
        it here (it needs Shift to force); it's hidden while Shift is held. The
        outline is only worked out here; Ui.draw draws it later, over the grid
        frame, clipped like the save selection box.
        Call inside the grid scissor region (before the grid frame is drawn)."""
        self._bp_force_outline = None
        if not self.blueprint_placing or sim.grid is None:
            return
        self._bp_sync(sim)
        bp = self._bp_current()
        if bp is None:
            return
        grid = sim.grid
        cell = grid.screen_to_cell(int(mouse_x), int(mouse_y))
        if cell is None:
            return
        ox, oy = _bp_anchor_offset(bp, cell[0], cell[1], grid)
        cell_sz = grid.view_cell_size
        sprites = self.component_sprites or {}
        colours = {
            "ok": (90, 255, 110),
            "same": (200, 200, 215),
            "forced": (90, 170, 255),
            "broke": (255, 190, 60),
            "blocked": (255, 70, 70),
        }
        force = is_key_down(KEY_SHIFT)
        targets = _bp_targets(sim, bp, ox, oy, force)
        # Would a normal click be refused here? Then outline in red, but only
        # while Shift isn't held (holding it is the force).
        needs_force = not force and any(t[3] in ("blocked", "same", "broke") for t in targets)
        for stats, x, y, reason in targets:
            try:
                px, py, cw, ch = _bp_cell_rect(grid, x, y)
            except Exception:
                continue
            r, g, b = colours[reason]
            draw_rectangle(px, py, cw, ch, Color(r, g, b, 70))
            tex = sprites.get(stats.sprite_name) if stats is not None else None
            if tex is not None:
                scale = min(1.0, cw / max(1, tex.width), ch / max(1, tex.height))
                dw, dh = tex.width * scale, tex.height * scale
                draw_texture_pro(
                    tex,
                    Rectangle(0, 0, tex.width, tex.height),
                    Rectangle(px + (cw - dw) * 0.5, py + (ch - dh) * 0.5, dw, dh),
                    Vector2(0, 0),
                    0.0,
                    Color(min(255, 120 + r // 2), min(255, 120 + g // 2), min(255, 120 + b // 2), 165),
                )
            draw_rectangle_lines(px, py, cw, ch, Color(r, g, b, 200))

        if needs_force:
            minx, miny, maxx, maxy = _bp_bounds(bp)
            try:
                bx, by = grid.cell_to_screen(minx + ox, miny + oy)
            except Exception:
                return
            # Same kind of outline as the save selection: around the blueprint's
            # cells, drawn later by Ui.draw (x, y, w, h).
            right, bottom = grid.cell_to_screen(maxx + ox + 1, maxy + oy + 1)
            self._bp_force_outline = (int(bx), int(by), int(right - bx), int(bottom - by))

    def _draw_force_outline(self) -> None:
        """Red "needs force" outline worked out by draw_blueprint_ghost this frame:
        the same 2-line outline as the save selection box, in red."""
        if self._bp_force_outline is None:
            return
        x, y, w, h = self._bp_force_outline
        red = Color(*_BP_FORCE_OUTLINE_COLOR, 255)
        draw_rectangle_lines(x, y, w, h, red)
        if w > 4 and h > 4:
            draw_rectangle_lines(x + 1, y + 1, w - 2, h - 2, red)

    def place_blueprint_at(self, sim: Simulation, cx: int, cy: int, quiet: bool = False) -> None:
        """Stamp the selected blueprint centred on cell (cx, cy). Silent: the
        ghost's colours and red outline already show what will happen.

        Without Shift, nothing is placed if any part is blocked or unaffordable.
        Depleted components are swapped out automatically. Holding Shift sells
        live blockers of a different type (matching parts are left alone) and
        places whatever parts can be afforded. Costs are charged as normal,
        sales refunded. `quiet` is accepted for main.py compatibility (unused)."""
        self._bp_sync(sim)
        bp = self._bp_current()
        if bp is None or sim.grid is None:
            return
        ox, oy = _bp_anchor_offset(bp, cx, cy, sim.grid)
        force = is_key_down(KEY_SHIFT)
        targets = _bp_targets(sim, bp, ox, oy, force)
        # Without Shift, an already-correct part still blocks placement (it is
        # only skipped, not sold, when Shift forces the placement).
        if any(t[3] == "blocked" or (t[3] == "same" and not force) for t in targets):
            return
        # Without Shift it's all-or-nothing on cost too; Shift places what it can.
        if not force and any(t[3] == "broke" for t in targets):
            return
        for stats, x, y, reason in targets:
            if reason not in ("ok", "forced"):
                continue  # "same" is left alone, "broke" is skipped under Shift
            existing = sim.grid.get(x, y, 0)
            if existing is not None:
                sim.remove_component(x, y, recompute_capacities=False)
                sim.store.money += Simulation.sell_value(existing)
            cost = sim.get_component_cost(stats)
            if sim.place_component(x, y, ReactorComponent(stats=stats), recompute_capacities=False):
                sim.store.money -= cost
        sim.recompute_max_capacities()

    def _draw_blueprint_cells(self, sim: Simulation, bp: dict, ox: int, oy: int, cs: int) -> None:
        """Grid tiles under the blueprint's bounding box, then its component sprites."""
        minx, miny, maxx, maxy = _bp_bounds(bp)
        cols, rows = maxx - minx + 1, maxy - miny + 1
        tile = getattr(sim.grid, "tile_texture", None) if sim.grid is not None else None
        for ry in range(rows):
            for rx in range(cols):
                tx, ty = ox + rx * cs, oy + ry * cs
                if tile is not None:
                    draw_texture_pro(
                        tile,
                        Rectangle(0, 0, tile.width, tile.height),
                        Rectangle(tx, ty, cs, cs),
                        Vector2(0, 0),
                        0.0,
                        Color(255, 255, 255, 255),
                    )
                else:
                    draw_rectangle(tx, ty, cs, cs, Color(30, 34, 44, 255))
        sprites = self.component_sprites or {}
        names = self._bp_sprite_lookup(sim)
        for entry in bp.get("cells", []):
            try:
                cx, cy, name = int(entry[0]) - minx, int(entry[1]) - miny, str(entry[2])
            except Exception:
                continue
            px, py = ox + cx * cs, oy + cy * cs
            tex = sprites.get(names.get(name))
            if tex is None:
                draw_rectangle(px, py, cs, cs, Color(120, 120, 140, 255))
                continue
            scale = cs / max(1, max(tex.width, tex.height))
            dw, dh = tex.width * scale, tex.height * scale
            draw_texture_pro(
                tex,
                Rectangle(0, 0, tex.width, tex.height),
                Rectangle(px + (cs - dw) * 0.5, py + (cs - dh) * 0.5, dw, dh),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )

    def _draw_blueprint_thumb(
        self, sim: Simulation, bp: dict, col_x: int, center_y: int, max_w: int, max_h: int
    ) -> tuple[int, int, int, int]:
        """Bordered thumbnail fitted to the blueprint's shape. The box (border
        included) is at most max_w x max_h, centred horizontally in a column
        starting at col_x and vertically on center_y. Returns the box rect."""
        pad = 2  # 1px border + 1px gap
        minx, miny, maxx, maxy = _bp_bounds(bp)
        cols, rows = maxx - minx + 1, maxy - miny + 1
        cs = max(2, min((max_w - 2 * pad) // cols, (max_h - 2 * pad) // rows, 20))
        box_w = cols * cs + 2 * pad
        box_h = rows * cs + 2 * pad
        x = col_x + max(0, (max_w - box_w) // 2)
        y = center_y - box_h // 2
        self._draw_blueprint_cells(sim, bp, x + pad, y + pad, cs)
        draw_rectangle_lines(x, y, box_w, box_h, Color(100, 110, 140, 255))
        return x, y, box_w, box_h

    def blueprint_input_gate(self) -> bool:
        """Call once per frame BEFORE any input handling. True = ignore all input.

        While the enlarged blueprint view is open, input is swallowed and any
        press, key or wheel movement closes it. After it closes, input stays
        blocked until every mouse button is released, so the closing click
        can't place, sell or press anything."""
        blocked = False
        if self._bp_preview_open:
            new_mouse, new_key, wheel = self._bp_watch_new_input()
            if new_mouse or new_key or wheel:
                self._bp_preview_open = False
                # Only a mouse close needs the wait-for-release latch.
                self._bp_input_latch = any(is_mouse_button_down(b) for b in _BP_MOUSE_BUTTONS)
            blocked = True
        elif self._bp_input_latch:
            if any(is_mouse_button_down(b) for b in _BP_MOUSE_BUTTONS):
                blocked = True
            else:
                self._bp_input_latch = False
        self._bp_input_blocked = blocked
        return blocked

    def draw_blueprint_preview(self, sim: Simulation, layout: Layout) -> None:
        """Enlarged view of the selected blueprint covering most of the screen.
        Call last in the frame so it sits on top of everything."""
        if not self._bp_preview_open:
            return
        self._bp_sync(sim)
        bp = self._bp_current()
        if bp is None:
            self._bp_preview_open = False
            return
        win_w, win_h = layout.window_width, layout.window_height
        text_color = Color(230, 230, 230, 255)
        border = Color(100, 110, 140, 255)
        draw_rectangle(0, 0, win_w, win_h, Color(0, 0, 0, 170))

        mx_, my_ = max(16, win_w // 16), max(16, win_h // 16)
        bx, by, bw, bh = mx_, my_, win_w - 2 * mx_, win_h - 2 * my_
        draw_rectangle(bx, by, bw, bh, Color(18, 20, 28, 240))
        draw_rectangle_lines(bx, by, bw, bh, border)

        title = str(bp.get("name", "Blueprint"))
        draw_text(title, bx + (bw - _measure(title, 20)) // 2, by + 14, 20, text_color)
        total_cost = _bp_total_cost(sim, bp)
        sub = f"{len(bp.get('cells', []))} parts  |  Total cost: {format_number_with_suffix(total_cost)}"
        sub_color = Color(255, 170, 90, 255) if sim.store.money < total_cost else Color(190, 190, 200, 255)
        draw_text(sub, bx + (bw - _measure(sub, 12)) // 2, by + 40, 12, sub_color)
        hint = "Click or press any key to close"
        draw_text(hint, bx + (bw - _measure(hint, 10)) // 2, by + bh - 22, 10, Color(150, 150, 165, 255))

        minx, miny, maxx, maxy = _bp_bounds(bp)
        cols, rows = maxx - minx + 1, maxy - miny + 1
        top, bottom = by + 64, by + bh - 34
        avail_w, avail_h = bw - 40, bottom - top
        cs = max(4, min(avail_w // cols, avail_h // rows, 96))
        gw, gh = cols * cs, rows * cs
        ox = bx + (bw - gw) // 2
        oy = top + (avail_h - gh) // 2
        self._draw_blueprint_cells(sim, bp, ox, oy, cs)
        draw_rectangle_lines(ox - 2, oy - 2, gw + 4, gh + 4, border)

    def _bp_update_delete_confirm(self, mouse_x: float, mouse_y: float) -> None:
        """While "Sure?" is showing, any input other than clicking it cancels."""
        rect = self._bp_delete_rect
        self._bp_delete_rect = None  # re-set by the panel when it's drawn this frame
        if not self.blueprint_confirm_delete:
            return
        new_mouse, new_key, wheel = self._bp_watch_new_input()
        if not (new_mouse or new_key or wheel):
            return
        if new_mouse == {MOUSE_BUTTON_LEFT} and not new_key and not wheel and rect is not None:
            x, y, w, h = rect
            if x <= mouse_x <= x + w and y <= mouse_y <= y + h:
                return  # clicking "Sure?": the panel performs the delete
        self.blueprint_confirm_delete = False

    def draw_blueprint_panel(
        self,
        sim: Simulation,
        layout: Layout,
        mouse_x: float,
        mouse_y: float,
        mouse_pressed: bool,
    ) -> None:
        """Blueprint controls + thumbnail, shown in the top banner when nothing
        is hovered."""
        self._bp_sync(sim)
        n = len(self.blueprints)
        cur = self._bp_current()
        if n == 0:
            self.blueprint_placing = False

        margin = 20
        panel_x = layout.top_panel_x
        panel_y = layout.top_panel_y
        panel_h = layout.top_panel_h
        right_edge = layout.pause_x - margin
        usable_w = right_edge - panel_x - margin
        text_color = Color(230, 230, 230, 255)
        dim_color = Color(170, 170, 180, 255)
        btn_h = 16
        by = panel_y + panel_h - margin - 6

        # Thumbnail on the left (nudged down to sit centred in the banner art).
        # Max box: a few px shorter than the old square, twice as wide. The
        # column width is fixed so the buttons don't shift between blueprints,
        # and it gives way if the buttons would otherwise run out of room.
        left = 0
        if cur is not None:
            base = max(32, min(panel_h - 20, 84))  # old square thumbnail size
            max_h = base - _BP_THUMB_H_SHRINK
            worst_labels = ("<", ">", "Confirm", "Cancel", "Cancel", "Delete")
            btn_room = sum(max(18, _measure(l, 10) + 14) for l in worst_labels) + 6 * (len(worst_labels) - 1)
            max_w = min(base * 2, max(base, usable_w - 14 - btn_room))
            center_y = panel_y + panel_h // 2 + _BP_THUMB_Y_OFFSET
            tx, ty, tw_, th_ = self._draw_blueprint_thumb(sim, cur, panel_x + margin, center_y, max_w, max_h)
            if tx <= mouse_x <= tx + tw_ and ty <= mouse_y <= ty + th_:
                draw_rectangle_lines(tx, ty, tw_, th_, Color(170, 190, 235, 255))
                if mouse_pressed:
                    self._bp_preview_open = True  # enlarge
                    self._bp_watch_begin()
            left = max_w + 14
        region_x = panel_x + margin + left
        region_w = max(40, usable_w - left)

        # Total cost: of the live selection while saving, else of the whole blueprint
        cost_txt = ""
        cost_color = text_color
        if self.blueprint_selecting:
            if self.blueprint_sel_rect is not None:
                total_cost = self._bp_cost_in_rect(sim, self.blueprint_sel_rect)
                cost_txt = f"Total cost: {format_number_with_suffix(total_cost)}"
                if sim.store.money < total_cost:
                    cost_color = Color(255, 170, 90, 255)
        elif cur is not None:
            total_cost = _bp_total_cost(sim, cur)
            cost_txt = f"Total cost: {format_number_with_suffix(total_cost)}"
            if sim.store.money < total_cost:
                cost_color = Color(255, 170, 90, 255)
        cost_y = panel_y + 56
        cost_has_room = cost_y + 10 <= by - 1

        title = "Blueprints"
        if cost_txt and not cost_has_room:
            title = f"Blueprints - {cost_txt}"
        tw = _measure(title, 16)
        draw_text(title, region_x + max(0, (region_w - tw) // 2), panel_y + 20, 16, text_color)

        # Info / status line
        if self.blueprint_status and get_time() < self.blueprint_status_until:
            info = self.blueprint_status
            info_color = Color(245, 200, 70, 255)
        elif self.blueprint_selecting:
            rect = self.blueprint_sel_rect
            if rect is None:
                info = "Drag over the grid to select an area (Esc cancels)"
                info_color = Color(120, 190, 255, 255)
            else:
                cnt = self._bp_count_in_rect(sim, rect)
                info = f"Selected {rect[2] - rect[0] + 1}x{rect[3] - rect[1] + 1}, {cnt} parts. Confirm to save"
                info_color = Color(120, 190, 255, 255)
        elif self.blueprint_placing:
            if is_key_down(KEY_SHIFT):
                info = "Shift: force place (sells differing parts)"
                info_color = Color(120, 190, 255, 255)
            else:
                info = "Click to place (Shift forces, Esc cancels)"
                info_color = Color(120, 255, 140, 255)
        elif cur is not None:
            info = f"{self.blueprint_index + 1}/{n}: {cur.get('name', '?')} ({len(cur.get('cells', []))} parts)"
            info_color = text_color
        else:
            info = "No saved blueprints. Build a reactor, then click Save."
            info_color = dim_color
        if _measure(info, 10) > region_w:
            info = info[: max(4, region_w // 6)] + "..."
        iw = _measure(info, 10)
        draw_text(info, region_x + max(0, (region_w - iw) // 2), panel_y + 42, 10, info_color)

        if cost_txt and cost_has_room:
            cw = _measure(cost_txt, 10)
            draw_text(cost_txt, region_x + max(0, (region_w - cw) // 2), cost_y, 10, cost_color)

        # Button row
        confirming = self.blueprint_confirm_delete and n > 0
        labels = [
            ("prev", "<", n > 1),
            ("next", ">", n > 1),
            ("save", "Confirm" if (self.blueprint_selecting and self.blueprint_sel_rect is not None) else ("Cancel" if self.blueprint_selecting else "Save"), True),
            ("place", "Cancel" if self.blueprint_placing else "Place", n > 0),
            ("delete", "Sure?" if confirming else "Delete", n > 0),
        ]
        if self.blueprint_selecting and self.blueprint_sel_rect is not None:
            labels.insert(3, ("cancel_sel", "Cancel", True))
        gap = 6
        widths = [max(18, _measure(lbl, 10) + 14) for _, lbl, _ in labels]
        total = sum(widths) + gap * (len(labels) - 1)
        bx = region_x + max(0, (region_w - total) // 2)
        action = None
        for (key, lbl, enabled), w in zip(labels, widths):
            hover = enabled and bx <= mouse_x <= bx + w and by <= mouse_y <= by + btn_h
            if key == "delete":
                self._bp_delete_rect = (bx, by, w, btn_h) if enabled else None
            if not enabled:
                bg, fg = Color(30, 30, 36, 220), Color(100, 100, 110, 255)
            elif key == "delete" and confirming:
                bg, fg = Color(150, 50, 40, 240), text_color
            elif key == "place" and self.blueprint_placing:
                bg, fg = Color(40, 110, 60, 240), text_color
            elif key == "save" and self.blueprint_selecting:
                bg, fg = Color(40, 90, 160, 240), text_color
            elif hover:
                bg, fg = Color(80, 90, 120, 240), text_color
            else:
                bg, fg = Color(45, 50, 70, 230), text_color
            draw_rectangle(bx, by, w, btn_h, bg)
            draw_rectangle_lines(bx, by, w, btn_h, Color(100, 110, 140, 255))
            draw_text(lbl, bx + (w - _measure(lbl, 10)) // 2, by + 3, 10, fg)
            if hover and mouse_pressed:
                action = key
            bx += w + gap

        if action is None:
            return
        if action != "delete":
            self.blueprint_confirm_delete = False

        if action == "prev":
            self.blueprint_index = (self.blueprint_index - 1) % n
        elif action == "next":
            self.blueprint_index = (self.blueprint_index + 1) % n
        elif action == "save":
            if not self.blueprint_selecting:
                # Start drag-selecting an area of the reactor to save
                self.cancel_blueprint_modes()
                self.blueprint_selecting = True
                sim.selected_component_index = -1
            elif self.blueprint_sel_rect is None:
                self.cancel_blueprint_modes()  # "Cancel" before anything was selected
            else:
                used = {b.get("name") for b in self.blueprints}
                k = n + 1
                while f"Design {k}" in used:
                    k += 1
                captured = _bp_capture(sim, f"Design {k}", self.blueprint_sel_rect)
                if captured is None:
                    self._bp_say("No components in the selected area.")
                else:
                    self.blueprints.append(captured)
                    self.blueprint_index = len(self.blueprints) - 1
                    _bp_mark_dirty(sim)
                    self.cancel_blueprint_modes()
                    self._bp_say(f"Saved {captured['name']}.")
        elif action == "cancel_sel":
            self.cancel_blueprint_modes()
        elif action == "place":
            was_placing = self.blueprint_placing
            self.cancel_blueprint_modes()
            self.blueprint_placing = not was_placing
            if self.blueprint_placing:
                sim.selected_component_index = -1  # blueprint replaces shop selection
        elif action == "delete":
            if confirming:
                removed = self.blueprints.pop(self.blueprint_index)
                _bp_mark_dirty(sim)
                self.blueprint_confirm_delete = False
                self._bp_say(f"Deleted {removed.get('name', 'blueprint')}.")
            else:
                self.blueprint_confirm_delete = True
                self._bp_watch_begin()

    @staticmethod
    def draw_warning_badge(x: int, y: int, size: int = 12) -> None:
        """Compact amber warning badge used for outlet bottleneck warnings."""
        draw_rectangle(x + 1, y + 1, size, size, Color(18, 14, 8, 230))
        draw_rectangle(x, y, size, size, Color(62, 46, 14, 235))
        draw_rectangle_lines(x, y, size, size, Color(245, 200, 70, 255))
        text_x = x + max(1, size // 2 - 2)
        text_y = y + max(-1, (size - 10) // 2 - 1)
        draw_text("!", text_x, text_y, 10, Color(255, 236, 150, 255))

    def draw_button(self, bx : int, by : int, btn_pressed : bool, btn_hover : bool, label : str, size : int):
        if size == 3:
            tex = self.btn_big_pressed if btn_pressed else (self.btn_big_hover if btn_hover else self.btn_big)
        elif size == 2:
            tex = self.btn_med_pressed if btn_pressed else (self.btn_med_hover if btn_hover else self.btn_med)
        else:
            tex = self.btn_small_pressed if btn_pressed else (self.btn_small_hover if btn_hover else self.btn_small)
        draw_texture_ex(tex, Vector2(bx, by), 0.0, 1.0, Color(255, 255, 255, 255))
        font = _fit_font_size(label, tex.width - 20, 14, min_size=9)
        text_w = _measure(label, font)
        tx = bx + max(0, (tex.width - text_w) // 2)
        ty = by + max(0, (tex.height - font) // 2) 
        if btn_pressed: ty += 2
        draw_text(label, tx, ty, font, Color(220, 220, 220, 255))

    def draw(
        self,
        sim: Simulation,
        layout: Layout,
        hover_vent: bool,
        pressed_vent: bool,
        hover_sell: bool,
        pressed_sell: bool,
        mouse_x: float,
        mouse_y: float,
        mouse_pressed: bool,
    ) -> None:
        if not self._bp_input_blocked:
            self._bp_update_delete_confirm(mouse_x, mouse_y)
            self._bp_handle_input(sim, mouse_x, mouse_y)

        # Heat bar (RE: fill = reactor_heat / maxHeat, clamped 0..1)
        heat_fill = 0.0
        if sim.max_reactor_heat > 0:
            heat_fill = min(1.0, max(0.0, sim.reactor_heat / sim.max_reactor_heat))
        draw_rectangle(
            layout.heat_bar_x,
            layout.heat_bar_y,
            int(layout.bar_width * heat_fill),
            layout.bar_height,
            Color(240, 80, 80, 200),
        )
        # Heat icon + label
        icon_x = layout.heat_bar_x + 4
        icon_y = layout.heat_bar_y + 5
        text_x = icon_x
        if self.heat_icon is not None:
            draw_texture_ex(self.heat_icon, Vector2(icon_x, icon_y), 0.0, 1.0, Color(255, 255, 255, 255))
            text_x += self.heat_icon.width + 6
        heat_delta = sim.last_heat_change
        heat_sign = "+" if heat_delta >= 0 else ""
        heat_label = (
            f"{format_number_with_suffix(sim.reactor_heat, max_decimals=3, min_decimals=3) if sim.reactor_heat else '0'}/"
            f"{format_number_with_suffix(sim.max_reactor_heat, max_decimals=3)} "
            f"({heat_sign}{format_number_with_suffix(heat_delta, min_decimals=1)}/t)"
        )
        heat_max_w = layout.heat_bar_x + layout.bar_width - text_x - 4
        heat_font = _fit_font_size(heat_label, heat_max_w, 16)
        draw_text(
            heat_label,
            text_x,
            layout.heat_bar_y + 8,
            heat_font,
            Color(220, 220, 220, 255),
        )

        # Power bar (RE: fill = stored_power / maxPower, clamped 0..1)
        power_fill = 0.0
        if sim.max_reactor_power > 0:
            power_fill = min(1.0, max(0.0, sim.stored_power / sim.max_reactor_power))
        draw_rectangle(
            layout.power_bar_x,
            layout.power_bar_y,
            int(layout.bar_width * power_fill),
            layout.bar_height,
            Color(80, 200, 255, 200),
        )
        # Power icon + label
        icon_x = layout.power_bar_x + 4
        icon_y = layout.power_bar_y + 5
        text_x = icon_x
        if self.power_icon is not None:
            draw_texture_ex(self.power_icon, Vector2(icon_x, icon_y), 0.0, 1.0, Color(255, 255, 255, 255))
            text_x += self.power_icon.width + 6
        power_delta = sim.last_power_change
        power_sign = "+" if power_delta >= 0 else ""
        power_label = (
            f"{format_number_with_suffix(sim.stored_power, max_decimals=3, isInteger=True)}/"
            f"{format_number_with_suffix(sim.max_reactor_power, max_decimals=3, isInteger=True)} "
            f"({power_sign}{format_number_with_suffix(power_delta, min_decimals=0)}/t)"
        )
        power_max_w = layout.power_bar_x + layout.bar_width - text_x - 4
        power_font = _fit_font_size(power_label, power_max_w, 16)
        draw_text(
            power_label,
            text_x,
            layout.power_bar_y + 8,
            power_font,
            Color(220, 220, 220, 255),
        )

        # Cash display (with EP in upgrade/prestige views)
        if sim.view_mode in ("upgrades", "prestige"):
            money_text = (
                f"${format_number_with_suffix(sim.store.money)}"
                f"  EP: {format_number_with_suffix(sim.store.exotic_particles)}"
                f" / {format_number_with_suffix(sim.store.total_exotic_particles)}"
            )
        else:
            money_text = f"${format_number_with_suffix(sim.store.money)}"
        font_size = _fit_font_size(money_text, layout.cash_w - 12, 16)
        text_width = _measure(money_text, font_size)
        money_x = layout.cash_x + max(0, (layout.cash_w - text_width) // 2)
        draw_text(
            money_text,
            money_x,
            layout.cash_y + 10,
            font_size,
            Color(230, 230, 230, 255),
        )

        # Vent Heat button (RE: "-{ventAmount} Heat (-{ventRate} per tick)")
        vent_amt = format_number_with_suffix(sim.manual_vent_amount, max_decimals=2)
        vent_rate = format_number_with_suffix(sim.auto_vent_rate_per_tick(), max_decimals=2)
        vent_cap = format_number_with_suffix(sim.preview_active_dissipation, max_decimals=3)
        label = f"-{vent_amt} Heat (cap {vent_cap}/t)"
        
        self.draw_button(layout.vent_x, layout.vent_y, pressed_vent, hover_vent, label, 3)

        # Sell All Power / Scrounge button
        # RE: "Sell All Power: +{power} $ (+{autoSellRate} $ per tick)"
        # or "Scrounge for cash (+1$)" when money+power < 10
        if sim.can_scrounge():
            label = "Scrounge for cash (+1$)"
        else:
            power_str = format_number_with_suffix(sim.stored_power, max_decimals=2)
            rate_str = format_number_with_suffix(sim.auto_sell_rate_per_tick(), max_decimals=2)
            label = f"+{power_str}$ (+{rate_str}$/t)"

        self.draw_button(layout.sell_x, layout.sell_y, pressed_sell, hover_sell, label, 3)

        # Stats panel is hidden until we wire the real stats page UI.
        new_selected, hovered = self.draw_store(sim, layout, mouse_x, mouse_y, mouse_pressed)
        if new_selected is not None:
            sim.selected_component_index = new_selected
            self.cancel_blueprint_modes()
        if hovered is not None:
            sim.hover_component = hovered
            sim.hover_placed_component = None  # shop hover overrides grid hover
        self.draw_component_info(sim, layout, mouse_x, mouse_y, mouse_pressed)
        # Blueprint save selection box, clipped to the grid viewport
        if sim.view_mode == "reactor" and self.blueprint_selecting and sim.grid is not None:
            g = sim.grid
            begin_scissor_mode(g.origin_x, g.origin_y, g.viewport_w, g.viewport_h)
            self.draw_blueprint_selection(sim)
            end_scissor_mode()
        # Blueprint "can't place" outline: drawn exactly like the selection box
        # (over the grid frame, clipped to the grid viewport)
        if sim.view_mode == "reactor" and self._bp_force_outline is not None and sim.grid is not None:
            g = sim.grid
            begin_scissor_mode(g.origin_x, g.origin_y, g.viewport_w, g.viewport_h)
            self._draw_force_outline()
            end_scissor_mode()
        self._bp_force_outline = None

    def draw_store(
        self,
        sim: Simulation,
        layout: Layout,
        mouse_x: float,
        mouse_y: float,
        mouse_pressed: bool,
    ) -> tuple[Optional[int], Optional[ComponentTypeStats]]:
        tab_slots = self.store_tab_slots(layout)
        if tab_slots:
            tab_textures = [
                (self.store_tab_power, self.store_tab_power_hover, self.store_tab_power_pressed),
                (self.store_tab_heat, self.store_tab_heat_hover, self.store_tab_heat_pressed),
                (self.store_tab_experimental, self.store_tab_experimental_hover, self.store_tab_experimental_pressed),
                (self.store_tab_arcane, self.store_tab_arcane_hover, self.store_tab_arcane_pressed),
            ]
            for idx, slot in enumerate(tab_slots):
                if idx >= len(tab_textures):
                    break
                base, hover, pressed = tab_textures[idx]
                if base is None:
                    continue
                x, y, slot_w, slot_h = slot
                hovered = x <= mouse_x <= x + slot_w and y <= mouse_y <= y + slot_h
                selected = idx == sim.shop_page
                locked = sim.shop_page_locked(idx)
                tex = base
                if locked:
                    tex = self.store_block
                elif selected and pressed is not None:
                    tex = pressed
                elif hovered and hover is not None:
                    tex = hover
                tint = Color(255, 255, 255, 255)
                draw_texture_ex(tex, Vector2(x, y), 0.0, 1.0, tint)
                if hovered and mouse_pressed and not locked:
                    if sim.shop_page != idx:
                        sim.selected_component_index = -1
                    sim.shop_page = idx

        shop_components = sim.shop_components_for_page()
        if not shop_components:
            return None, None

        selected_index = None
        hovered_component = None
        slots = self.store_item_slots(layout, shop_components)
        for idx, (comp, rect) in enumerate(slots):
            x, y, slot_w, slot_h = rect
            hovered = x <= mouse_x <= x + slot_w and y <= mouse_y <= y + slot_h

            if comp.sprite_name:
                # Icon drawing happens in main for consistency with texture cache.
                pass

            if hovered:
                hovered_component = comp
            # RE: unnamed_function_10560 (line 396749) — only selectable
            # if cost <= money
            if hovered and mouse_pressed and comp.cost <= sim.store.money:
                selected_index = idx

        return selected_index, hovered_component

    def store_tab_slots(self, layout: Layout) -> list[tuple[int, int, int, int]]:
        if layout.store_area_w <= 0 or layout.store_area_h <= 0:
            return []
        slot_w = 30
        slot_h = 28
        cols = 4
        gap_x = (layout.store_area_w - cols * slot_w) / max(1, cols + 1)
        start_x = layout.store_area_x + gap_x
        y = layout.store_area_y + layout.store_tab_offset_y + (layout.store_row_h - slot_h) // 2
        slots: list[tuple[int, int, int, int]] = []
        for col in range(cols):
            x = start_x + col * (slot_w + gap_x)
            slots.append((int(x), int(y), slot_w, slot_h))
        return slots

    def store_item_slots(
        self, layout: Layout, components: list[ComponentTypeStats]
    ) -> list[tuple[ComponentTypeStats, tuple[int, int, int, int]]]:
        if not components:
            return []

        cols = 5
        slot_w = layout.store_area_w / cols
        slot_h = layout.store_row_h
        start_x = layout.store_area_x
        row_h = layout.store_row_h
        sep_h = layout.store_sep_h
        rows = max(1, int((layout.store_area_h + sep_h) // (row_h + sep_h)))
        max_row = max(0, rows - 2)

        slots: list[tuple[ComponentTypeStats, tuple[int, int, int, int]]] = []
        for comp in components:
            row = min(max(comp.shop_row, 0), max_row)
            col = min(max(comp.shop_col, 0), cols - 1)
            x = start_x + col * slot_w
            y = layout.store_area_y + (row + 1) * (row_h + sep_h) + (row_h - slot_h) // 2
            slots.append((comp, (int(x), int(y), int(slot_w), int(slot_h))))
        return slots

    def draw_component_info(
        self,
        sim: Simulation,
        layout: Layout,
        mouse_x: float = -1.0,
        mouse_y: float = -1.0,
        mouse_pressed: bool = False,
    ) -> None:
        """Draw the top info banner.  Background always visible; text slots
        are filled only when a component is hovered (RE: unnamed_function_10411).

        Panel layout (6 text slots):
          [Slot 5: Power Per Tick]            [Slot 4: Heat Per Tick]
          (top-left)                           (top-right)

                       [Slot 0: Title]
                     [Slot 1: Description]

          [Slot 2: Cost/Sells for]        [Slot 3: Heat/Durability]
          (bottom-left)                    (bottom-right)
        """
        # In upgrade/prestige views, _draw_upgrade_panel already handles
        # the top banner — skip here to avoid overwriting upgrade hover info.
        if sim.view_mode != "reactor":
            return

        panel_x = layout.top_panel_x
        panel_y = layout.top_panel_y
        panel_w = layout.top_panel_w
        panel_h = layout.top_panel_h
        margin = 20
        font_sm = 10
        font_title = 16

        # Banner background is always drawn
        if self.top_banner is not None:
            draw_texture_ex(
                self.top_banner,
                Vector2(panel_x, panel_y),
                0.0,
                1.0,
                Color(255, 255, 255, 255),
            )

        comp = sim.hover_component
        # Blueprint modes keep the banner on the blueprint controls, so hovering a
        # component doesn't swap in its info while saving, placing or deleting.
        if (
            comp is None
            or self.blueprint_selecting
            or self.blueprint_placing
            or self.blueprint_confirm_delete
        ):
            self.draw_blueprint_panel(sim, layout, mouse_x, mouse_y, mouse_pressed)
            return

        placed = sim.hover_placed_component
        text_color = Color(230, 230, 230, 255)

        # Determine which corner slots are active (fuel cells on grid only)
        has_per_tick = (
            placed is not None
            and not placed.depleted
            and comp.pulses_produced > 0
        )

        # ── Slot 5: Power Per Tick — top-left ──
        top_row_y = panel_y + 20
        if has_per_tick:
            ppt = f"Power Per Tick: {format_number_with_suffix(placed.last_power)}"
            draw_text(ppt, panel_x + margin, top_row_y, font_sm, text_color)

        # ── Slot 4: Heat Per Tick — top-right ──
        # Right boundary is left of pause/replace buttons to avoid overlap.
        right_edge = layout.pause_x - margin
        if has_per_tick:
            hpt = f"Heat Per Tick: {format_number_with_suffix(placed.last_heat)}"
            hw = _measure(hpt, font_sm)
            draw_text(hpt, right_edge - hw, top_row_y, font_sm, text_color)

        # ── Slot 0: Title — centered ──
        title = comp.display_name or comp.name
        if placed is not None and placed.depleted:
            title = f"Depleted {title}"
        # Center within the area left of pause/replace buttons
        usable_w = right_edge - panel_x - margin
        title_w = _measure(title, font_title)
        title_x = panel_x + max(0, (usable_w - title_w) // 2 + margin)
        title_y = panel_y + 20
        draw_text(title, title_x, title_y, font_title, text_color)

        # ── Slot 1: Description — centered, wrapped, below title ──
        description = _format_component_description(comp, sim)
        if placed is not None and placed.depleted:
            description = "This cell has run out of fuel and is now inert. Right-click to remove it."
        # Usable width stops before the pause/replace buttons
        desc_max_w = right_edge - panel_x - margin
        desc_lines = _wrap_text(description, desc_max_w, font_sm) if description else []
        y = panel_y + (40 + panel_h - margin - 14*len(desc_lines)) // 2
        for line in desc_lines:
            line_w = _measure(line, font_sm)
            line_x = panel_x + max(0, (desc_max_w - line_w) // 2 + margin)
            draw_text(line, line_x, y, font_sm, text_color, light = True)
            y += 14

        # Throughput warning: outlets are the bottleneck relative to vent capacity.
        show_outlet_warning = (
            placed is not None
            and comp.type_of_component == "Outlet"
            and sim.is_outlet_bottleneck(placed)
        )
        if show_outlet_warning:
            warning_text = (
                "Warning icon: this outlet is a throughput bottleneck for an adjacent vent."
            )
            warning_font = 11
            warning_color = Color(255, 220, 90, 255)
            icon_x = panel_x + margin
            icon_y = y + 2
            self.draw_warning_badge(icon_x, icon_y, size=10)

            wy = y
            warn_lines = _wrap_text(warning_text, max(20, desc_max_w - 18), warning_font)
            for line in warn_lines:
                draw_text(line, icon_x + 14, wy, warning_font, warning_color)
                wy += 13

        # ── Slot 2: Cost / Sells for — bottom-left ──
        if placed is not None:
            slot2_text = _format_sell_line(placed)
        else:
            slot2_text = _format_cost_line(comp, sim.get_component_cost(comp))
        if slot2_text:
            draw_text(slot2_text, panel_x + margin, panel_y + panel_h - margin, font_sm, text_color)

        # ── Slot 3: Heat OR Durability — bottom-right ──
        # Only shown for non-depleted grid components (RE: line 388719)
        if placed is not None and not placed.depleted:
            slot3_text = ""
            # Heat (written first, may be overwritten by durability)
            if comp.heat_capacity > 0.0:
                eff_hc = sim.get_effective_heat_capacity(placed)
                slot3_text = (
                    f"Heat: {format_number_with_suffix(placed.heat)}"
                    f" / {format_number_with_suffix(eff_hc)}"
                )
            # Durability overwrites heat in the same slot (RE: line 388770)
            if comp.max_durability > 0.0:
                eff_dur = sim.get_effective_max_durability(placed)
                slot3_text = (
                    f"Durability: {format_number_with_suffix(placed.durability)}"
                    f" / {format_number_with_suffix(eff_dur)}"
                )
            if slot3_text:
                sw = _measure(slot3_text, font_sm)
                draw_text(
                    slot3_text,
                    right_edge - sw,
                    panel_y + panel_h - 20,
                    font_sm,
                    text_color,
                )

    def draw_upgrade_grid(
        self,
        sim: Simulation,
        layout: Layout,
        mouse_x: float,
        mouse_y: float,
        mouse_down: bool,
        mouse_released: bool,
    ) -> None:
        """Draw the upgrade icon grid and handle hover/click.

        Shown when sim.view_mode == 'upgrades' or 'prestige'.
        Replaces the reactor grid area.
        Layout matches the original game's grouped arrangement.
        """
        mgr = sim.upgrade_manager
        if not mgr.upgrades:
            return

        is_prestige = sim.view_mode == "prestige"
        positions = _PRESTIGE_GRID_POSITIONS if is_prestige else _UPGRADE_GRID_POSITIONS

        # Use actual icon button texture dimensions for spacing
        if self.icon_button is not None:
            cell_w = self.icon_button.width
            cell_h = self.icon_button.height
        else:
            cell_w = layout.upgrade_cell_size
            cell_h = layout.upgrade_cell_size
        gap = layout.upgrade_gap
        ox = layout.upgrade_grid_x + 5
        oy = layout.upgrade_grid_y + 6

        hovered_upgrade: Optional[UpgradeType] = None

        for u in mgr.upgrades:
            if u.index not in positions:
                continue
            row, col = positions[u.index]
            x = ox + col * (cell_w + gap)
            y = oy + row * (cell_h + gap)

            is_hover = x <= mouse_x <= x + cell_w and y <= mouse_y <= y + cell_h
            can_buy = mgr.can_purchase(u.index, sim.store.money, sim.store.exotic_particles)
            is_one_time_owned = u.cost_multiplier == 0.0 and u.level > 0

            # Pick background texture — no lock button, use dimmed tint instead
            if is_one_time_owned:
                tex = self.icon_button
            elif mouse_down and is_hover and can_buy:
                tex = self.icon_button_pressed
                y += 2
            elif is_hover and can_buy:
                tex = self.icon_button_hover
            else:
                tex = self.icon_button

            can_afford = (is_one_time_owned and u.level) or  can_buy

            # Bright if purchasable, dim otherwise
            if can_afford:
                tint = Color(255, 255, 255, 255)
            else:
                tint = Color(55, 55, 55, 255)

            if tex is not None:
                draw_texture_ex(tex, Vector2(x, y), 0.0, 1.0, tint)
            else:
                bg_color = Color(40, 50, 70, 255) if can_buy else Color(30, 30, 40, 255)
                draw_rectangle(x, y, cell_w, cell_h, bg_color)
                draw_rectangle_lines(x, y, cell_w, cell_h, Color(80, 90, 110, 255))

            # Draw upgrade icon sprite centered on button
            sprites = self.upgrade_sprites
            if sprites:
                icon_tex = sprites.get(u.icon)
                if icon_tex is not None:
                    ix = x + (cell_w - icon_tex.width) / 2
                    iy = y + (cell_h - icon_tex.height) / 2 - 3 
                    draw_texture_ex(
                        icon_tex,
                        Vector2(ix, iy),
                        0.0,
                        1.0,
                        tint
                    )

                # Category overlay in bottom-right corner
                cat_tex = sprites.get(u.category)
                if cat_tex is not None:
                    if u.level < 7:
                        cat_tint = [
                            Color(255, 255, 255, 255),
                            Color(0, 255, 0, 255),
                            Color(255, 182, 53, 255),
                            Color(255, 182, 53, 255),
                            Color(153, 153, 153, 255),
                            Color(241, 227, 44, 255),
                            Color(160, 255, 250, 255)
                        ][u.level]
                    else:
                        cat_tint = Color(121, 0, 188, 255)
                    if not can_afford:
                        cat_tint = Color(cat_tint[0] // 4, cat_tint[1] // 4, cat_tint[2] // 4, 255)
                    cx = x + cell_w - cat_tex.width - 2
                    cy = y + cell_h - cat_tex.height - 2
                    draw_texture_ex(cat_tex, Vector2(cx, cy), 0.0, 1.0, cat_tint)

            # Level indicator (bottom-left corner, above category overlay)
            if not is_one_time_owned and u.level > 0:
                lvl_text = str(u.level)
                draw_text(lvl_text, x + 4, y + cell_h - 14, 10, Color(200, 255, 200, 255))

            # Hover tracking
            if is_hover:
                hovered_upgrade = u

            # Click to purchase
            if is_hover and mouse_released and can_buy:
                sim.store.money, sim.store.exotic_particles = mgr.purchase(
                    u.index, sim.store.money, sim.store.exotic_particles
                )
                sim.recompute_max_capacities()
                # Subspace Expansion (upgrade 50): resize grid on purchase
                if u.index == 50:
                    sim.resize_grid_for_subspace()

        # Draw the top panel — always draw banner background, add upgrade
        # info text when hovering.  This replaces draw_component_info for
        # upgrade/prestige views.
        self._draw_upgrade_panel(sim, layout, hovered_upgrade)

    def _draw_upgrade_panel(self, sim: Simulation, layout: Layout, u: UpgradeType | None) -> None:
        """Draw top banner panel for upgrade/prestige views.

        Always draws the banner background.  When *u* is not None (an upgrade
        is hovered), also renders the upgrade's title, description and cost.
        """
        panel_x = layout.top_panel_x
        panel_y = layout.top_panel_y
        panel_w = layout.top_panel_w
        panel_h = layout.top_panel_h
        margin = 20
        font_sm = 10
        font_title = 16

        # Banner background — always drawn so the panel area isn't empty
        if self.top_banner is not None:
            draw_texture_ex(
                self.top_banner,
                Vector2(panel_x, panel_y),
                0.0,
                1.0,
                Color(255, 255, 255, 255),
            )

        if u is None:
            return

        mgr = sim.upgrade_manager
        text_color = Color(230, 230, 230, 255)

        # Title — constrained to avoid overlapping pause/replace buttons
        right_edge = layout.pause_x - margin
        usable_w = right_edge - panel_x - margin
        title = mgr.display_name(u.index)
        if u.level > 0 and u.cost_multiplier != 0.0:
            title = f"{title} (Lv. {u.level})"
        title_w = _measure(title, font_title)
        title_x = panel_x + max(0, (usable_w - title_w) // 2 + margin)
        draw_text(title, title_x, panel_y + 20, font_title, text_color)

        # Description
        desc_lines = _wrap_text(u.description, usable_w, font_sm)
        y = panel_y + (40 + panel_h - margin - 14*len(desc_lines)) // 2
        for line in desc_lines:
            line_w = _measure(line, font_sm)
            line_x = panel_x + max(0, (usable_w - line_w) // 2 + margin)
            draw_text(line, line_x, y, font_sm, text_color, light=True)
            y += 14

        # Cost line (bottom-left)
        is_one_time_owned = u.cost_multiplier == 0.0 and u.level > 0
        if is_one_time_owned:
            cost_text = "PURCHASED"
        else:
            cost = mgr.get_cost(u.index)
            currency = "EP" if u.is_prestige else "$"
            cost_text = f"Cost: {format_number_with_suffix(cost)} {currency}"
        draw_text(cost_text, panel_x + margin, panel_y + panel_h - margin, font_sm, text_color)

    def draw_statistics_panel(self, sim: Simulation, layout: Layout) -> None:
        """Draw the Statistics panel in the grid content area."""
        panel_x = layout.top_panel_x
        panel_y = layout.top_panel_y
        panel_w = layout.top_panel_w
        panel_h = layout.top_panel_h
        text_color = Color(230, 230, 230, 255)

        if self.top_banner is not None:
            draw_texture_ex(
                self.top_banner,
                Vector2(panel_x, panel_y),
                0.0, 1.0,
                Color(255, 255, 255, 255),
            )

        # Content area
        content_x = layout.upgrade_grid_x
        content_y = layout.upgrade_grid_y + 4
        content_w = panel_w - (content_x - panel_x) * 2
        font_title = 14
        font_sm = 11
        line_h = 14

        # Title
        title = "Statistics:"
        tw = _measure(title, font_title)
        draw_text(title, content_x + (content_w - tw) // 2, content_y, font_title, text_color)
        y = content_y + 24

        # Stat lines
        fmt = format_number_with_suffix
        lines = [
            f"Build Version: 1",
            "",
            f"Current Money: {fmt(sim.store.money)}",
            f"Total Money: {fmt(sim.store.total_money)}",
            f"Money earned this game: {fmt(sim.store.money_earned_this_game)}",
            "",
            f"Current Power: {fmt(sim.stored_power)}",
            f"Total Power produced: {fmt(sim.store.total_power_produced)}",
            f"Power produced this game: {fmt(sim.store.power_produced_this_game)}",
            "",
            f"Current Reactor Heat: {fmt(sim.reactor_heat)}",
            f"Total Heat dissipated: {fmt(sim.store.total_heat_dissipated)}",
            f"Heat dissipated this game: {fmt(sim.store.heat_dissipated_this_game)}",
            f"Vent dissipation cap: {fmt(sim.preview_vent_capacity, max_decimals=4)}/t",
            f"Outlet transfer cap: {fmt(sim.preview_outlet_capacity, max_decimals=4)}/t",
            f"Outlet + vent cap: {fmt(sim.preview_vent_capacity + sim.preview_outlet_capacity, max_decimals=4)}/t",
            "",
            f"Current Exotic Particles: {fmt(sim.store.exotic_particles)}",
            f"Total Exotic Particles: {fmt(sim.store.total_exotic_particles)}",
            f"Exotic Particles earned from next prestige: {fmt(sim.calculate_prestige_ep())}",
        ]

        for line in lines:
            if line == "":
                y += line_h // 2
                continue
            line_font = _fit_font_size(line, content_w - 8, font_sm, min_size=9)
            wrapped = _wrap_text(line, content_w - 8, line_font)
            for wline in wrapped:
                lw = _measure(wline, line_font)
                draw_text(wline, content_x + (content_w - lw) // 2, y, line_font, text_color)
                y += line_h

    def draw_options_panel(
        self,
        sim: Simulation,
        layout: Layout,
        mouse_x: float,
        mouse_y: float,
        mouse_down: bool,
        mouse_released: bool,
        dt: float,
    ) -> None:
        """Draw the Options panel in the grid content area."""
        panel_x = layout.top_panel_x
        panel_y = layout.top_panel_y
        panel_w = layout.top_panel_w
        panel_h = layout.top_panel_h
        text_color = Color(220, 220, 220, 255)

        if self.top_banner is not None:
            draw_texture_ex(
                self.top_banner,
                Vector2(panel_x, panel_y),
                0.0, 1.0,
                Color(255, 255, 255, 255),
            )

        content_x = layout.upgrade_grid_x
        content_y = layout.upgrade_grid_y + 4
        content_w = panel_w - (content_x - panel_x) * 2
        font_sm = 12
        line_h = 16

        # Prestige button — 3-phase state machine (RE: fn 10493/10490)
        # Phase A: Normal → Phase B: Confirm → Phase C: Refund window
        if sim.prestige_can_refund:
            # Phase C: Refund window (post-prestige, one-shot)
            prestige_label = "Refund prestige upgrades?"
            can_click = True
            bg_normal = Color(40, 100, 80, 255)
            bg_hover = Color(60, 130, 100, 255)
            border_color = Color(70, 140, 110, 255)
        elif sim.prestige_confirming:
            # Phase B: Confirmation
            prestige_label = "Click again to confirm (Will restart game)"
            can_click = True
            bg_normal = Color(140, 90, 30, 255)
            bg_hover = Color(180, 110, 40, 255)
            border_color = Color(190, 130, 50, 255)
        else:
            # Phase A: Normal
            ep_gain = sim.calculate_prestige_ep()
            prestige_label = f"Prestige for {format_number_with_suffix(ep_gain)} exotic particles."
            can_click = True
            bg_normal = Color(70, 50, 100, 255)
            bg_hover = Color(100, 70, 140, 255)
            border_color = Color(100, 80, 130, 255)

        pbtn_w = self.btn_big.width
        pbtn_h = self.btn_big.height
        pbtn_x = content_x + (content_w - pbtn_w) // 2
        pbtn_y = content_y
        hover_prestige_btn = (pbtn_x <= mouse_x <= pbtn_x + pbtn_w and
                              pbtn_y <= mouse_y <= pbtn_y + pbtn_h)
        self.draw_button(pbtn_x, pbtn_y, hover_prestige_btn and mouse_down, hover_prestige_btn, prestige_label, 3)

        if hover_prestige_btn and mouse_released and can_click:
            if sim.prestige_can_refund:
                sim.refund_prestige_upgrades()
            elif sim.prestige_confirming:
                sim.do_prestige()
            else:
                sim.prestige_confirming = True

        y = content_y + 40
        desc = (
            "When you 'prestige', you will lose all components, money, power, heat, and upgrades. "
            "In exchange, you'll get exotic particles, which will let you get powerful, permanent "
            "upgrades. It is recommended you wait until you can get 51 particles before your first prestige."
        )
        desc_lines = _wrap_text(desc, content_w * 0.8, font_sm)
        for line in desc_lines:
            lw = _measure(line, font_sm)
            draw_text(line, content_x + (content_w - lw) // 2, y, font_sm, text_color)
            y += line_h

        # Reset Game button
        y += line_h + 150
        btn_w = self.btn_big.width
        btn_h = self.btn_big.height
        btn_x = content_x + (content_w - pbtn_w) // 2
        btn_y = y

        hover_reset = (btn_x <= mouse_x <= btn_x + btn_w and
                       btn_y <= mouse_y <= btn_y + btn_h)

        # Decrement confirm timer
        if sim.reset_confirm_timer > 0:
            sim.reset_confirm_timer -= dt

        if hover_reset and mouse_released:
            if sim.reset_confirm_timer > 0:
                # Second click within timer — perform reset
                sim.reset_game()
                sim.reset_confirm_timer = 0.0
            else:
                # First click — start confirmation
                sim.reset_confirm_timer = 3.0

        # Draw button
        if sim.reset_confirm_timer > 0:
            label = "Click again to confirm"
        else:
            label = "Reset Game"

        self.draw_button(btn_x, btn_y, hover_reset and mouse_down, hover_reset, label, 3)

        # ── Export / Import buttons ──────────────────────────────────
        if self.save_dir is not None:
            from game.save import export_save_old, export_save_new, import_save_from_file

            ei_y = btn_y + btn_h + 12
            ei_btn_w = self.btn_med.width
            ei_btn_h = self.btn_med.height
            gap = 10
            total_w = ei_btn_w * 2 + gap
            ei_start_x = content_x + (content_w - total_w) // 2

            # Export Old button
            old_x = ei_start_x
            hover_old = (old_x <= mouse_x <= old_x + ei_btn_w and
                         ei_y <= mouse_y <= ei_y + ei_btn_h)
            self.draw_button(old_x, ei_y, hover_old and mouse_down, hover_old, "Export Old", 2)

            if hover_old and mouse_released:
                if _WEB:
                    export_save_old(sim)
                else:
                    export_save_old(sim, self.save_dir / "save_export_old.txt")

            # Export New button
            new_x = ei_start_x + ei_btn_w + gap
            hover_new = (new_x <= mouse_x <= new_x + ei_btn_w and
                         ei_y <= mouse_y <= ei_y + ei_btn_h)
            self.draw_button(new_x, ei_y, hover_new and mouse_down, hover_new, "Export New", 2)

            if hover_new and mouse_released:
                if _WEB:
                    export_save_new(sim)
                else:
                    export_save_new(sim, self.save_dir / "save_export_new.txt")

            # Import button (second row)
            im_y = ei_y + ei_btn_h + 8
            im_x = content_x + (content_w - ei_btn_w) // 2
            hover_import = (im_x <= mouse_x <= im_x + ei_btn_w and
                            im_y <= mouse_y <= im_y + ei_btn_h)
            self.draw_button(im_x, im_y, hover_import and mouse_down, hover_import, "Import", 2)

            if hover_import and mouse_released:
                import_save_from_file(sim)

    def draw_help_panel(self, sim: Simulation, layout: Layout, wheel_move: float = 0.0, mouse_x: float = 0.0, mouse_y: float = 0.0, mouse_down: bool = False) -> None:
        """Draw a rich, scrollable Help panel in the grid content area."""
        panel_x = layout.top_panel_x
        panel_y = layout.top_panel_y
        panel_w = layout.top_panel_w
        panel_h = layout.top_panel_h

        if self.top_banner is not None:
            draw_texture_ex(
                self.top_banner,
                Vector2(panel_x, panel_y),
                0.0, 1.0,
                Color(255, 255, 255, 255),
            )

        # Content region sits below the top banner, inside the grid frame
        content_x = layout.upgrade_grid_x
        content_y = layout.upgrade_grid_y
        content_w = panel_w - (content_x - panel_x) * 2
        content_h = layout.window_height - content_y - (layout.window_height - layout.grid_frame_y - 513)

        # Build content items
        items, total_height = _build_help_content(content_w)

        # Scroll
        max_scroll = max(0.0, total_height - content_h)
        self.help_scroll_y -= wheel_move * 30

        # Drag scrolling
        if mouse_down:
            if self.help_drag_active:
                delta = self.help_drag_last_y - mouse_y
                self.help_scroll_y += delta
            else:
                in_content = (content_x <= mouse_x <= content_x + content_w and
                              content_y <= mouse_y <= content_y + content_h)
                if in_content:
                    self.help_drag_active = True
            self.help_drag_last_y = mouse_y
        else:
            self.help_drag_active = False

        self.help_scroll_y = max(0.0, min(self.help_scroll_y, max_scroll))

        # Render inside scissor region
        begin_scissor_mode(content_x, content_y, content_w, content_h)

        header_color = Color(245, 200, 70, 255)
        text_color = Color(210, 210, 220, 255)
        divider_color = Color(80, 80, 100, 180)

        for item in items:
            tag = item[0]
            item_y = item[1] - self.help_scroll_y + content_y

            if tag == _HELP_HEADER:
                _, y_off, text = item
                if item_y + 20 < content_y or item_y > content_y + content_h:
                    continue
                draw_text(text, content_x + 4, int(item_y), 16, header_color)

            elif tag == _HELP_TEXT:
                _, y_off, text = item
                if item_y + 14 < content_y or item_y > content_y + content_h:
                    continue
                draw_text(text, content_x + 4, int(item_y), 12, text_color)

            elif tag == _HELP_SPRITE_LINE:
                _, y_off, sprite_name, text = item
                if item_y + 26 < content_y or item_y > content_y + content_h:
                    continue
                sprite_size = 24
                tex = self.component_sprites.get(sprite_name) if self.component_sprites else None
                text_x_offset = sprite_size + 6
                if tex is not None:
                    scale = sprite_size / max(1, max(tex.width, tex.height))
                    dw = tex.width * scale
                    dh = tex.height * scale
                    sx = content_x + 4
                    sy = item_y + 1
                    draw_texture_pro(
                        tex,
                        Rectangle(0, 0, tex.width, tex.height),
                        Rectangle(sx, sy, dw, dh),
                        Vector2(0, 0), 0.0, Color(255, 255, 255, 255),
                    )
                else:
                    text_x_offset = 4
                # Draw wrapped text lines to the right of the sprite
                wrap_w = content_w - text_x_offset - 8
                lines = _wrap_text(text, wrap_w, 12)
                ly = item_y + 2
                for line in lines:
                    draw_text(line, content_x + text_x_offset, int(ly), 12, text_color)
                    ly += 14

            elif tag == _HELP_GRID:
                _, y_off, rows, height = item
                if item_y + height < content_y or item_y > content_y + content_h:
                    continue
                cell = 26
                gap = 2
                grid_w = len(rows[0]) * (cell + gap) - gap if rows else 0
                gx_start = content_x + (content_w - grid_w) // 2
                sprites = self.component_sprites
                for ri, row in enumerate(rows):
                    for ci, sname in enumerate(row):
                        if sname is None:
                            continue
                        tex = sprites.get(sname) if sprites else None
                        if tex is None:
                            continue
                        cx = gx_start + ci * (cell + gap)
                        cy = int(item_y) + ri * (cell + gap)
                        sc = cell / max(1, max(tex.width, tex.height))
                        dw = tex.width * sc
                        dh = tex.height * sc
                        ox = (cell - dw) * 0.5
                        oy = (cell - dh) * 0.5
                        draw_texture_pro(
                            tex,
                            Rectangle(0, 0, tex.width, tex.height),
                            Rectangle(cx + ox, cy + oy, dw, dh),
                            Vector2(0, 0), 0.0, Color(255, 255, 255, 255),
                        )

            elif tag == _HELP_SPRITE_ROW:
                _, y_off, sprite_list, height = item
                if item_y + height < content_y or item_y > content_y + content_h:
                    continue
                icon_sz = 28
                gap = 6
                total_w = len(sprite_list) * (icon_sz + gap) - gap
                rx = content_x + (content_w - total_w) // 2
                sprites = self.component_sprites
                for si, sname in enumerate(sprite_list):
                    tex = sprites.get(sname) if sprites else None
                    if tex is None:
                        continue
                    ix = rx + si * (icon_sz + gap)
                    sc = icon_sz / max(1, max(tex.width, tex.height))
                    dw = tex.width * sc
                    dh = tex.height * sc
                    ox = (icon_sz - dw) * 0.5
                    oy = (icon_sz - dh) * 0.5
                    draw_texture_pro(
                        tex,
                        Rectangle(0, 0, tex.width, tex.height),
                        Rectangle(ix + ox, int(item_y) + oy, dw, dh),
                        Vector2(0, 0), 0.0, Color(255, 255, 255, 255),
                    )

            elif tag == _HELP_DIVIDER:
                _, y_off = item
                if item_y + 4 < content_y or item_y > content_y + content_h:
                    continue
                draw_rectangle(content_x + 8, int(item_y + 3), content_w - 16, 1, divider_color)

            # _HELP_SPACER: just empty space, nothing to draw

        end_scissor_mode()

        # Scroll indicator (thin 4px track on right edge)
        if max_scroll > 0:
            track_x = content_x + content_w - 5
            track_y = content_y + 2
            track_h = content_h - 4
            draw_rectangle(track_x, track_y, 4, track_h, Color(40, 40, 50, 160))
            thumb_ratio = content_h / max(1, total_height)
            thumb_h = max(16, int(track_h * thumb_ratio))
            scroll_ratio = self.help_scroll_y / max(1.0, max_scroll)
            thumb_y = track_y + int((track_h - thumb_h) * scroll_ratio)
            draw_rectangle(track_x, thumb_y, 4, thumb_h, Color(160, 160, 180, 200))


# ── Help panel content types ─────────────────────────────────────────
_HELP_HEADER = 0
_HELP_TEXT = 1
_HELP_SPRITE_LINE = 2
_HELP_DIVIDER = 3
_HELP_SPACER = 4
_HELP_GRID = 5
_HELP_SPRITE_ROW = 6


def _build_help_content(content_w: int) -> tuple[list, float]:
    """Build a list of tagged items with pre-computed y-offsets.

    Returns (items, total_height).
    """
    items: list = []
    y = 4.0

    def _header(text: str) -> None:
        nonlocal y
        items.append((_HELP_HEADER, y, text))
        y += 22

    def _text(text: str) -> None:
        nonlocal y
        lines = _wrap_text(text, content_w - 16, 12)
        for line in lines:
            items.append((_HELP_TEXT, y, line))
            y += 14
        y += 2

    def _sprite_line(sprite_name: str, text: str) -> None:
        nonlocal y
        sprite_text_w = content_w - 38
        lines = _wrap_text(text, sprite_text_w, 12)
        line_count = max(1, len(lines))
        height = max(26, line_count * 14 + 4)
        items.append((_HELP_SPRITE_LINE, y, sprite_name, text))
        y += height

    def _divider() -> None:
        nonlocal y
        items.append((_HELP_DIVIDER, y))
        y += 10

    def _spacer(h: float = 6) -> None:
        nonlocal y
        items.append((_HELP_SPACER, y))
        y += h

    def _grid(rows: list[list]) -> None:
        """Render a grid of sprites centered in the content area."""
        nonlocal y
        cell = 26
        gap = 2
        h = len(rows) * (cell + gap) - gap
        items.append((_HELP_GRID, y, rows, h))
        y += h + 4

    def _sprite_row(sprites: list[str]) -> None:
        """Render a horizontal row of sprites, centered."""
        nonlocal y
        h = 30
        items.append((_HELP_SPRITE_ROW, y, sprites, h))
        y += h + 2

    F = "Fuel1-1.png"
    V = "Vent1.png"
    O = "Outlet1.png"
    X = "Exchanger1.png"
    R = "Reflector1.png"
    I = "Inlet1.png"
    C = "Coolant1.png"
    K = "Capacitor1.png"
    P = "Plate1.png"

    # ══════════════════════════════════════════════════════════
    # Section 1: Controls
    # ══════════════════════════════════════════════════════════
    _header("Controls")
    _text(
        "Left-click a shop item to select it (green highlight), then "
        "left-click on the reactor grid to place it. Placing on an " 
        "occupied cell auto-sells the old component and places the " 
        "new one. Right-click a placed component to sell it."
    )
    _divider()
    _text(
        "Perpetual mode (top-right toggle): Automatically replace used cells (requires associated upgrade)"
    )
    _divider()
    _text(
        "Middle-click drag or scroll wheel to pan the grid. "
        "Press Space to pause/unpause the simulation."
    )
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 2: Fuel Cells
    # ══════════════════════════════════════════════════════════
    _header("Fuel Cells")
    _text(
        "Fuel cells produce power and heat. They come in three sizes:"
    )
    _sprite_line("Fuel1-1.png",
        "Single (1 core) - base output. Cheapest way to start.")
    _sprite_line("Fuel1-2.png",
        "Double (2 cores) - more pulses, more output per slot.")
    _sprite_line("Fuel1-4.png",
        "Quad (4 cores) - massive output, needs strong cooling.")
    _spacer(4)
    _text("There are 6 base fuel tiers with increasing stats:")
    _sprite_row([
        "Fuel1-1.png", "Fuel2-1.png", "Fuel3-1.png",
        "Fuel4-1.png", "Fuel5-1.png", "Fuel6-1.png",
    ])
    _text("And 5 experimental fuels unlocked via prestige:")
    _sprite_row([
        "Fuel7-1.png", "Fuel8-1.png", "Fuel9-1.png",
        "Fuel10-1.png", "Fuel11-1.png",
    ])
    _text(
        "Protium gains permanent power from each depleted cell. "
        "Kymium oscillates in a cosine wave. "
        "Stavrium pulses its entire row and column!"
    )
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 3: Pulse System
    # ══════════════════════════════════════════════════════════
    _header("Pulse System")
    _text(
        "Each fuel cell emits pulses to its 4 cardinal neighbors and "
        "itself. Pulses from multiple sources stack."
    )
    _spacer(2)
    _text("A lone fuel cell has 1 pulse (just itself):")
    _grid([
        [None, None, None],
        [None, F,    None],
        [None, None, None],
    ])
    _text("Two cells side by side - each gets 2 pulses:")
    _grid([
        [None, None, None, None],
        [None, F,    F,    None],
        [None, None, None, None],
    ])
    _text("A 3x3 block - center gets 5 pulses (1 self + 4 neighbors):")
    _grid([
        [F, F, F],
        [F, F, F],
        [F, F, F],
    ])
    _text(
        "This matters because of the heat formula!"
    )
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 4: Power & Heat Formulas
    # ══════════════════════════════════════════════════════════
    _header("Power & Heat Formulas")
    _text("Each tick, fuel cells calculate:")
    _text("  Power = pulses * energyPerPulse * upgrades")
    _text("  Heat  = pulses^2 * heatPerPulse / cellArea")
    _spacer(4)
    _text(
        "Power scales linearly with pulses, but heat scales with the "
        "SQUARE. A cell with 5 pulses makes 25x the heat of a lone "
        "cell! This is the core tension of reactor design."
    )
    _spacer(4)
    _text(
        "Heat from a fuel cell is split equally among cardinal "
        "neighbors that can hold heat. If none exist, all heat goes "
        "directly to the reactor hull."
    )
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 5: Heat Components
    # ══════════════════════════════════════════════════════════
    _header("Heat Components")
    _text(
        "If hull heat reaches max, 5% of overflow hits every component "
        "each tick. Components explode at their heat capacity. At 2x "
        "max hull heat, ALL components are destroyed (full meltdown)."
    )
    _spacer(4)
    _sprite_line("Vent1.png",
        "Vent - the only exit for heat. Dissipates its stored heat "
        "into the air each tick. Must be fed by outlets or fuel "
        "neighbors.")
    _text("Vent tiers (higher = faster dissipation):")
    _sprite_row([
        "Vent1.png", "Vent2.png", "Vent3.png",
        "Vent4.png", "Vent5.png",
    ])
    _spacer(4)
    _sprite_line("Outlet1.png",
        "Outlet - transfers heat FROM the reactor hull INTO adjacent "
        "components. Place next to dedicated vents, not fuel.")
    _text("Outlet tiers:")
    _sprite_row([
        "Outlet1.png", "Outlet2.png", "Outlet3.png",
        "Outlet4.png", "Outlet5.png",
    ])
    _spacer(4)
    _sprite_line("Inlet1.png",
        "Inlet - pulls heat FROM adjacent components INTO the hull. "
        "Rescues overheating components.")
    _text("Inlet tiers:")
    _sprite_row([
        "Inlet1.png", "Inlet2.png", "Inlet3.png",
        "Inlet4.png", "Inlet5.png",
    ])
    _spacer(4)
    _sprite_line("Exchanger1.png",
        "Exchanger - balances heat with each neighbor toward an equal "
        "fill ratio. Spreads heat from hot to cool components.")
    _text("Exchanger tiers:")
    _sprite_row([
        "Exchanger1.png", "Exchanger2.png", "Exchanger3.png",
        "Exchanger4.png", "Exchanger5.png",
    ])
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 6: The Heat Pipeline
    # ══════════════════════════════════════════════════════════
    _header("The Heat Pipeline")
    _text("Heat flows through your reactor in stages:")
    _spacer(2)
    _sprite_line("Fuel1-1.png", "1. Fuel cells GENERATE heat")
    _sprite_line("Exchanger1.png", "2. Exchangers SPREAD heat evenly")
    _sprite_line("Inlet1.png", "3. Inlets PULL component heat to hull")
    _sprite_line("Outlet1.png", "4. Outlets PUSH hull heat to vents")
    _sprite_line("Vent1.png", "5. Vents DISSIPATE heat to air")
    _spacer(4)
    _text("Example - direct vent cooling:")
    _grid([
        [None, V, None],
        [V,    F, V],
        [None, V, None],
    ])
    _text(
        "Fuel heat splits equally among 4 adjacent vents. Each vent "
        "dissipates its share to air. Simple and effective early on."
    )
    _spacer(4)
    _text("Example - separated cooling (outlets feed dedicated vents):")
    _grid([
        [V, O, V],
        [R, F, R],
        [V, O, V],
    ])
    _text(
        "Reflectors block direct heat absorption - all fuel heat goes "
        "to hull. Outlets push hull heat to corner vents. Those vents "
        "are NOT adjacent to fuel, so they only handle hull heat."
    )
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 7: Other Components
    # ══════════════════════════════════════════════════════════
    _header("Other Components")
    _sprite_line("Reflector1.png",
        "Reflector - gives +10% power to each adjacent fuel cell per "
        "upgrade level. Only boosts POWER, not heat. Loses durability "
        "from neighbor pulses. Thermally isolated.")
    _text("Reflector tiers:")
    _sprite_row([
        "Reflector1.png", "Reflector2.png", "Reflector3.png",
        "Reflector4.png", "Reflector5.png",
    ])
    _spacer(4)
    _sprite_line("Capacitor1.png",
        "Capacitor - adds to max power storage (base: 100). More "
        "storage = more power banked before selling.")
    _sprite_line("Plate1.png",
        "Plating - adds to max hull heat capacity (base: 1000). "
        "More headroom before overflow and meltdown.")
    _text("Capacitor and Plating tiers:")
    _sprite_row([
        "Capacitor1.png", "Capacitor2.png", "Capacitor3.png",
        "Capacitor4.png", "Capacitor5.png",
    ])
    _sprite_row([
        "Plate1.png", "Plate2.png", "Plate3.png",
        "Plate4.png", "Plate5.png",
    ])
    _spacer(4)
    _sprite_line("Coolant1.png",
        "Coolant - passive heat sink with high capacity. Absorbs heat "
        "from adjacent fuel. Relies on exchangers/inlets to drain.")
    _sprite_line("Coolant6.png",
        "Extreme Coolant (Tier 6) - absorbs 10% of heat from all "
        "components within distance 2, but its heat is permanently "
        "trapped. Cannot be drained by exchangers or inlets!")
    _text("Coolant tiers:")
    _sprite_row([
        "Coolant1.png", "Coolant2.png", "Coolant3.png",
        "Coolant4.png", "Coolant5.png", "Coolant6.png",
    ])
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 8: Selling & Money
    # ══════════════════════════════════════════════════════════
    _header("Selling & Money")
    _text(
        "Right-click to sell. Sell value depends on condition:")
    _text(
        "  sell = cost * (1 - heat/maxHeat)^2 * (dur/maxDur)^2")
    _text(
        "Fuel cells always sell for $0. Pristine components sell "
        "for full cost. Damaged ones sell for much less."
    )
    _spacer(4)
    _text(
        "Click 'Sell All Power' to convert stored power to money. "
        "Auto-sell upgrades sell automatically each tick. When broke, "
        "the 'Scrounge for cash' button gives you $1."
    )
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 9: Upgrades & Prestige
    # ══════════════════════════════════════════════════════════
    _header("Upgrades & Prestige")
    _text(
        "Spend money on upgrades to improve fuel durability, power, "
        "vent rates, and more. Most can be purchased multiple times."
    )
    _text(
        "Prestige resets everything but earns exotic particles (EP) "
        "based on total money. EP buys permanent upgrades that "
        "persist through resets and unlock experimental fuels."
    )
    _text(
        "Tip: wait for 51+ EP before your first prestige."
    )
    _divider()

    # ══════════════════════════════════════════════════════════
    # Section 10: Layout Strategy
    # ══════════════════════════════════════════════════════════
    _header("Layout Strategy")
    _text("Early game: checkerboard fuel + vents (1 pulse each):")
    _grid([
        [F, V, F, V, F],
        [V, F, V, F, V],
        [F, V, F, V, F],
    ])
    _text(
        "Each fuel cell only has vent neighbors so pulse count = 1 "
        "(self only). Minimal heat, vents handle it directly."
    )
    _spacer(6)
    _text(
        "Mid/Late game: separate your cooling bank from your fuel. "
        "Fuel cells can explode and destroy neighbors!"
    )
    _grid([
        [K, V, K, R, F],
        [V, O, V, R, F],
        [K, V, K, R, F],
    ])
    _text(
        "Left: cooling bank - outlet surrounded by vents, capacitors "
        "for power storage and active venting. Center: reflector "
        "buffer protects capacitors from explosions AND boosts "
        "adjacent fuel power. Right: fuel cells."
    )
    _spacer(6)
    _text("Scaling up: more outlets, more vents, more fuel:")
    _grid([
        [K, V, K, P, F, F],
        [V, O, V, R, F, F],
        [K, V, K, R, F, F],
        [V, O, V, R, F, F],
        [K, V, K, P, F, F],
    ])
    _text(
        "Plates and reflectors form a buffer between the cooling "
        "bank and the fuel cluster. Fuel heat all goes to hull "
        "(neighbors are fuel or reflectors with 0 heat capacity), "
        "then outlets pull it to vents."
    )
    _spacer(6)
    _text(
        "Remember: vents are often the bottleneck. Their dissipation "
        "rate limits total cooling. If heat builds up, add more vents "
        "or upgrade to higher-tier vents."
    )
    _spacer(60)

    return items, y


# ── Upgrade grid position tables (row, col) ──────────────────────────
# RE: unnamed_function_10402 (lines 385871-386261) — explicit (col, row) coords.
# Grid spacing in original: 50px horizontal (0x32), 54px vertical (0x36).
#
# Page 0 (Main Upgrades):
#   Row 0: fuel durability (0-5) + fuel power (6-11) = 12 cols
#   Row 1: perpetual (12-17) + [22,24,18,20,21,19] = 12 cols
#   Row 2: empty
#   Row 3: [25,26,27, _, 23]
#   Row 4: empty
#   Row 5: [28,29,30, _, 31]
_UPGRADE_GRID_POSITIONS: dict[int, tuple[int, int]] = {
    # Row 0: Fuel durability (cols 0-5) + Fuel power (cols 6-11)
    0: (0, 0), 1: (0, 1), 2: (0, 2), 3: (0, 3), 4: (0, 4), 5: (0, 5),
    6: (0, 6), 7: (0, 7), 8: (0, 8), 9: (0, 9), 10: (0, 10), 11: (0, 11),
    # Row 1: Perpetual fuel (cols 0-5) + infrastructure in display order (cols 6-11)
    16: (1, 0), 17: (1, 1), 18: (1, 2), 19: (1, 3), 20: (1, 4), 21: (1, 5),
    22: (1, 6), 24: (1, 7), 12: (1, 8), 14: (1, 9), 15: (1, 10), 13: (1, 11),
    # Row 3: Vents group + Coolant (gap at col 3)
    25: (3, 0), 26: (3, 1), 27: (3, 2), 23: (3, 4),
    # Row 5: Exchangers group + Reflectors (gap at col 3)
    28: (5, 0), 29: (5, 1), 30: (5, 2), 31: (5, 4),
    # Gate upgrades 32-33 not displayed in main grid
}

# Page 1 (Prestige Upgrades):
#   Row 0: [32, _, 34,35,36,37,38,39,43,44,40]
#   Row 1: [33, 45, _, 50]
#   Row 2: [46, _, _, 42, 41]
#   Rows 3-5: [47], [48], [49] in col 0
_PRESTIGE_GRID_POSITIONS: dict[int, tuple[int, int]] = {
    # Row 0: Research Grant + prestige upgrades
    32: (0, 0),   # Research Grant
    34: (0, 2),   # Infused Fuel Cells
    35: (0, 3),   # Unleashed Fuel Cells
    36: (0, 4),   # Quantum Buffering
    37: (0, 5),   # Full-Spectrum Reflectors
    38: (0, 6),   # Fluid Hyperdynamics
    39: (0, 7),   # Fractal Piping
    43: (0, 8),   # Ultracryonics
    44: (0, 9),   # Phlebotinum Core
    40: (0, 10),  # Aggressive Bartering
    # Row 1: Protium Research + Refactored Protium + Component Discount
    33: (1, 0),   # Protium Research
    45: (1, 1),   # Refactored Protium
    50: (1, 3),   # Subspace Expansion
    # Row 2: Monastium + Vortex Cooling + Exp Capacitance
    46: (2, 0),   # Monastium Research
    42: (2, 3),   # Vortex Cooling
    41: (2, 4),   # Experimental Capacitance Research
    # Rows 3-5: Special fuel research (col 0 only)
    47: (3, 0),   # Kymium Research
    48: (4, 0),   # Discurrium Research
    49: (5, 0),   # Stavrium Research
}


def _measure(text: str, font_size: int) -> int:
    if measure_text is not None:
        return measure_text(text, font_size)
    return int(len(text) * font_size * 0.6)


def _fit_font_size(text: str, max_width: int, base_size: int, min_size: int = 8) -> int:
    """Return the largest font size <= base_size that fits text within max_width."""
    size = base_size
    while size > min_size:
        if _measure(text, size) <= max_width:
            return size
        size -= 1
    return min_size


def _wrap_text(text: str, max_width: int, font_size: int) -> list[str]:
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        width = _measure(candidate, font_size)
        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _format_component_description(comp: ComponentTypeStats, sim: "Simulation | None" = None) -> str:
    """Fill {N} placeholders in description templates with actual stat values.

    RE: unnamed_function_10455 — 17-element array passed to String.Format:
      {0}  = MaxDurability (fn_10370 stat=1)
      {1}  = HeatCapacity (fn_10370 stat=2)
      {2}  = Power for 1 core (fn_10446 cores=1) = energyPerPulse
      {3}  = HeatPerPulse (fn_10370 stat=4)
      {4}  = PulsesPerCore (fn_10370 stat=5)
      {5}  = SelfVentRate × selfVentMult (fn_10370 stat=6 × Reactor+0x70)
      {6}  = fn_10370 stat=7 (unused in known templates)
      {7}  = fn_10370 stat=8 (HeatExchangeRate)
      {8}  = fn_10370 stat=9 × heatExchangeMult (ReactorVentRate × mult)
      {9}  = fn_10370 stat=10 × heatExchangeMult
      {10} = ReactorHeatCapacityIncrease (fn_10370 stat=0xb)
      {11} = ReactorPowerCapacityIncrease (fn_10370 stat=0xc)
      {12} = Power for 4 cores (fn_10446 cores=4): 4 × energyPerPulse
      {13} = Heat for 4 cores (fn_10444 cores=4): (16 × heatPerPulse) / (cellW × cellH)
      {14} = Power for 12 cores (fn_10446 cores=12): 12 × energyPerPulse
      {15} = Heat for 12 cores (fn_10444 cores=12): (144 × heatPerPulse) / (cellW × cellH)
      {16} = ReflectorBonusPct (fn_10445)
    """
    from game.upgrades import StatCategory as SC

    description = comp.description or ""
    if "{" not in description:
        return description or ""

    tid = comp.component_type_id

    # Apply upgrade multipliers if simulation is available
    def _m(stat: int) -> float:
        if sim is None:
            return 1.0
        return sim.upgrade_manager.get_upgrade_stat_bonus(tid, stat)

    dur = comp.max_durability * _m(SC.MAX_DURABILITY)
    heat_cap = comp.heat_capacity * _m(SC.HEAT_CAPACITY)
    epp = comp.energy_per_pulse * _m(SC.ENERGY_PER_PULSE)
    # RE: Protium (type 16) — displayed power includes permanent depletion bonus
    if tid == 16 and sim is not None:
        epp *= sim.depleted_protium_count / 100.0 + 1.0
    hpp = comp.heat_per_pulse * _m(SC.HEAT_PER_PULSE)
    # Include global multipliers from Active Venting / Active Exchangers
    _svm = sim.self_vent_mult if sim is not None else 1.0
    _hem = sim.heat_exchange_mult if sim is not None else 1.0
    svr = comp.self_vent_rate * _m(SC.SELF_VENT_RATE) * _svm
    rvr = comp.reactor_vent_rate * _m(SC.REACTOR_TRANSFER_RATE) * _hem
    reactor_heat_cap = comp.reactor_heat_capacity_increase * _m(SC.REACTOR_HEAT_CAP_INCREASE)
    reactor_power_cap = comp.reactor_power_capacity_increase * _m(SC.REACTOR_POWER_CAP_INCREASE)

    # Multi-core power/heat formulas (RE: fn_10446 / fn_10444)
    cell_area = max(1, comp.cell_width * comp.cell_height)
    # {12}/{13}: double cell (cores=4)
    power_4 = 4 * epp
    heat_4 = (16 * hpp) / cell_area
    # {14}/{15}: quad cell (cores=12)
    power_12 = 12 * epp
    heat_12 = (144 * hpp) / cell_area

    # {8} = stat 9 (AdjacentTransferRate) × heatExchangeMult — used by exchangers
    adj_rate = comp.self_vent_rate * _m(SC.ADJACENT_TRANSFER_RATE) * _hem
    placeholder_map = {
        "0": format_number_with_suffix(dur),
        "1": format_number_with_suffix(heat_cap),
        "2": format_number_with_suffix(epp),
        "3": format_number_with_suffix(hpp),
        "4": format_number_with_suffix(comp.pulses_produced),
        "5": format_number_with_suffix(svr),
        "7": format_number_with_suffix(comp.self_vent_rate * _m(SC.REACTOR_VENT_RATE)),  # stat=8
        "8": format_number_with_suffix(adj_rate),
        "9": format_number_with_suffix(rvr),
        "10": format_number_with_suffix(reactor_heat_cap),
        "11": format_number_with_suffix(reactor_power_cap),
        "12": format_number_with_suffix(power_4),
        "13": format_number_with_suffix(heat_4),
        "14": format_number_with_suffix(power_12),
        "15": format_number_with_suffix(heat_12),
        "16": f"{int(_m(SC.REFLECTOR_EFFECTIVENESS) - 1.0) + 10}",
    }

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return placeholder_map.get(key, "?")

    return re.sub(r"\{(\d+)\}", _replace, description)


def _format_cost_line(comp: ComponentTypeStats, effective_cost: float | None = None) -> str:
    cost = effective_cost if effective_cost is not None else comp.cost
    if cost > 0.0:
        return f"Cost: {format_number_with_suffix(cost)}"
    return "Cost: ???"


def _format_sell_line(placed: ReactorComponent) -> str:
    from game.simulation import Simulation
    sell = Simulation.sell_value(placed)
    if sell > 0.0:
        return f"Sells for: {format_number_with_suffix(sell)}"
    if placed.stats.cost > 0.0:
        return "Sells for: 0"
    return ""





def format_number_with_suffix(value: float, max_decimals: int = 3, min_decimals: int = 0, isInteger: bool = False) -> str:
    zero = "0." + "0" * min_decimals if min_decimals > 0 else "0"
    if not math.isfinite(value):
        return zero
    if value == 0.0:
        return zero

    # Derived from FormatNumberWithSuffix in the decompiled WebGL build.
    suffixes = [
        "",
        "K",
        "M",
        "B",
        "T",
        "Qa",
        "Qi",
        "Sx",
        "Sp",
        "O",
        "N",
        "U",
        "D",
        "DD",
        "TD",
        "QuD",
        "QaD",
        "SxD",
        "SpD",
        "OD",
        "ND",
        "V",
    ]
    abs_val = abs(value)
    if abs_val == 0.0:
        return "0"

    if abs_val < 1000.0:
        group = 0
    else:
        exp = int(math.floor(math.log10(abs_val)))
        group = max(0, int(exp / 3))

    group = min(group, len(suffixes) - 1)
    scale = 10 ** (group * 3)
    scaled = value / scale
    if group < len(suffixes) - 1 and abs(scaled) >= 999.5:
        group += 1
        scale *= 1000
        scaled = value / scale
    if isInteger and group == 0:
        decimals = 0
    else:
        decimals = max(0, min(4, max_decimals))

    out = f"{scaled:.{decimals}f}"
    if "." in out:
        out = out.rstrip("0").rstrip(".")
    if min_decimals > 0:
        if "." not in out:
            out += "." + "0" * min_decimals
        else:
            current = len(out.split(".")[1])
            if current < min_decimals:
                out += "0" * (min_decimals - current)
    return f"{out}{suffixes[group]}"
