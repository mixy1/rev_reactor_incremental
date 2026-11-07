from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Tuple

from raylib_compat import (
    Color,
    Rectangle,
    Texture2D,
    Vector2,
    begin_scissor_mode,
    draw_rectangle,
    draw_rectangle_lines,
    draw_texture_ex,
    draw_texture_pro,
    end_scissor_mode,
)


# Scrollbar visual constants
_SCROLLBAR_THICKNESS = 6
_SCROLLBAR_COLOR = Color(100, 100, 120, 180)
_SCROLLBAR_THUMB_COLOR = Color(180, 180, 200, 220)
_SCROLLBAR_THUMB_HOVER = Color(220, 220, 240, 240)

# Zoom: each wheel notch changes the on-screen cell size by base_cell / this.
_ZOOM_STEPS_PER_BASE = 8


@dataclass
class Grid:
    width: int
    height: int
    tile_size: int
    layers: int = 1
    origin_x: int = 16
    origin_y: int = 64
    tile_texture: Optional[Texture2D] = None
    full_texture: Optional[Texture2D] = None
    cell_size: Optional[int] = None
    base_width: int = 0
    base_height: int = 0
    cells: list[Optional[object]] = field(init=False, repr=False)

    # Viewport pixel size (computed in __post_init__)
    viewport_w: int = field(init=False, repr=False, default=0)
    viewport_h: int = field(init=False, repr=False, default=0)

    # Scroll state
    scroll_x: float = field(init=False, repr=False, default=0.0)
    scroll_y: float = field(init=False, repr=False, default=0.0)

    # Scrollbar drag state
    _scrollbar_dragging_h: bool = field(init=False, repr=False, default=False)
    _scrollbar_dragging_v: bool = field(init=False, repr=False, default=False)
    _neighbor_cache: list[tuple[tuple[int, int, int], ...]] = field(
        init=False, repr=False, default_factory=list
    )

    # Zoom state (Subspace Expansion). `cell_size` stays the unzoomed size the
    # viewport is built from; `view_cell_size` is the current on-screen size
    # used for drawing and mouse mapping (may be fractional at full zoom-out,
    # where the grid is scaled to exactly fill the viewport). 0 = not zoomed.
    _zoom_cell_size: float = field(init=False, repr=False, default=0)
    _zoom_accum: float = field(init=False, repr=False, default=0.0)

    def __post_init__(self) -> None:
        if self.cell_size is None:
            self.cell_size = self.tile_size * 2
        if self.base_width == 0:
            self.base_width = self.width
        if self.base_height == 0:
            self.base_height = self.height
        self.viewport_w = self.base_width * self.cell_size
        self.viewport_h = self.base_height * self.cell_size
        self.cells = [None] * (self.width * self.height * self.layers)
        self._rebuild_neighbor_cache()

    def _rebuild_neighbor_cache(self) -> None:
        """Precompute cardinal topology; it changes only when the grid resizes."""
        cache: list[tuple[tuple[int, int, int], ...]] = []
        for z in range(self.layers):
            for y in range(self.height):
                for x in range(self.width):
                    coords: list[tuple[int, int, int]] = []
                    if x > 0:
                        coords.append((x - 1, y, z))
                    if x < self.width - 1:
                        coords.append((x + 1, y, z))
                    if y > 0:
                        coords.append((x, y - 1, z))
                    if y < self.height - 1:
                        coords.append((x, y + 1, z))
                    cache.append(tuple(coords))
        self._neighbor_cache = cache

    def index(self, x: int, y: int, z: int = 0) -> int:
        if not self.in_bounds(x, y, z):
            raise IndexError(f"Grid index out of bounds: ({x}, {y}, {z})")
        return (z * self.height + y) * self.width + x

    def in_bounds(self, x: int, y: int, z: int = 0) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and 0 <= z < self.layers

    def get(self, x: int, y: int, z: int = 0) -> Optional[object]:
        if not self.in_bounds(x, y, z):
            return None
        return self.cells[(z * self.height + y) * self.width + x]

    def set(self, x: int, y: int, z: int, value: Optional[object]) -> None:
        self.cells[self.index(x, y, z)] = value

    def clear(self, x: int, y: int, z: int = 0) -> None:
        self.set(x, y, z, None)

    def iter_cells(self) -> Iterable[Tuple[int, int, int, Optional[object]]]:
        for z in range(self.layers):
            for y in range(self.height):
                for x in range(self.width):
                    idx = (z * self.height + y) * self.width + x
                    yield x, y, z, self.cells[idx]

    def neighbor_offsets(self, x: int, y: int) -> list[int]:
        offsets: list[int] = []
        if x > 0:
            offsets.append(-1)
        if x < self.width - 1:
            offsets.append(1)
        if y > 0:
            offsets.append(-self.width)
        if y < self.height - 1:
            offsets.append(self.width)
        return offsets

    def neighbors(self, x: int, y: int, z: int = 0) -> tuple[tuple[int, int, int], ...]:
        if not self.in_bounds(x, y, z):
            return ()
        idx = (z * self.height + y) * self.width + x
        return self._neighbor_cache[idx]

    def manhattan_neighbors(self, x: int, y: int, z: int, radius: int) -> list[tuple[int, int, int]]:
        """RE: fn 10440 — cells within Manhattan distance ≤ radius (diamond shape), excluding self."""
        coords: list[tuple[int, int, int]] = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                if abs(dx) + abs(dy) > radius:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    coords.append((nx, ny, z))
        return coords

    # ── Zoom ─────────────────────────────────────────────────────

    @property
    def view_cell_size(self) -> float:
        """Current on-screen cell size in px (cell_size when not zoomed). It can
        be fractional at full zoom-out; use cell_rect()/cell_to_screen() for
        exact, gap-free pixel edges."""
        return self._zoom_cell_size or self.cell_size

    @property
    def zoomed(self) -> bool:
        return self.view_cell_size != self.cell_size

    def fit_cell_size(self) -> float:
        """Cell size that makes the whole grid fill the viewport exactly on its
        limiting axis (e.g. exactly the viewport height), never above cell_size."""
        fit = min(self.viewport_w / max(1, self.width), self.viewport_h / max(1, self.height))
        return self.cell_size if fit >= self.cell_size else fit

    def _zoom_levels(self) -> list:
        """Zoom stops from cell_size down to the exact fit, in whole-pixel steps."""
        base = self.cell_size
        fit = self.fit_cell_size()
        step = max(1, round(base / _ZOOM_STEPS_PER_BASE))
        levels = [base]  # normal size is always a stop, however close the fit is
        size = base - step
        while size > fit + step / 2:
            levels.append(size)
            size -= step
        if fit < base:
            levels.append(fit)
        return levels

    def set_view_cell_size(self, size: float, anchor_x: Optional[float] = None, anchor_y: Optional[float] = None) -> None:
        """Zoom to `size` px per cell (clamped between fit-to-viewport and
        cell_size), keeping the grid point under (anchor_x, anchor_y) in place.
        Anchors outside the viewport use the viewport centre."""
        size = max(self.fit_cell_size(), min(self.cell_size, size))
        old = self.view_cell_size
        if abs(size - old) < 1e-9:
            return
        inside = (
            anchor_x is not None and anchor_y is not None
            and self.origin_x <= anchor_x < self.origin_x + self.viewport_w
            and self.origin_y <= anchor_y < self.origin_y + self.viewport_h
        )
        lx = (anchor_x - self.origin_x) if inside else self.viewport_w / 2
        ly = (anchor_y - self.origin_y) if inside else self.viewport_h / 2
        # Grid position (in cells) under the anchor before zooming
        gx = (lx - self.pad_x + self.scroll_x) / old
        gy = (ly - self.pad_y + self.scroll_y) / old
        self._zoom_cell_size = 0 if size == self.cell_size else size
        # Scroll so the same grid position stays under the anchor
        self.scroll_x = gx * size - (lx - self.pad_x)
        self.scroll_y = gy * size - (ly - self.pad_y)
        self.clamp_scroll()

    def zoom_by(self, wheel_move: float, anchor_x: Optional[float] = None, anchor_y: Optional[float] = None) -> None:
        """Wheel up zooms in (towards cell_size), wheel down zooms out (towards
        the exact fit). Fractional trackpad deltas accumulate into notches."""
        self._zoom_accum += wheel_move
        steps = int(self._zoom_accum)  # truncates toward zero
        if steps == 0:
            return
        self._zoom_accum -= steps
        levels = self._zoom_levels()
        cur = self.view_cell_size
        idx = min(range(len(levels)), key=lambda i: abs(levels[i] - cur))
        idx = max(0, min(len(levels) - 1, idx - steps))
        self.set_view_cell_size(levels[idx], anchor_x, anchor_y)

    def reset_zoom(self) -> None:
        self._zoom_accum = 0.0
        if self.zoomed:
            self.set_view_cell_size(self.cell_size)

    @property
    def pad_x(self) -> float:
        """Horizontal offset that centres the grid when it's narrower than the viewport."""
        return max(0.0, (self.viewport_w - self.width * self.view_cell_size) / 2)

    @property
    def pad_y(self) -> float:
        return max(0.0, (self.viewport_h - self.height * self.view_cell_size) / 2)

    def _edge_x(self, i: int) -> int:
        """Screen x of the left edge of column i (i == width gives the right edge)."""
        return int(round(self.origin_x + self.pad_x + i * self.view_cell_size - self.scroll_x))

    def _edge_y(self, j: int) -> int:
        return int(round(self.origin_y + self.pad_y + j * self.view_cell_size - self.scroll_y))

    def cell_rect(self, x: int, y: int) -> tuple[int, int, int, int]:
        """Exact on-screen (x, y, w, h) of a cell; neighbouring cells share edges."""
        x0, y0 = self._edge_x(x), self._edge_y(y)
        return x0, y0, self._edge_x(x + 1) - x0, self._edge_y(y + 1) - y0

    def _viewport_px(self) -> tuple[int, int, int, int]:
        """Viewport edges snapped to whole screen pixels (x0, y0, x1, y1)."""
        return (
            int(round(self.origin_x)),
            int(round(self.origin_y)),
            int(round(self.origin_x + self.viewport_w)),
            int(round(self.origin_y + self.viewport_h)),
        )

    def content_rect(self) -> tuple[int, int, int, int]:
        """Visible part of the grid on screen in whole pixels: the viewport,
        shrunk on any axis where the (zoomed-out) grid is smaller than it."""
        vx0, vy0, vx1, vy1 = self._viewport_px()
        x0 = max(vx0, self._edge_x(0))
        y0 = max(vy0, self._edge_y(0))
        x1 = min(vx1, self._edge_x(self.width))
        y1 = min(vy1, self._edge_y(self.height))
        return x0, y0, x1 - x0, y1 - y0

    def content_insets(self) -> tuple[int, int, int, int]:
        """(left, top, right, bottom) whole px between the viewport edges and
        the visible grid. All 0 unless zoomed out past the viewport on an axis."""
        vx0, vy0, vx1, vy1 = self._viewport_px()
        x, y, w, h = self.content_rect()
        return x - vx0, y - vy0, vx1 - (x + w), vy1 - (y + h)

    # ── Scroll / Resize ──────────────────────────────────────────

    @property
    def is_expanded(self) -> bool:
        """Grid is larger than its base size (Subspace Expansion)."""
        return self.width > self.base_width or self.height > self.base_height

    def _overflow_x(self) -> bool:
        return self.width * self.view_cell_size > self.viewport_w + 0.5

    def _overflow_y(self) -> bool:
        return self.height * self.view_cell_size > self.viewport_h + 0.5

    @property
    def needs_scroll(self) -> bool:
        """True when the grid doesn't fit the viewport at the current zoom."""
        return self._overflow_x() or self._overflow_y()

    def resize(self, new_width: int, new_height: int) -> None:
        """Grow or shrink the grid, preserving existing cells at their (x,y) positions."""
        if new_width == self.width and new_height == self.height:
            return
        old_w, old_h = self.width, self.height
        old_cells = self.cells

        self.width = new_width
        self.height = new_height
        self.cells = [None] * (new_width * new_height * self.layers)

        # Copy existing cells
        for z in range(self.layers):
            for y in range(min(old_h, new_height)):
                for x in range(min(old_w, new_width)):
                    old_idx = (z * old_h + y) * old_w + x
                    new_idx = (z * new_height + y) * new_width + x
                    self.cells[new_idx] = old_cells[old_idx]

        self._rebuild_neighbor_cache()
        # Keep the zoom within the new fit..cell_size range
        if self.zoomed:
            size = max(self.fit_cell_size(), min(self.cell_size, self.view_cell_size))
            self._zoom_cell_size = 0 if size == self.cell_size else size
        self.clamp_scroll()

    def clamp_scroll(self) -> None:
        cs = self.view_cell_size
        max_sx = max(0.0, self.width * cs - self.viewport_w)
        max_sy = max(0.0, self.height * cs - self.viewport_h)
        self.scroll_x = max(0.0, min(self.scroll_x, float(max_sx)))
        self.scroll_y = max(0.0, min(self.scroll_y, float(max_sy)))

    def cell_to_screen(self, x: int, y: int) -> tuple[int, int]:
        return self._edge_x(x), self._edge_y(y)

    def screen_to_cell(self, sx: int, sy: int) -> Optional[tuple[int, int]]:
        # Must be within the viewport rectangle
        if not (self.origin_x <= sx < self.origin_x + self.viewport_w and
                self.origin_y <= sy < self.origin_y + self.viewport_h):
            return None
        return self.screen_to_cell_unbounded(sx, sy)

    def screen_to_cell_unbounded(self, sx: int, sy: int) -> Optional[tuple[int, int]]:
        """Map screen coords to grid coords without viewport clipping.

        Used for drag interactions when cursor temporarily leaves the
        game canvas while the mouse button is still held.
        """
        cs = self.view_cell_size
        x = int((sx - self.origin_x - self.pad_x + self.scroll_x) // cs)
        y = int((sy - self.origin_y - self.pad_y + self.scroll_y) // cs)
        # Agree exactly with the rounded cell edges used for drawing
        if self._edge_x(x) > sx:
            x -= 1
        elif self._edge_x(x + 1) <= sx:
            x += 1
        if self._edge_y(y) > sy:
            y -= 1
        elif self._edge_y(y + 1) <= sy:
            y += 1
        if 0 <= x < self.width and 0 <= y < self.height:
            return x, y
        return None

    def draw(self, line_color: Color) -> None:
        if not self.is_expanded:
            # Original behavior: use full_texture if available
            if self.full_texture is not None:
                scale_x = (self.width * self.cell_size) / max(1, self.full_texture.width)
                scale_y = (self.height * self.cell_size) / max(1, self.full_texture.height)
                draw_texture_ex(
                    self.full_texture,
                    Vector2(self.origin_x, self.origin_y),
                    0.0,
                    min(scale_x, scale_y),
                    line_color,
                )
                return

            tiles_per_cell = max(1, int(self.cell_size // self.tile_size))
            tile_w = self.width * tiles_per_cell
            tile_h = self.height * tiles_per_cell
            for y in range(tile_h):
                for x in range(tile_w):
                    px = self.origin_x + x * self.tile_size
                    py = self.origin_y + y * self.tile_size
                    if self.tile_texture is not None:
                        scale = self.tile_size / max(1, self.tile_texture.width)
                        draw_texture_ex(
                            self.tile_texture,
                            Vector2(px, py),
                            0.0,
                            scale,
                            line_color,
                        )
                    else:
                        draw_rectangle_lines(px, py, self.tile_size, self.tile_size, line_color)
            return

        # Expanded grid: tiles fitted to each (possibly zoomed) cell, clipped to
        # the viewport and offset by scroll / centring padding.
        begin_scissor_mode(
            self.origin_x, self.origin_y,
            self.viewport_w, self.viewport_h,
        )

        tiles_per_cell = max(1, int(self.cell_size // self.tile_size))
        tex = self.tile_texture
        src = Rectangle(0, 0, tex.width, tex.height) if tex is not None else None
        vx0, vy0 = self.origin_x, self.origin_y
        vx1, vy1 = vx0 + self.viewport_w, vy0 + self.viewport_h
        for cy in range(self.height):
            for cx in range(self.width):
                px, py, cw, ch = self.cell_rect(cx, cy)
                # Cull off-screen cells
                if px + cw < vx0 or px > vx1 or py + ch < vy0 or py > vy1:
                    continue
                # Split the cell into tiles on integer boundaries (no seams)
                for j in range(tiles_per_cell):
                    ty0 = py + (j * ch) // tiles_per_cell
                    ty1 = py + ((j + 1) * ch) // tiles_per_cell
                    for i in range(tiles_per_cell):
                        tx0 = px + (i * cw) // tiles_per_cell
                        tx1 = px + ((i + 1) * cw) // tiles_per_cell
                        if tex is not None:
                            draw_texture_pro(
                                tex,
                                src,
                                Rectangle(tx0, ty0, tx1 - tx0, ty1 - ty0),
                                Vector2(0, 0),
                                0.0,
                                line_color,
                            )
                        else:
                            draw_rectangle_lines(tx0, ty0, tx1 - tx0, ty1 - ty0, line_color)

        end_scissor_mode()

    def _scrollbar_tracks(self) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """((x, y, w) of the horizontal track, (x, y, h) of the vertical track),
        hugging the visible grid so they line up with a frame drawn around it."""
        cx, cy, cw, ch = self.content_rect()
        return (cx, cy + ch, cw), (cx + cw, cy, ch)

    def draw_scrollbars(self) -> None:
        """Draw scrollbar tracks and thumbs along right and bottom edges of the grid.
        Each bar only appears when the grid overflows on that axis at the current zoom."""
        if not self.needs_scroll:
            return

        cs = self.view_cell_size
        grid_w_px = self.width * cs
        grid_h_px = self.height * cs
        t = _SCROLLBAR_THICKNESS
        (hx, hy, hw), (vx, vy, vh) = self._scrollbar_tracks()

        # Horizontal scrollbar (bottom edge)
        if self._overflow_x():
            draw_rectangle(hx, hy, hw, t, _SCROLLBAR_COLOR)
            ratio = self.viewport_w / max(1, grid_w_px)
            thumb_w = max(20, int(hw * ratio))
            max_sx = max(1, grid_w_px - self.viewport_w)
            thumb_x = hx + int((hw - thumb_w) * (self.scroll_x / max_sx))
            draw_rectangle(thumb_x, hy, thumb_w, t, _SCROLLBAR_THUMB_COLOR)

        # Vertical scrollbar (right edge)
        if self._overflow_y():
            draw_rectangle(vx, vy, t, vh, _SCROLLBAR_COLOR)
            ratio = self.viewport_h / max(1, grid_h_px)
            thumb_h = max(20, int(vh * ratio))
            max_sy = max(1, grid_h_px - self.viewport_h)
            thumb_y = vy + int((vh - thumb_h) * (self.scroll_y / max_sy))
            draw_rectangle(vx, thumb_y, t, thumb_h, _SCROLLBAR_THUMB_COLOR)

    def handle_scroll_input(
        self, mx: float, my: float,
        prev_mx: float, prev_my: float,
        middle_down: bool, wheel_move: float,
    ) -> None:
        """Handle middle-mouse drag panning and scroll wheel."""
        if not self.needs_scroll:
            return

        # Middle mouse drag: inverted (drag down → scroll up feels natural for panning)
        if middle_down:
            dx = prev_mx - mx
            dy = prev_my - my
            self.scroll_x += dx
            self.scroll_y += dy
            self.clamp_scroll()

        # Scroll wheel: vertical scroll when mouse is over viewport
        if wheel_move != 0.0:
            if (self.origin_x <= mx < self.origin_x + self.viewport_w and
                    self.origin_y <= my < self.origin_y + self.viewport_h):
                self.scroll_y -= wheel_move * self.view_cell_size
                self.clamp_scroll()

    def handle_scrollbar_drag(
        self, mx: float, my: float,
        mouse_down: bool, mouse_pressed: bool,
    ) -> bool:
        """Handle LMB click/drag on scrollbar tracks. Returns True if input was consumed."""
        if not self.needs_scroll:
            self._scrollbar_dragging_h = False
            self._scrollbar_dragging_v = False
            return False

        t = _SCROLLBAR_THICKNESS
        cs = self.view_cell_size
        grid_w_px = self.width * cs
        grid_h_px = self.height * cs
        over_x, over_y = self._overflow_x(), self._overflow_y()
        (h_track_x, h_track_y, h_track_w), (v_track_x, v_track_y, v_track_h) = self._scrollbar_tracks()

        consumed = False

        in_h_track = (h_track_x <= mx <= h_track_x + h_track_w and
                      h_track_y <= my <= h_track_y + t)
        in_v_track = (v_track_x <= mx <= v_track_x + t and
                      v_track_y <= my <= v_track_y + v_track_h)

        # Start drag on press
        if mouse_pressed:
            if in_h_track and over_x:
                self._scrollbar_dragging_h = True
            if in_v_track and over_y:
                self._scrollbar_dragging_v = True

        # Release drag
        if not mouse_down:
            self._scrollbar_dragging_h = False
            self._scrollbar_dragging_v = False

        # Process drag
        if self._scrollbar_dragging_h and mouse_down and over_x:
            ratio = max(0.0, min(1.0, (mx - h_track_x) / max(1, h_track_w)))
            max_sx = max(0, grid_w_px - self.viewport_w)
            self.scroll_x = ratio * max_sx
            self.clamp_scroll()
            consumed = True

        if self._scrollbar_dragging_v and mouse_down and over_y:
            ratio = max(0.0, min(1.0, (my - v_track_y) / max(1, v_track_h)))
            max_sy = max(0, grid_h_px - self.viewport_h)
            self.scroll_y = ratio * max_sy
            self.clamp_scroll()
            consumed = True

        return consumed
