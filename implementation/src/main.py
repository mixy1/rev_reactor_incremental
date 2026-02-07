from __future__ import annotations

import math
from pathlib import Path

from raylib_compat import (
    Color,
    Texture2D,
    WindowShouldClose,
    begin_drawing,
    begin_scissor_mode,
    clear_background,
    close_window,
    draw_rectangle,
    draw_text,
    draw_texture_pro,
    end_drawing,
    end_scissor_mode,
    get_frame_time,
    get_mouse_position,
    get_mouse_wheel_move,
    get_time,
    is_key_pressed,
    init_window,
    is_mouse_button_down,
    is_mouse_button_pressed,
    load_texture,
    measure_text,
    MOUSE_BUTTON_LEFT,
    MOUSE_BUTTON_MIDDLE,
    MOUSE_BUTTON_RIGHT,
    KEY_F1,
    KEY_F2,
    KEY_F3,
    KEY_F4,
    KEY_F5,
    KEY_SPACE,
    KEY_ESCAPE,
    KEY_X,
    KEY_Y,
    Rectangle,
    Vector2,
    set_exit_key,
    set_target_fps,
    take_screenshot,
    unload_texture,
)
from game.simulation import Simulation
from game.save import save_game, load_game

from assets import sprite_path, reference_path
from game.layout import load_layout
from game.grid import Grid
from game.simulation import ReactorComponent, ExplosionEffect, demo_simulation
from game.ui import Ui


def _load_texture(path: Path) -> Texture2D:
    return load_texture(str(path))


def main() -> None:
    layout = load_layout()
    init_window(layout.window_width, layout.window_height, "Rev Reactor (Prototype)")
    set_exit_key(0)  # Disable raylib's default ESC-to-close
    set_target_fps(60)

    sim = demo_simulation()
    save_path = Path(__file__).resolve().parent / "save.json"

    heat_tex = _load_texture(sprite_path("Heat.png"))
    power_tex = _load_texture(sprite_path("Power.png"))
    grid_tex = _load_texture(sprite_path("GridTile.png"))
    grid_full = _load_texture(sprite_path("MainGrid.png"))
    grid_backer = _load_texture(sprite_path("GridBacker.png"))
    grid_frame = _load_texture(sprite_path("GridFrame.png"))
    side_grid = _load_texture(sprite_path("SideGrid.png"))
    btn_big = _load_texture(sprite_path("ButtonBIG.png"))
    btn_big_hover = _load_texture(sprite_path("ButtonBIGHover.png"))
    btn_big_pressed = _load_texture(sprite_path("ButtonBIGClicked.png"))
    btn_small = _load_texture(sprite_path("ButtonSMALL.png"))
    btn_small_hover = _load_texture(sprite_path("ButtonSMALLHover.png"))
    btn_small_pressed = _load_texture(sprite_path("ButtonSMALLClicked.png"))
    btn_med = _load_texture(sprite_path("ButtonMED.png"))
    btn_med_hover = _load_texture(sprite_path("ButtonMEDHover.png"))
    btn_med_pressed = _load_texture(sprite_path("ButtonMEDClicked.png"))
    btn_back = _load_texture(sprite_path("ButtonBACK.png"))
    btn_back_hover = _load_texture(sprite_path("ButtonBACKHover.png"))
    btn_back_pressed = _load_texture(sprite_path("ButtonBACKClicked.png"))
    btn_play = _load_texture(sprite_path("ButtonPLAY.png"))
    btn_play_hover = _load_texture(sprite_path("ButtonPLAYHover.png"))
    btn_play_pressed = _load_texture(sprite_path("ButtonPLAYClicked.png"))
    btn_pause = _load_texture(sprite_path("ButtonPAUSE.png"))
    btn_pause_hover = _load_texture(sprite_path("ButtonPAUSEHover.png"))
    btn_pause_pressed = _load_texture(sprite_path("ButtonPAUSEClicked.png"))
    btn_replace = _load_texture(sprite_path("ButtonREPLACE.png"))
    btn_replace_hover = _load_texture(sprite_path("ButtonREPLACEHover.png"))
    btn_replace_pressed = _load_texture(sprite_path("ButtonREPLACEClicked.png"))
    btn_noreplace = _load_texture(sprite_path("ButtonNOREPLACE.png"))
    btn_noreplace_hover = _load_texture(sprite_path("ButtonNOREPLACEHover.png"))
    btn_noreplace_pressed = _load_texture(sprite_path("ButtonNOREPLACEClicked.png"))
    top_banner = _load_texture(sprite_path("TopBanner.png"))
    store_block = _load_texture(sprite_path("Block.png"))
    tab_power = _load_texture(sprite_path("Power.png"))
    tab_power_hover = _load_texture(sprite_path("PowerHover.png"))
    tab_power_pressed = _load_texture(sprite_path("PowerClicked.png"))
    tab_heat = _load_texture(sprite_path("Heat.png"))
    tab_heat_hover = _load_texture(sprite_path("HeatHover.png"))
    tab_heat_pressed = _load_texture(sprite_path("HeatClicked.png"))
    tab_experimental = _load_texture(sprite_path("Experimental.png"))
    tab_experimental_hover = _load_texture(sprite_path("ExperimentalHover.png"))
    tab_experimental_pressed = _load_texture(sprite_path("ExperimentalClicked.png"))
    tab_arcane = _load_texture(sprite_path("Arcane.png"))
    tab_arcane_hover = _load_texture(sprite_path("ArcaneHover.png"))
    tab_arcane_pressed = _load_texture(sprite_path("ArcaneClicked.png"))
    icon_btn = _load_texture(sprite_path("IconButton.png"))
    icon_btn_hover = _load_texture(sprite_path("IconHoverButton.png"))
    icon_btn_pressed = _load_texture(sprite_path("IconClickedButton.png"))
    icon_btn_locked = _load_texture(sprite_path("IconButtonLocked.png"))
    reference_names = [
        "screenshot-main.png",
        "screenshot-upgrades.png",
        "screenshot-statistics.png",
        "screenshot-prestige.png",
        "screenshot-help.png",
        "screenshot-options.png",
    ]
    reference_textures = [(_load_texture(reference_path(name)), name) for name in reference_names]

    # Explosion animation: 12 frames (RE: Explosion MonoBehaviour)
    explosion_textures = [_load_texture(sprite_path(f"Explosion_{i}.png")) for i in range(12)]

    if sim.grid is None or sim.grid.base_width != layout.grid_width or sim.grid.base_height != layout.grid_height:
        sim.grid = Grid(
            width=layout.grid_width,
            height=layout.grid_height,
            tile_size=32,
            origin_x=layout.grid_origin_x,
            origin_y=layout.grid_origin_y,
            cell_size=layout.grid_cell_size,
            tile_texture=grid_tex,
            base_width=layout.grid_width,
            base_height=layout.grid_height,
        )
    grid = sim.grid
    grid.tile_texture = grid_tex
    grid.full_texture = grid_full

    component_sprites = {}
    for comp in sim.shop_components:
        if comp.sprite_name in component_sprites:
            continue
        try:
            component_sprites[comp.sprite_name] = _load_texture(sprite_path(comp.sprite_name))
        except FileNotFoundError:
            continue

    # Load upgrade icon sprites: map upgrade icon/category paths to component sprites
    _UPGRADE_ICON_MAP = {
        "UI/Upgrade Icons/Fuel1": "Fuel1-1.png",
        "UI/Upgrade Icons/Fuel2": "Fuel2-1.png",
        "UI/Upgrade Icons/Fuel3": "Fuel3-1.png",
        "UI/Upgrade Icons/Fuel4": "Fuel4-1.png",
        "UI/Upgrade Icons/Fuel5": "Fuel5-1.png",
        "UI/Upgrade Icons/Fuel6": "Fuel6-1.png",
        "UI/Upgrade Icons/Vent": "Vent1.png",
        "UI/Upgrade Icons/Exchanger": "Exchanger1.png",
        "UI/Upgrade Icons/Coolant": "Coolant1.png",
        "UI/Upgrade Icons/Reflector": "Reflector1.png",
        "UI/Upgrade Icons/Wiring": "Capacitor1.png",
        "UI/Upgrade Icons/Alloys": "Plate1UP.png",
        "UI/Upgrade Icons/Heatsink": "Plate1UP.png",
        "UI/Upgrade Icons/PowerLines": "Capacitor1.png",
        "UI/Upgrade Icons/Piping": "Plate1.png",
        "UI/Upgrade Icons/Chronometer": "Clock.png",
        "UI/Upgrade Icons/Bartering": "Explosion_0.png",
        "UI/Upgrade Icons/Discount": "GridTile.png",
        "UI/Upgrade Icons/Research": "Fuel7-1.png",
        "UI/Upgrade Icons/ActiveVenting": "Capacitor1.png",
        "UI/Upgrade Icons/ActiveExchanger": "Capacitor1.png",
        "UI/Upgrade Icons/ReinforcedExchanger": "Plate1.png",
        "UI/Upgrade Icons/InfusedFuel": "Fuel5-4.png",
        "UI/Upgrade Icons/UnleashedFuel": "Fuel6-4.png",
        "UI/Upgrade Icons/QuantumBuffering": "Capacitor5.png",
        "UI/Upgrade Icons/FullSpectrum": "Reflector5.png",
        "UI/Upgrade Icons/FluidHyperdynamics": "Vent5.png",
        "UI/Upgrade Icons/FractalPiping": "Exchanger5.png",
        "UI/Upgrade Icons/ExpCapacitor": "Capacitor6.png",
        "UI/Upgrade Icons/VortexCooling": "Coolant6.png",
        "UI/Upgrade Icons/Ultracryonics": "Coolant5.png",
        "UI/Upgrade Icons/PhlebotinumCore": "Plate5.png",
        "UI/Upgrade Icons/RefactoredProtium": "Fuel7-2.png",
        "UI/Upgrade Icons/Monastium": "Fuel8-1.png",
        "UI/Upgrade Icons/Kymium": "Fuel9-1.png",
        "UI/Upgrade Icons/Discurrium": "Fuel10-1.png",
        "UI/Upgrade Icons/Stavrium": "Fuel11-1.png",
        # Category overlay sprites
        "UI/Upgrade Icons/GenericPlus": "GenericPlus.png",
        "UI/Upgrade Icons/GenericPower": "GenericPower.png",
        "UI/Upgrade Icons/GenericInfinity": "GenericInfinity.png",
        "UI/Upgrade Icons/GenericHeat": "GenericHeat.png",
    }
    upgrade_sprites = {}
    for icon_path, sprite_name in _UPGRADE_ICON_MAP.items():
        if icon_path in upgrade_sprites:
            continue
        try:
            upgrade_sprites[icon_path] = _load_texture(sprite_path(sprite_name))
        except FileNotFoundError:
            pass

    ui = Ui(
        heat_icon=heat_tex,
        power_icon=power_tex,
        button_base=btn_big,
        button_hover=btn_big_hover,
        button_pressed=btn_big_pressed,
        icon_button=icon_btn,
        icon_button_hover=icon_btn_hover,
        icon_button_pressed=icon_btn_pressed,
        icon_button_locked=icon_btn_locked,
        store_block=store_block,
        store_tab_power=tab_power,
        store_tab_power_hover=tab_power_hover,
        store_tab_power_pressed=tab_power_pressed,
        store_tab_heat=tab_heat,
        store_tab_heat_hover=tab_heat_hover,
        store_tab_heat_pressed=tab_heat_pressed,
        store_tab_experimental=tab_experimental,
        store_tab_experimental_hover=tab_experimental_hover,
        store_tab_experimental_pressed=tab_experimental_pressed,
        store_tab_arcane=tab_arcane,
        store_tab_arcane_hover=tab_arcane_hover,
        store_tab_arcane_pressed=tab_arcane_pressed,
        top_banner=top_banner,
        upgrade_sprites=upgrade_sprites,
    )

    ui.save_dir = save_path.parent
    load_game(sim, save_path)

    show_reference = False
    reference_index = 0
    last_place_cell = None
    last_sell_cell = None
    prev_mx, prev_my = 0.0, 0.0

    try:
        while not WindowShouldClose():
            dt = get_frame_time()

            # RE fn 10408 lines 387652-387665: ticks only run when
            # NOT manually paused AND no UI panel is open.  Controller+0x28
            # holds a pointer-to-panel; when *it != 0 a panel is active and
            # ticks are suppressed (timer reset to Time.time, preventing
            # catch-up).  Our equivalent: view_mode != "reactor" acts as the
            # implicit panel-open flag.
            if not sim.paused and sim.view_mode == "reactor":
                sim.step(dt)
            else:
                # RE: else branch resets tick timer → prevent accumulated
                # dt from causing a burst of ticks on unpause/panel close.
                sim._tick_accumulator = 0.0

            # Explosion animations run even when paused (cosmetic only)
            sim.update_explosions(dt)

            # ── Keyboard events ──────────────────────────────────────
            if is_key_pressed(KEY_F1):
                show_reference = not show_reference
            if is_key_pressed(KEY_F2):
                reference_index = (reference_index + 1) % len(reference_textures)
            if is_key_pressed(KEY_F3):
                reference_index = (reference_index - 1) % len(reference_textures)

            # F4 = take debug screenshot (saved to CWD by raylib)
            if is_key_pressed(KEY_F4):
                import time
                ts = time.strftime("%Y%m%d_%H%M%S")
                fname = f"debug_{sim.view_mode}_{ts}.png"
                take_screenshot(fname)

            # Space = toggle pause (RE: line 387964, writes PauseButton.IsToggled)
            if is_key_pressed(KEY_SPACE):
                sim.paused = not sim.paused

            # ESC: close overlay if open, else deselect (RE: line 387898-387908)
            if is_key_pressed(KEY_ESCAPE):
                if sim.view_mode != "reactor":
                    sim.view_mode = "reactor"
                else:
                    sim.selected_component_index = -1

            # X: debug — multiply money by 10
            if is_key_pressed(KEY_X):
                sim.store.money = max(sim.store.money * 10, 10.0)

            # Y: debug — multiply exotic particles by 10
            if is_key_pressed(KEY_Y):
                sim.store.exotic_particles = max(sim.store.exotic_particles * 10, 10.0)

            # ── Mouse state ──────────────────────────────────────────
            mouse = get_mouse_position()
            mx = mouse.x if hasattr(mouse, "x") else mouse[0]
            my = mouse.y if hasattr(mouse, "y") else mouse[1]

            # ── Scroll / pan input (before grid clicks) ────────────────
            scrollbar_consumed = False
            if sim.view_mode == "reactor" and sim.grid is not None:
                wheel = get_mouse_wheel_move()
                middle_down = is_mouse_button_down(MOUSE_BUTTON_MIDDLE)
                scrollbar_consumed = sim.grid.handle_scrollbar_drag(
                    mx, my,
                    mouse_down=is_mouse_button_down(MOUSE_BUTTON_LEFT),
                    mouse_pressed=is_mouse_button_pressed(MOUSE_BUTTON_LEFT),
                )
                sim.grid.handle_scroll_input(
                    mx, my, prev_mx, prev_my,
                    middle_down=middle_down,
                    wheel_move=wheel,
                )

            # ── Button: Vent Heat ─────────────────────────────────────
            bw, bh = btn_big.width, btn_big.height
            vent_x, vent_y = layout.vent_x, layout.vent_y
            hover_vent = vent_x <= mx <= vent_x + bw and vent_y <= my <= vent_y + bh
            pressed_vent = hover_vent and is_mouse_button_down(MOUSE_BUTTON_LEFT)
            if hover_vent and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                sim.vent_heat()

            # ── Button: Sell Power / Scrounge ─────────────────────────
            sell_x, sell_y = layout.sell_x, layout.sell_y
            hover_sell = sell_x <= mx <= sell_x + bw and sell_y <= my <= sell_y + bh
            pressed_sell = hover_sell and is_mouse_button_down(MOUSE_BUTTON_LEFT)
            if hover_sell and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                sim.sell_or_scrounge()

            # ── Button: Pause (toggle) ────────────────────────────────
            pw, ph = btn_play.width, btn_play.height
            hover_pause = (layout.pause_x <= mx <= layout.pause_x + pw and
                           layout.pause_y <= my <= layout.pause_y + ph)
            pressed_pause = hover_pause and is_mouse_button_down(MOUSE_BUTTON_LEFT)
            if hover_pause and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                sim.paused = not sim.paused

            # ── Button: Replace (toggle) ──────────────────────────────
            rw, rh = btn_replace.width, btn_replace.height
            hover_replace = (layout.replace_x <= mx <= layout.replace_x + rw and
                             layout.replace_y <= my <= layout.replace_y + rh)
            pressed_replace = hover_replace and is_mouse_button_down(MOUSE_BUTTON_LEFT)
            if hover_replace and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                sim.replace_mode = not sim.replace_mode

            # ── Button: Upgrades ───────────────────────────────────────
            uw, uh = btn_med.width, btn_med.height
            hover_upgrades = (layout.main_upgrades_x <= mx <= layout.main_upgrades_x + uw and
                              layout.main_upgrades_y <= my <= layout.main_upgrades_y + uh)
            if hover_upgrades and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                if sim.view_mode == "upgrades":
                    sim.view_mode = "reactor"
                else:
                    sim.view_mode = "upgrades"

            # ── Button: Prestige ───────────────────────────────────────
            hover_prestige = (layout.prestige_upgrades_x <= mx <= layout.prestige_upgrades_x + uw and
                              layout.prestige_upgrades_y <= my <= layout.prestige_upgrades_y + uh)
            if hover_prestige and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                if sim.view_mode == "prestige":
                    sim.view_mode = "reactor"
                else:
                    sim.view_mode = "prestige"

            # ── Button: Back ───────────────────────────────────────────
            bkw, bkh = btn_back.width, btn_back.height
            hover_back = (layout.back_x <= mx <= layout.back_x + bkw and
                          layout.back_y <= my <= layout.back_y + bkh)
            if hover_back and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                sim.view_mode = "reactor"

            # ── Bottom buttons: Options / Statistics / Help ───────────
            sw, sh = btn_small.width, btn_small.height

            hover_options = (layout.options_x <= mx <= layout.options_x + sw and
                             layout.options_y <= my <= layout.options_y + sh)
            if hover_options and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                sim.view_mode = "reactor" if sim.view_mode == "options" else "options"

            hover_stats = (layout.stats_x_btn <= mx <= layout.stats_x_btn + sw and
                           layout.stats_y_btn <= my <= layout.stats_y_btn + sh)
            if hover_stats and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                sim.view_mode = "reactor" if sim.view_mode == "statistics" else "statistics"

            hover_help = (layout.help_x <= mx <= layout.help_x + sw and
                          layout.help_y <= my <= layout.help_y + sh)
            if hover_help and is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
                sim.view_mode = "reactor" if sim.view_mode == "help" else "help"

            # Clear confirmation state when navigating away from options
            # RE: fn 10489 — binary clears all confirmation state on navigation
            if sim.view_mode != "options":
                sim.prestige_confirming = False
                sim.prestige_can_refund = False
                sim.reset_confirm_timer = 0.0

            # ── Grid: Left click — place / replace (reactor view only) ──
            if sim.view_mode == "reactor" and sim.grid is not None and is_mouse_button_down(MOUSE_BUTTON_LEFT) and not scrollbar_consumed:
                cell = sim.grid.screen_to_cell(int(mx), int(my))
                if cell is not None and cell != last_place_cell:
                    cx, cy = cell
                    selected = sim.selected_component()
                    if selected is not None:
                        existing = sim.grid.get(cx, cy, 0)
                        if existing is None:
                            # Empty cell: place if affordable
                            cost = sim.get_component_cost(selected)
                            if sim.store.money >= cost:
                                if sim.place_component(cx, cy, ReactorComponent(stats=selected)):
                                    sim.store.money -= cost
                        elif Simulation.can_replace(existing, selected):
                            # Click-to-replace: always active for compatible components
                            cost = sim.get_component_cost(selected)
                            refund = Simulation.sell_value(existing)
                            if sim.store.money + refund >= cost:
                                sim.remove_component(cx, cy)
                                sim.store.money += refund
                                if sim.place_component(cx, cy, ReactorComponent(stats=selected)):
                                    sim.store.money -= cost
                    last_place_cell = cell
            elif not is_mouse_button_down(MOUSE_BUTTON_LEFT):
                last_place_cell = None

            # ── Right click — sell / deselect ────────────────────────
            # RE: Two deselect paths in unnamed_function_10410:
            #   1. Mouse NOT over grid cell + RMB down → deselect (line 388001)
            #   2. Mouse over empty grid cell + RMB down → deselect (line 388094)
            #   Mouse over occupied grid cell + RMB held → sell (line 388084)
            if sim.view_mode == "reactor" and sim.grid is not None and is_mouse_button_down(MOUSE_BUTTON_RIGHT):
                cell = sim.grid.screen_to_cell(int(mx), int(my))
                if cell is not None:
                    if cell != last_sell_cell:
                        cx, cy = cell
                        existing = sim.grid.get(cx, cy, 0)
                        if existing is not None:
                            refund = Simulation.sell_value(existing)
                            sim.remove_component(cx, cy)
                            sim.store.money += refund
                        else:
                            sim.selected_component_index = -1
                        last_sell_cell = cell
                else:
                    # Not over grid: deselect on press (line 388001-388004)
                    if is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
                        sim.selected_component_index = -1
            elif not is_mouse_button_down(MOUSE_BUTTON_RIGHT):
                last_sell_cell = None

            begin_drawing()
            clear_background(Color(18, 18, 22, 255))

            if show_reference and reference_textures:
                ref_tex, ref_name = reference_textures[reference_index]
                src = Rectangle(0, 0, ref_tex.width, ref_tex.height)
                dst = Rectangle(0, 0, layout.window_width, layout.window_height)
                origin = Vector2(0, 0)
                draw_texture_pro(ref_tex, src, dst, origin, 0.0, Color(255, 255, 255, 160))
                draw_text(
                    f"Reference: {ref_name}",
                    16,
                    layout.window_height - 20,
                    12,
                    Color(200, 200, 200, 255),
                )

            draw_texture_pro(
                side_grid,
                Rectangle(0, 0, side_grid.width, side_grid.height),
                Rectangle(
                    layout.left_panel_x,
                    layout.left_panel_y,
                    layout.left_panel_w,
                    layout.left_panel_h,
                ),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )

            frame_x = layout.grid_frame_x
            frame_y = layout.grid_frame_y
            backer_x = frame_x + layout.grid_backer_offset_x
            backer_y = frame_y + layout.grid_backer_offset_y

            draw_texture_pro(
                grid_backer,
                Rectangle(0, 0, grid_backer.width, grid_backer.height),
                Rectangle(backer_x, backer_y, grid_backer.width, grid_backer.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )

            if sim.view_mode == "reactor":
                # ── Reactor grid view ──────────────────────────────────
                grid.draw(Color(255, 255, 255, 120))

                use_scissor = sim.grid is not None and sim.grid.needs_scroll

                if use_scissor:
                    begin_scissor_mode(
                        sim.grid.origin_x, sim.grid.origin_y,
                        sim.grid.viewport_w, sim.grid.viewport_h,
                    )

                if sim.grid is not None:
                    cell_sz = sim.grid.cell_size
                    bar_h = max(2, cell_sz // 10)
                    bar_margin = 2
                    bar_w = cell_sz - bar_margin * 2

                    for gx, gy, _gz, component in sim.grid.iter_cells():
                        if component is None:
                            continue
                        tex = component_sprites.get(component.stats.sprite_name)
                        if tex is None:
                            continue
                        px, py = sim.grid.cell_to_screen(gx, gy)
                        scale = min(1.0, cell_sz / max(1, tex.width), cell_sz / max(1, tex.height))
                        draw_w = tex.width * scale
                        draw_h = tex.height * scale
                        offset_x = (cell_sz - draw_w) * 0.5
                        offset_y = (cell_sz - draw_h) * 0.5

                        if component.depleted:
                            tint = Color(100, 100, 100, 255)
                        else:
                            tint = Color(255, 255, 255, 255)

                        draw_texture_pro(
                            tex,
                            Rectangle(0, 0, tex.width, tex.height),
                            Rectangle(px + offset_x, py + offset_y, draw_w, draw_h),
                            Vector2(0, 0),
                            0.0,
                            tint,
                        )

                        bars_drawn = 0
                        stats = component.stats

                        eff_hc = sim.get_effective_heat_capacity(component)
                        if eff_hc > 0.0 and not component.depleted:
                            raw_fill = component.heat / eff_hc
                            fill = min(1.0, max(0.0, raw_fill))
                            bar_y = py + cell_sz - bar_margin - bar_h
                            if raw_fill > 0.8:
                                pulse = abs(math.sin(get_time() * 6.0))
                                bg_r = int(40 + 80 * pulse)
                                draw_rectangle(
                                    int(px + bar_margin), int(bar_y),
                                    int(bar_w), int(bar_h),
                                    Color(bg_r, 10, 10, 200),
                                )
                            else:
                                draw_rectangle(
                                    int(px + bar_margin), int(bar_y),
                                    int(bar_w), int(bar_h),
                                    Color(40, 10, 10, 180),
                                )
                            if fill > 0.001:
                                if raw_fill > 0.8:
                                    pulse = abs(math.sin(get_time() * 6.0))
                                    r = 255
                                    g = int(120 + 135 * pulse)
                                    b = int(60 + 195 * pulse)
                                else:
                                    r = int(180 + 75 * fill)
                                    g = int(60 * (1.0 - fill))
                                    b = 20
                                draw_rectangle(
                                    int(px + bar_margin), int(bar_y),
                                    int(bar_w * fill), int(bar_h),
                                    Color(min(255, r), g, b, 220),
                                )
                            bars_drawn += 1

                        eff_dur = sim.get_effective_max_durability(component)
                        if eff_dur > 0.0:
                            fill = min(1.0, max(0.0, component.durability / eff_dur))
                            bar_y = py + cell_sz - bar_margin - bar_h * (bars_drawn + 1) - bars_drawn
                            draw_rectangle(
                                int(px + bar_margin), int(bar_y),
                                int(bar_w), int(bar_h),
                                Color(10, 30, 10, 180),
                            )
                            if fill > 0.001:
                                if fill > 0.5:
                                    r = int(220 * (1.0 - fill) * 2)
                                    g = 200
                                else:
                                    r = 220
                                    g = int(200 * fill * 2)
                                draw_rectangle(
                                    int(px + bar_margin), int(bar_y),
                                    int(bar_w * fill), int(bar_h),
                                    Color(r, g, 30, 220),
                                )
                            bars_drawn += 1

                # Draw explosion animations on top of grid cells
                if sim.grid is not None:
                    cell_sz = sim.grid.cell_size
                    for effect in sim.explosions:
                        if 0 <= effect.frame < 12:
                            ex_tex = explosion_textures[effect.frame]
                            ex_scale = cell_sz / max(1, ex_tex.height)
                            ex_w = ex_tex.width * ex_scale
                            ex_h = ex_tex.height * ex_scale
                            ex_ox = (cell_sz - ex_w) * 0.5
                            ex_oy = (cell_sz - ex_h) * 0.5
                            ex_sx, ex_sy = sim.grid.cell_to_screen(effect.grid_x, effect.grid_y)
                            draw_texture_pro(
                                ex_tex,
                                Rectangle(0, 0, ex_tex.width, ex_tex.height),
                                Rectangle(ex_sx + ex_ox, ex_sy + ex_oy, ex_w, ex_h),
                                Vector2(0, 0),
                                0.0,
                                Color(255, 255, 255, 255),
                            )

                if use_scissor:
                    end_scissor_mode()

            elif sim.view_mode in ("upgrades", "prestige"):
                # ── Upgrade/Prestige grid view ─────────────────────────
                ui.draw_upgrade_grid(
                    sim, layout,
                    mouse_x=mx, mouse_y=my,
                    mouse_pressed=is_mouse_button_pressed(MOUSE_BUTTON_LEFT),
                )
            elif sim.view_mode == "statistics":
                ui.draw_statistics_panel(sim, layout)
            elif sim.view_mode == "options":
                ui.draw_options_panel(sim, layout, mouse_x=mx, mouse_y=my,
                                      mouse_pressed=is_mouse_button_pressed(MOUSE_BUTTON_LEFT),
                                      dt=dt)
            elif sim.view_mode == "help":
                ui.draw_help_panel(sim, layout)

            draw_texture_pro(
                grid_frame,
                Rectangle(0, 0, grid_frame.width, grid_frame.height),
                Rectangle(frame_x, frame_y, grid_frame.width, grid_frame.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )

            # Scrollbars drawn on top of grid frame so they're visible
            if sim.view_mode == "reactor" and sim.grid is not None:
                sim.grid.draw_scrollbars()

            # Top-left upgrade tabs
            upg_tex = btn_med_pressed if sim.view_mode == "upgrades" else (btn_med_hover if hover_upgrades else btn_med)
            draw_texture_pro(
                upg_tex,
                Rectangle(0, 0, upg_tex.width, upg_tex.height),
                Rectangle(layout.main_upgrades_x, layout.main_upgrades_y, upg_tex.width, upg_tex.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )
            draw_text("Upgrades", layout.main_upgrades_x + 12, layout.main_upgrades_y + 6, 14, Color(230, 230, 230, 255))
            prs_tex = btn_med_pressed if sim.view_mode == "prestige" else (btn_med_hover if hover_prestige else btn_med)
            draw_texture_pro(
                prs_tex,
                Rectangle(0, 0, prs_tex.width, prs_tex.height),
                Rectangle(layout.prestige_upgrades_x, layout.prestige_upgrades_y, prs_tex.width, prs_tex.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )
            draw_text(
                "Prestige",
                layout.prestige_upgrades_x + 12,
                layout.prestige_upgrades_y + 6,
                14,
                Color(230, 230, 230, 255),
            )

            # Bottom buttons (Options / Statistics / Help)
            opt_tex = btn_small_pressed if sim.view_mode == "options" else (btn_small_hover if hover_options else btn_small)
            draw_texture_pro(
                opt_tex,
                Rectangle(0, 0, opt_tex.width, opt_tex.height),
                Rectangle(layout.options_x, layout.options_y, opt_tex.width, opt_tex.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )
            draw_text("Options", layout.options_x + 10, layout.options_y + 6, 12, Color(230, 230, 230, 255))
            stats_tex = btn_small_pressed if sim.view_mode == "statistics" else (btn_small_hover if hover_stats else btn_small)
            draw_texture_pro(
                stats_tex,
                Rectangle(0, 0, stats_tex.width, stats_tex.height),
                Rectangle(layout.stats_x_btn, layout.stats_y_btn, stats_tex.width, stats_tex.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )
            draw_text("Statistics", layout.stats_x_btn + 6, layout.stats_y_btn + 6, 12, Color(230, 230, 230, 255))
            help_tex = btn_small_pressed if sim.view_mode == "help" else (btn_small_hover if hover_help else btn_small)
            draw_texture_pro(
                help_tex,
                Rectangle(0, 0, help_tex.width, help_tex.height),
                Rectangle(layout.help_x, layout.help_y, help_tex.width, help_tex.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )
            draw_text("Help", layout.help_x + 16, layout.help_y + 6, 12, Color(230, 230, 230, 255))

            # Back button (visible only when in upgrade/prestige view)
            if sim.view_mode != "reactor":
                back_tex = btn_back_pressed if (hover_back and is_mouse_button_down(MOUSE_BUTTON_LEFT)) else (btn_back_hover if hover_back else btn_back)
                draw_texture_pro(
                    back_tex,
                    Rectangle(0, 0, back_tex.width, back_tex.height),
                    Rectangle(layout.back_x, layout.back_y, back_tex.width, back_tex.height),
                    Vector2(0, 0),
                    0.0,
                    Color(255, 255, 255, 255),
                )
                # ButtonBACK is 96x46; arrow takes ~28px on left, center text in remaining area
                back_text_x = layout.back_x + 28 + (96 - 28 - measure_text("Back", 14)) // 2
                draw_text("Back", back_text_x, layout.back_y + 16, 14, Color(230, 230, 230, 255))

            # Grid hover (fallback — shop hover in ui.draw() will override)
            sim.hover_component = None
            sim.hover_placed_component = None
            if sim.view_mode == "reactor" and sim.grid is not None:
                cell = sim.grid.screen_to_cell(int(mx), int(my))
                if cell is not None:
                    cx, cy = cell
                    grid_comp = sim.grid.get(cx, cy, 0)
                    if grid_comp is not None:
                        sim.hover_component = grid_comp.stats
                        sim.hover_placed_component = grid_comp

            ui.draw(
                sim,
                layout,
                hover_vent=hover_vent,
                pressed_vent=pressed_vent,
                hover_sell=hover_sell,
                pressed_sell=pressed_sell,
                mouse_x=mx,
                mouse_y=my,
                mouse_pressed=is_mouse_button_pressed(MOUSE_BUTTON_LEFT),
            )

            # Store icon overlay (draw after slots so icons sit on top)
            shop_components = sim.shop_components_for_page()
            slots = ui.store_item_slots(layout, shop_components)
            for _idx, (comp, rect) in enumerate(slots):
                tex = component_sprites.get(comp.sprite_name)
                if tex is None:
                    continue
                x, y, w, h = rect
                draw_w = tex.width
                draw_h = tex.height
                icon_x = x + (w - draw_w) / 2
                icon_y = y + (h - draw_h) / 2
                eff_cost = sim.get_component_cost(comp)
                if _idx == sim.selected_component_index and sim.store.money >= eff_cost:
                    tint = Color(120, 255, 120, 255)  # green tint for selected + affordable
                elif eff_cost > 0.0 and sim.store.money < eff_cost:
                    tint = Color(120, 120, 120, 255)  # gray for unaffordable
                else:
                    tint = Color(255, 255, 255, 255)
                draw_texture_pro(
                    tex,
                    Rectangle(0, 0, tex.width, tex.height),
                    Rectangle(icon_x, icon_y, draw_w, draw_h),
                    Vector2(0, 0),
                    0.0,
                    tint,
                )

            # Top-right toggle buttons (drawn after ui.draw so they render
            # on top of the info banner)
            # Play/Pause: PLAY sprites when running, PAUSE sprites when paused
            if sim.paused:
                if pressed_pause:
                    pause_tex = btn_pause_pressed
                elif hover_pause:
                    pause_tex = btn_pause_hover
                else:
                    pause_tex = btn_pause
            else:
                if pressed_pause:
                    pause_tex = btn_play_pressed
                elif hover_pause:
                    pause_tex = btn_play_hover
                else:
                    pause_tex = btn_play
            draw_texture_pro(
                pause_tex,
                Rectangle(0, 0, pause_tex.width, pause_tex.height),
                Rectangle(layout.pause_x, layout.pause_y, pause_tex.width, pause_tex.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )

            # Replace/NoReplace: REPLACE sprites when on, NOREPLACE when off
            if sim.replace_mode:
                if pressed_replace:
                    replace_tex = btn_replace_pressed
                elif hover_replace:
                    replace_tex = btn_replace_hover
                else:
                    replace_tex = btn_replace
            else:
                if pressed_replace:
                    replace_tex = btn_noreplace_pressed
                elif hover_replace:
                    replace_tex = btn_noreplace_hover
                else:
                    replace_tex = btn_noreplace
            draw_texture_pro(
                replace_tex,
                Rectangle(0, 0, replace_tex.width, replace_tex.height),
                Rectangle(layout.replace_x, layout.replace_y, replace_tex.width, replace_tex.height),
                Vector2(0, 0),
                0.0,
                Color(255, 255, 255, 255),
            )

            end_drawing()
            prev_mx, prev_my = mx, my
    finally:
        save_game(sim, save_path)
        unload_texture(heat_tex)
        unload_texture(power_tex)
        unload_texture(grid_tex)
        unload_texture(grid_full)
        unload_texture(grid_backer)
        unload_texture(grid_frame)
        unload_texture(side_grid)
        unload_texture(btn_big)
        unload_texture(btn_big_hover)
        unload_texture(btn_big_pressed)
        unload_texture(btn_small)
        unload_texture(btn_small_hover)
        unload_texture(btn_small_pressed)
        unload_texture(btn_med)
        unload_texture(btn_med_hover)
        unload_texture(btn_med_pressed)
        unload_texture(btn_back)
        unload_texture(btn_back_hover)
        unload_texture(btn_back_pressed)
        unload_texture(btn_play)
        unload_texture(btn_play_hover)
        unload_texture(btn_play_pressed)
        unload_texture(btn_pause)
        unload_texture(btn_pause_hover)
        unload_texture(btn_pause_pressed)
        unload_texture(btn_replace)
        unload_texture(btn_replace_hover)
        unload_texture(btn_replace_pressed)
        unload_texture(btn_noreplace)
        unload_texture(btn_noreplace_hover)
        unload_texture(btn_noreplace_pressed)
        unload_texture(top_banner)
        unload_texture(store_block)
        unload_texture(tab_power)
        unload_texture(tab_power_hover)
        unload_texture(tab_power_pressed)
        unload_texture(tab_heat)
        unload_texture(tab_heat_hover)
        unload_texture(tab_heat_pressed)
        unload_texture(tab_experimental)
        unload_texture(tab_experimental_hover)
        unload_texture(tab_experimental_pressed)
        unload_texture(tab_arcane)
        unload_texture(tab_arcane_hover)
        unload_texture(tab_arcane_pressed)
        unload_texture(icon_btn)
        unload_texture(icon_btn_hover)
        unload_texture(icon_btn_pressed)
        unload_texture(icon_btn_locked)
        for tex in explosion_textures:
            unload_texture(tex)
        for tex in component_sprites.values():
            unload_texture(tex)
        for tex, _ in reference_textures:
            unload_texture(tex)
        close_window()


if __name__ == "__main__":
    main()
