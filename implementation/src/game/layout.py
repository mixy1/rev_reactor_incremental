from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2]


def default_layout_path() -> Path:
    return _repo_root() / "implementation" / "layout.json"


@dataclass
class Layout:
    window_width: int = 900
    window_height: int = 630

    grid_frame_x: int = 270
    grid_frame_y: int = 106
    grid_backer_offset_x: int = 11
    grid_backer_offset_y: int = 1
    grid_origin_x: int = 281
    grid_origin_y: int = 107
    grid_cell_size: int = 32
    grid_width: int = 19
    grid_height: int = 16

    hud_x: int = 16
    hud_y: int = 16
    hud_line_spacing: int = 20

    power_bar_x: int = 14
    power_bar_y: int = 142
    heat_bar_x: int = 14
    heat_bar_y: int = 78
    bar_width: int = 242
    bar_height: int = 28

    cash_x: int = 13
    cash_y: int = 13
    cash_w: int = 244
    cash_h: int = 30
    cash_line_spacing: int = 18

    vent_x: int = 13
    vent_y: int = 109
    sell_x: int = 13
    sell_y: int = 173

    pause_x: int = 847
    pause_y: int = 17
    replace_x: int = 847
    replace_y: int = 59
    options_x: int = 13
    options_y: int = 587
    stats_x_btn: int = 97
    stats_y_btn: int = 587
    help_x: int = 181
    help_y: int = 587
    back_x: int = 285
    back_y: int = 569
    main_upgrades_x: int = 13
    main_upgrades_y: int = 45
    prestige_upgrades_x: int = 149
    prestige_upgrades_y: int = 45
    shop_root_x: int = 7
    shop_root_y: int = 247
    shop_root_w: int = 64
    shop_root_h: int = 64
    store_area_x: int = 15
    store_area_y: int = 231
    store_area_w: int = 240
    store_area_h: int = 336
    store_row_h: int = 30
    store_sep_h: int = 4
    store_tab_offset_y: int = -5

    stats_x: int = 560
    stats_y: int = 360
    stats_line_spacing: int = 16

    left_panel_x: int = 0
    left_panel_y: int = 0
    left_panel_w: int = 270
    left_panel_h: int = 630

    top_panel_x: int = 270
    top_panel_y: int = 0
    top_panel_w: int = 630
    top_panel_h: int = 106

    # Upgrade grid (occupies same area as reactor grid when upgrade view is active)
    upgrade_grid_x: int = 281
    upgrade_grid_y: int = 107
    upgrade_cell_size: int = 44
    upgrade_cols: int = 13
    upgrade_rows: int = 5
    upgrade_gap: int = 2


def load_layout(path: Path | None = None) -> Layout:
    if path is None:
        path = default_layout_path()
    if not path.exists():
        return Layout()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Layout()
    try:
        return Layout(**data)
    except TypeError:
        return Layout()


def save_layout(layout: Layout, path: Path | None = None) -> None:
    if path is None:
        path = default_layout_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(layout), indent=2), encoding="utf-8")
