from __future__ import annotations

import sys
from dataclasses import dataclass, field
import math
import re
from typing import Optional

_WEB = sys.platform == "emscripten"

from raylib_compat import (
    Color,
    Rectangle,
    Texture2D,
    draw_rectangle,
    draw_rectangle_lines,
    draw_text,
    draw_texture_ex,
    draw_texture_pro,
    measure_text,
    Vector2,
)

from game.layout import Layout
from game.types import ComponentTypeStats
from game.simulation import ReactorComponent, Simulation
from game.upgrades import UpgradeManager, UpgradeType


@dataclass
class Ui:
    heat_icon: Optional[Texture2D] = None
    power_icon: Optional[Texture2D] = None
    button_base: Optional[Texture2D] = None
    button_hover: Optional[Texture2D] = None
    button_pressed: Optional[Texture2D] = None
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

    @staticmethod
    def draw_warning_badge(x: int, y: int, size: int = 12) -> None:
        """Compact amber warning badge used for outlet bottleneck warnings."""
        draw_rectangle(x + 1, y + 1, size, size, Color(18, 14, 8, 230))
        draw_rectangle(x, y, size, size, Color(62, 46, 14, 235))
        draw_rectangle_lines(x, y, size, size, Color(245, 200, 70, 255))
        text_x = x + max(1, size // 2 - 2)
        text_y = y + max(-1, (size - 10) // 2 - 1)
        draw_text("!", text_x, text_y, 10, Color(255, 236, 150, 255))

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
        icon_x = layout.heat_bar_x + 2
        icon_y = layout.heat_bar_y + 2
        text_x = icon_x
        if self.heat_icon is not None:
            draw_texture_ex(self.heat_icon, Vector2(icon_x, icon_y), 0.0, 1.0, Color(255, 255, 255, 255))
            text_x += self.heat_icon.width + 6
        heat_delta = sim.last_heat_change
        heat_sign = "+" if heat_delta >= 0 else ""
        heat_label = (
            f"{format_number_with_suffix(sim.reactor_heat, max_decimals=0)}/"
            f"{format_number_with_suffix(sim.max_reactor_heat, max_decimals=0)} "
            f"({heat_sign}{format_number_with_suffix(heat_delta, min_decimals=3)}/t)"
        )
        heat_max_w = layout.heat_bar_x + layout.bar_width - text_x - 4
        heat_font = _fit_font_size(heat_label, heat_max_w, 16)
        draw_text(
            heat_label,
            text_x,
            layout.heat_bar_y + 6,
            heat_font,
            Color(240, 80, 80, 255),
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
        icon_x = layout.power_bar_x + 2
        icon_y = layout.power_bar_y + 2
        text_x = icon_x
        if self.power_icon is not None:
            draw_texture_ex(self.power_icon, Vector2(icon_x, icon_y), 0.0, 1.0, Color(255, 255, 255, 255))
            text_x += self.power_icon.width + 6
        power_delta = sim.last_power_change
        power_sign = "+" if power_delta >= 0 else ""
        power_label = (
            f"{format_number_with_suffix(sim.stored_power, max_decimals=0)}/"
            f"{format_number_with_suffix(sim.max_reactor_power, max_decimals=0)} "
            f"({power_sign}{format_number_with_suffix(power_delta, min_decimals=3)}/t)"
        )
        power_max_w = layout.power_bar_x + layout.bar_width - text_x - 4
        power_font = _fit_font_size(power_label, power_max_w, 16)
        draw_text(
            power_label,
            text_x,
            layout.power_bar_y + 6,
            power_font,
            Color(80, 200, 255, 255),
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
        font_size = _fit_font_size(money_text, layout.cash_w - 4, 16)
        text_width = _measure(money_text, font_size)
        money_x = layout.cash_x + max(0, (layout.cash_w - text_width) // 2)
        draw_text(
            money_text,
            money_x,
            layout.cash_y + 6,
            font_size,
            Color(230, 230, 230, 255),
        )

        # Vent Heat button (RE: "-{ventAmount} Heat (-{ventRate} per tick)")
        vent_amt = format_number_with_suffix(sim.manual_vent_amount, max_decimals=2)
        vent_rate = format_number_with_suffix(sim.auto_vent_rate_per_tick(), max_decimals=2)
        vent_cap = format_number_with_suffix(sim.preview_active_dissipation, max_decimals=2)
        label = f"-{vent_amt} Heat (-{vent_rate}/t, cap {vent_cap}/t)"
        bx, by = layout.vent_x, layout.vent_y
        tex = self.button_base
        if pressed_vent and self.button_pressed is not None:
            tex = self.button_pressed
        elif hover_vent and self.button_hover is not None:
            tex = self.button_hover

        if tex is not None:
            draw_texture_ex(tex, Vector2(bx, by), 0.0, 1.0, Color(255, 255, 255, 255))
            btn_w = tex.width
            btn_h = tex.height
            btn_text_w = tex.width - 20
        else:
            btn_w = 220
            btn_h = 28
            draw_rectangle(bx, by, btn_w, btn_h, Color(60, 60, 70, 255))
            btn_text_w = 204
        vent_font = _fit_font_size(label, btn_text_w, 14, min_size=9)
        vent_text_w = _measure(label, vent_font)
        tx = bx + max(0, (btn_w - vent_text_w) // 2)
        ty = by + max(0, (btn_h - vent_font) // 2) - 1
        draw_text(label, tx, ty, vent_font, Color(240, 240, 240, 255))

        # Sell All Power / Scrounge button
        # RE: "Sell All Power: +{power} $ (+{autoSellRate} $ per tick)"
        # or "Scrounge for cash (+1$)" when money+power < 10
        if sim.can_scrounge():
            label = "Scrounge for cash (+1$)"
        else:
            power_str = format_number_with_suffix(sim.stored_power, max_decimals=2)
            rate_str = format_number_with_suffix(sim.auto_sell_rate_per_tick(), max_decimals=2)
            label = f"+{power_str}$ (+{rate_str}$/t)"
        bx, by = layout.sell_x, layout.sell_y
        tex = self.button_base
        if pressed_sell and self.button_pressed is not None:
            tex = self.button_pressed
        elif hover_sell and self.button_hover is not None:
            tex = self.button_hover

        if tex is not None:
            draw_texture_ex(tex, Vector2(bx, by), 0.0, 1.0, Color(255, 255, 255, 255))
            btn_w = tex.width
            btn_h = tex.height
            btn_text_w = tex.width - 20
        else:
            btn_w = 320
            btn_h = 28
            draw_rectangle(bx, by, btn_w, btn_h, Color(60, 60, 70, 255))
            btn_text_w = 304
        sell_font = _fit_font_size(label, btn_text_w, 14, min_size=9)
        sell_text_w = _measure(label, sell_font)
        tx = bx + max(0, (btn_w - sell_text_w) // 2)
        ty = by + max(0, (btn_h - sell_font) // 2) - 1
        draw_text(label, tx, ty, sell_font, Color(240, 240, 240, 255))

        # Stats panel is hidden until we wire the real stats page UI.
        new_selected, hovered = self.draw_store(sim, layout, mouse_x, mouse_y, mouse_pressed)
        if new_selected is not None:
            sim.selected_component_index = new_selected
        if hovered is not None:
            sim.hover_component = hovered
            sim.hover_placed_component = None  # shop hover overrides grid hover
        self.draw_component_info(sim, layout)

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
                if selected and pressed is not None and not locked:
                    tex = pressed
                elif hovered and hover is not None and not locked:
                    tex = hover
                tint = Color(70, 70, 70, 255) if locked else Color(255, 255, 255, 255)
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

    def draw_component_info(self, sim: Simulation, layout: Layout) -> None:
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
        margin = 14
        font_sm = 12
        font_title = 14

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
        if comp is None:
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
        top_row_y = panel_y + 12
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
        title_y = panel_y + 12
        draw_text(title, title_x, title_y, font_title, text_color)

        # ── Slot 1: Description — centered, wrapped, below title ──
        description = _format_component_description(comp, sim)
        if placed is not None and placed.depleted:
            description = "This cell has run out of fuel and is now inert. Right-click to remove it."
        # Usable width stops before the pause/replace buttons
        desc_max_w = right_edge - panel_x - margin
        desc_lines = _wrap_text(description, desc_max_w, font_sm) if description else []
        y = title_y + 20
        for line in desc_lines:
            line_w = _measure(line, font_sm)
            line_x = panel_x + max(0, (desc_max_w - line_w) // 2 + margin)
            draw_text(line, line_x, y, font_sm, text_color)
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
            draw_text(slot2_text, panel_x + margin, panel_y + panel_h - 20, font_sm, text_color)

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
        mouse_pressed: bool,
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
        ox = layout.upgrade_grid_x
        oy = layout.upgrade_grid_y

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
                tex = self.icon_button_pressed
            elif is_hover and can_buy:
                tex = self.icon_button_hover
            else:
                tex = self.icon_button

            # Bright if purchasable, dim otherwise
            if can_buy:
                tint = Color(255, 255, 255, 255)
            else:
                tint = Color(70, 70, 70, 255)

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
                    # Scale to fit within button with margin
                    margin = 8
                    max_w = cell_w - margin * 2
                    max_h = cell_h - margin * 2
                    scale = min(max_w / max(1, icon_tex.width), max_h / max(1, icon_tex.height))
                    dw = icon_tex.width * scale
                    dh = icon_tex.height * scale
                    ix = x + (cell_w - dw) / 2
                    iy = y + (cell_h - dh) / 2
                    draw_texture_pro(
                        icon_tex,
                        Rectangle(0, 0, icon_tex.width, icon_tex.height),
                        Rectangle(ix, iy, dw, dh),
                        Vector2(0, 0), 0.0, tint,
                    )

                # Category overlay in bottom-right corner
                cat_tex = sprites.get(u.category)
                if cat_tex is not None:
                    cx = x + cell_w - cat_tex.width - 2
                    cy = y + cell_h - cat_tex.height - 2
                    draw_texture_ex(cat_tex, Vector2(cx, cy), 0.0, 1.0, Color(255, 255, 255, 255))

            # Level indicator (bottom-left corner, above category overlay)
            if u.level > 0:
                lvl_text = str(u.level)
                draw_text(lvl_text, x + 4, y + cell_h - 14, 10, Color(200, 255, 200, 255))

            # Hover tracking
            if is_hover:
                hovered_upgrade = u

            # Click to purchase
            if is_hover and mouse_pressed and can_buy:
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
        margin = 14
        font_sm = 12
        font_title = 14

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
        draw_text(title, title_x, panel_y + 8, font_title, text_color)

        # Description
        desc_lines = _wrap_text(u.description, usable_w, font_sm)
        y = panel_y + 26
        for line in desc_lines:
            line_w = _measure(line, font_sm)
            line_x = panel_x + max(0, (usable_w - line_w) // 2 + margin)
            draw_text(line, line_x, y, font_sm, text_color)
            y += 14

        # Cost line (bottom-left)
        is_one_time_owned = u.cost_multiplier == 0.0 and u.level > 0
        if is_one_time_owned:
            cost_text = "PURCHASED"
        else:
            cost = mgr.get_cost(u.index)
            currency = "EP" if u.is_prestige else "$"
            cost_text = f"Cost: {format_number_with_suffix(cost)} {currency}"
        draw_text(cost_text, panel_x + margin, panel_y + panel_h - 20, font_sm, text_color)

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
        mouse_pressed: bool,
        dt: float,
    ) -> None:
        """Draw the Options panel in the grid content area."""
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

        pbtn_w = _measure(prestige_label, font_sm) + 24
        pbtn_h = 26
        pbtn_x = content_x + (content_w - pbtn_w) // 2
        pbtn_y = content_y

        hover_prestige_btn = (pbtn_x <= mouse_x <= pbtn_x + pbtn_w and
                              pbtn_y <= mouse_y <= pbtn_y + pbtn_h)

        if hover_prestige_btn and can_click:
            pbg = bg_hover
        elif can_click:
            pbg = bg_normal
        else:
            pbg = Color(40, 35, 50, 255)
        draw_rectangle(pbtn_x, pbtn_y, pbtn_w, pbtn_h, pbg)
        draw_rectangle_lines(pbtn_x, pbtn_y, pbtn_w, pbtn_h, border_color)
        plw = _measure(prestige_label, font_sm)
        ptint = text_color if can_click else Color(140, 140, 140, 255)
        draw_text(prestige_label, pbtn_x + (pbtn_w - plw) // 2, pbtn_y + 7, font_sm, ptint)

        if hover_prestige_btn and mouse_pressed and can_click:
            if sim.prestige_can_refund:
                sim.refund_prestige_upgrades()
            elif sim.prestige_confirming:
                sim.do_prestige()
            else:
                sim.prestige_confirming = True

        y = content_y + 34
        desc = (
            "When you 'prestige', you will lose all components, money, power, heat, and upgrades. "
            "In exchange, you'll get exotic particles, which will let you get powerful, permanent "
            "upgrades. It is recommended you wait until you can get 51 particles before your first prestige."
        )
        desc_lines = _wrap_text(desc, content_w, font_sm)
        for line in desc_lines:
            lw = _measure(line, font_sm)
            draw_text(line, content_x + (content_w - lw) // 2, y, font_sm, text_color)
            y += line_h

        # Reset Game button
        y += line_h
        btn_w = 160
        btn_h = 28
        btn_x = content_x + (content_w - btn_w) // 2
        btn_y = y

        hover_reset = (btn_x <= mouse_x <= btn_x + btn_w and
                       btn_y <= mouse_y <= btn_y + btn_h)

        # Decrement confirm timer
        if sim.reset_confirm_timer > 0:
            sim.reset_confirm_timer -= dt

        if hover_reset and mouse_pressed:
            if sim.reset_confirm_timer > 0:
                # Second click within timer — perform reset
                sim.reset_game()
                sim.reset_confirm_timer = 0.0
            else:
                # First click — start confirmation
                sim.reset_confirm_timer = 3.0

        # Draw button
        if sim.reset_confirm_timer > 0:
            bg_color = Color(180, 50, 50, 255) if hover_reset else Color(140, 40, 40, 255)
            label = "Click again to confirm"
        else:
            bg_color = Color(80, 40, 40, 255) if hover_reset else Color(60, 30, 30, 255)
            label = "Reset Game"

        draw_rectangle(btn_x, btn_y, btn_w, btn_h, bg_color)
        draw_rectangle_lines(btn_x, btn_y, btn_w, btn_h, Color(120, 60, 60, 255))
        lw = _measure(label, font_sm)
        draw_text(label, btn_x + (btn_w - lw) // 2, btn_y + 7, font_sm, text_color)

        # ── Export / Import buttons ──────────────────────────────────
        if self.save_dir is not None:
            from game.save import export_save, import_save_from_file

            ei_y = btn_y + btn_h + 12
            ei_btn_w = 74
            ei_btn_h = 26
            gap = 10
            total_w = ei_btn_w * 2 + gap
            ei_start_x = content_x + (content_w - total_w) // 2

            # Export button
            ex_x = ei_start_x
            hover_export = (ex_x <= mouse_x <= ex_x + ei_btn_w and
                            ei_y <= mouse_y <= ei_y + ei_btn_h)
            ex_bg = Color(60, 80, 60, 255) if hover_export else Color(40, 60, 40, 255)
            draw_rectangle(ex_x, ei_y, ei_btn_w, ei_btn_h, ex_bg)
            draw_rectangle_lines(ex_x, ei_y, ei_btn_w, ei_btn_h, Color(80, 120, 80, 255))
            ex_lw = _measure("Export", font_sm)
            draw_text("Export", ex_x + (ei_btn_w - ex_lw) // 2, ei_y + 7, font_sm, text_color)

            if hover_export and mouse_pressed:
                if _WEB:
                    export_save(sim)
                else:
                    export_save(sim, self.save_dir / "save_export.txt")

            # Import button
            im_x = ei_start_x + ei_btn_w + gap
            hover_import = (im_x <= mouse_x <= im_x + ei_btn_w and
                            ei_y <= mouse_y <= ei_y + ei_btn_h)
            im_bg = Color(50, 60, 80, 255) if hover_import else Color(35, 45, 60, 255)
            draw_rectangle(im_x, ei_y, ei_btn_w, ei_btn_h, im_bg)
            draw_rectangle_lines(im_x, ei_y, ei_btn_w, ei_btn_h, Color(70, 90, 120, 255))
            im_lw = _measure("Import", font_sm)
            draw_text("Import", im_x + (ei_btn_w - im_lw) // 2, ei_y + 7, font_sm, text_color)

            if hover_import and mouse_pressed:
                import_save_from_file(sim)

    def draw_help_panel(self, sim: Simulation, layout: Layout) -> None:
        """Draw the Help panel in the grid content area."""
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

        content_x = layout.upgrade_grid_x
        content_y = layout.upgrade_grid_y + 4
        content_w = panel_w - (content_x - panel_x) * 2
        font_title = 14
        font_sm = 12
        line_h = 16

        # Title
        title = "Help"
        tw = _measure(title, font_title)
        draw_text(title, content_x + (content_w - tw) // 2, content_y, font_title, text_color)
        y = content_y + 28

        help_text = (
            "Left-click a shop item to select it, then left-click on the grid to place it. "
            "Right-click a grid cell to sell the component in it. "
            "Replace mode: when enabled, placing a component on an occupied cell will sell the existing "
            "component and replace it with the new one. "
            "Sell All Power button converts all stored power into money. "
            "Vent Heat button removes heat from the reactor hull. "
            "Components generate heat when active; manage it with vents and exchangers to prevent meltdowns. "
            "Fuel cells deplete over time; buy upgrades to improve their durability and output."
        )
        help_lines = _wrap_text(help_text, content_w, font_sm)
        for line in help_lines:
            lw = _measure(line, font_sm)
            draw_text(line, content_x + (content_w - lw) // 2, y, font_sm, text_color)
            y += line_h


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
    12: (1, 0), 13: (1, 1), 14: (1, 2), 15: (1, 3), 16: (1, 4), 17: (1, 5),
    22: (1, 6), 24: (1, 7), 18: (1, 8), 20: (1, 9), 21: (1, 10), 19: (1, 11),
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





def format_number_with_suffix(value: float, max_decimals: int = 3, min_decimals: int = 0) -> str:
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
