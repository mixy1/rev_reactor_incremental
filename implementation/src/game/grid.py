from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Tuple

from raylib_compat import (
    Color,
    Texture2D,
    Vector2,
    begin_scissor_mode,
    draw_rectangle,
    draw_rectangle_lines,
    draw_texture_ex,
    end_scissor_mode,
)


# Scrollbar visual constants
_SCROLLBAR_THICKNESS = 6
_SCROLLBAR_COLOR = Color(100, 100, 120, 180)
_SCROLLBAR_THUMB_COLOR = Color(180, 180, 200, 220)
_SCROLLBAR_THUMB_HOVER = Color(220, 220, 240, 240)


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

    def index(self, x: int, y: int, z: int = 0) -> int:
        if not self.in_bounds(x, y, z):
            raise IndexError(f"Grid index out of bounds: ({x}, {y}, {z})")
        return (z * self.height + y) * self.width + x

    def in_bounds(self, x: int, y: int, z: int = 0) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and 0 <= z < self.layers

    def get(self, x: int, y: int, z: int = 0) -> Optional[object]:
        if not self.in_bounds(x, y, z):
            return None
        return self.cells[self.index(x, y, z)]

    def set(self, x: int, y: int, z: int, value: Optional[object]) -> None:
        self.cells[self.index(x, y, z)] = value

    def clear(self, x: int, y: int, z: int = 0) -> None:
        self.set(x, y, z, None)

    def iter_cells(self) -> Iterable[Tuple[int, int, int, Optional[object]]]:
        for z in range(self.layers):
            for y in range(self.height):
                for x in range(self.width):
                    yield x, y, z, self.get(x, y, z)

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

    def neighbors(self, x: int, y: int, z: int = 0) -> list[tuple[int, int, int]]:
        coords: list[tuple[int, int, int]] = []
        if x > 0:
            coords.append((x - 1, y, z))
        if x < self.width - 1:
            coords.append((x + 1, y, z))
        if y > 0:
            coords.append((x, y - 1, z))
        if y < self.height - 1:
            coords.append((x, y + 1, z))
        return coords

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

    # ── Scroll / Resize ──────────────────────────────────────────

    @property
    def needs_scroll(self) -> bool:
        return self.width > self.base_width or self.height > self.base_height

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

        self.clamp_scroll()

    def clamp_scroll(self) -> None:
        grid_w_px = self.width * self.cell_size
        grid_h_px = self.height * self.cell_size
        max_sx = max(0, grid_w_px - self.viewport_w)
        max_sy = max(0, grid_h_px - self.viewport_h)
        self.scroll_x = max(0.0, min(self.scroll_x, float(max_sx)))
        self.scroll_y = max(0.0, min(self.scroll_y, float(max_sy)))

    def cell_to_screen(self, x: int, y: int) -> tuple[int, int]:
        return (
            int(self.origin_x + x * self.cell_size - self.scroll_x),
            int(self.origin_y + y * self.cell_size - self.scroll_y),
        )

    def screen_to_cell(self, sx: int, sy: int) -> Optional[tuple[int, int]]:
        # Must be within the viewport rectangle
        if not (self.origin_x <= sx < self.origin_x + self.viewport_w and
                self.origin_y <= sy < self.origin_y + self.viewport_h):
            return None
        x = int((sx - self.origin_x + self.scroll_x) // self.cell_size)
        y = int((sy - self.origin_y + self.scroll_y) // self.cell_size)
        if 0 <= x < self.width and 0 <= y < self.height:
            return x, y
        return None

    def screen_to_cell_unbounded(self, sx: int, sy: int) -> Optional[tuple[int, int]]:
        """Map screen coords to grid coords without viewport clipping.

        Used for drag interactions when cursor temporarily leaves the
        game canvas while the mouse button is still held.
        """
        x = int((sx - self.origin_x + self.scroll_x) // self.cell_size)
        y = int((sy - self.origin_y + self.scroll_y) // self.cell_size)
        if 0 <= x < self.width and 0 <= y < self.height:
            return x, y
        return None

    def draw(self, line_color: Color) -> None:
        if not self.needs_scroll:
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

        # Scrollable grid: tile-based drawing with scissor clipping
        begin_scissor_mode(
            self.origin_x, self.origin_y,
            self.viewport_w, self.viewport_h,
        )

        tiles_per_cell = max(1, int(self.cell_size // self.tile_size))
        tile_w_total = self.width * tiles_per_cell
        tile_h_total = self.height * tiles_per_cell
        for ty in range(tile_h_total):
            for tx in range(tile_w_total):
                px = int(self.origin_x + tx * self.tile_size - self.scroll_x)
                py = int(self.origin_y + ty * self.tile_size - self.scroll_y)
                # Cull off-screen tiles
                if (px + self.tile_size < self.origin_x or
                        px > self.origin_x + self.viewport_w or
                        py + self.tile_size < self.origin_y or
                        py > self.origin_y + self.viewport_h):
                    continue
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

        end_scissor_mode()

    def draw_scrollbars(self) -> None:
        """Draw scrollbar tracks and thumbs along right and bottom edges of viewport."""
        if not self.needs_scroll:
            return

        grid_w_px = self.width * self.cell_size
        grid_h_px = self.height * self.cell_size
        t = _SCROLLBAR_THICKNESS

        # Horizontal scrollbar (bottom edge)
        if self.width > self.base_width:
            track_x = self.origin_x
            track_y = self.origin_y + self.viewport_h
            track_w = self.viewport_w
            draw_rectangle(track_x, track_y, track_w, t, _SCROLLBAR_COLOR)

            ratio = self.viewport_w / max(1, grid_w_px)
            thumb_w = max(20, int(track_w * ratio))
            max_sx = max(1, grid_w_px - self.viewport_w)
            thumb_x = track_x + int((track_w - thumb_w) * (self.scroll_x / max_sx))
            draw_rectangle(thumb_x, track_y, thumb_w, t, _SCROLLBAR_THUMB_COLOR)

        # Vertical scrollbar (right edge)
        if self.height > self.base_height:
            track_x = self.origin_x + self.viewport_w
            track_y = self.origin_y
            track_h = self.viewport_h
            draw_rectangle(track_x, track_y, t, track_h, _SCROLLBAR_COLOR)

            ratio = self.viewport_h / max(1, grid_h_px)
            thumb_h = max(20, int(track_h * ratio))
            max_sy = max(1, grid_h_px - self.viewport_h)
            thumb_y = track_y + int((track_h - thumb_h) * (self.scroll_y / max_sy))
            draw_rectangle(track_x, thumb_y, t, thumb_h, _SCROLLBAR_THUMB_COLOR)

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
                self.scroll_y -= wheel_move * self.cell_size
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
        grid_w_px = self.width * self.cell_size
        grid_h_px = self.height * self.cell_size

        consumed = False

        # Horizontal scrollbar hit area
        h_track_x = self.origin_x
        h_track_y = self.origin_y + self.viewport_h
        h_track_w = self.viewport_w
        in_h_track = (h_track_x <= mx <= h_track_x + h_track_w and
                      h_track_y <= my <= h_track_y + t)

        # Vertical scrollbar hit area
        v_track_x = self.origin_x + self.viewport_w
        v_track_y = self.origin_y
        v_track_h = self.viewport_h
        in_v_track = (v_track_x <= mx <= v_track_x + t and
                      v_track_y <= my <= v_track_y + v_track_h)

        # Start drag on press
        if mouse_pressed:
            if in_h_track and self.width > self.base_width:
                self._scrollbar_dragging_h = True
            if in_v_track and self.height > self.base_height:
                self._scrollbar_dragging_v = True

        # Release drag
        if not mouse_down:
            self._scrollbar_dragging_h = False
            self._scrollbar_dragging_v = False

        # Process drag
        if self._scrollbar_dragging_h and mouse_down and self.width > self.base_width:
            ratio = max(0.0, min(1.0, (mx - h_track_x) / max(1, h_track_w)))
            max_sx = max(0, grid_w_px - self.viewport_w)
            self.scroll_x = ratio * max_sx
            self.clamp_scroll()
            consumed = True

        if self._scrollbar_dragging_v and mouse_down and self.height > self.base_height:
            ratio = max(0.0, min(1.0, (my - v_track_y) / max(1, v_track_h)))
            max_sy = max(0, grid_h_px - self.viewport_h)
            self.scroll_y = ratio * max_sy
            self.clamp_scroll()
            consumed = True

        return consumed
