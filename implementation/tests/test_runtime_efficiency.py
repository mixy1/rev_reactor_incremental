from __future__ import annotations

import time

from game.grid import Grid
from game.save import _build_save_dict, _restore_with_catch_up
from game.simulation import MAX_CATCH_UP_TICKS, demo_simulation


def test_grid_neighbor_cache_survives_resize() -> None:
    grid = Grid(width=2, height=2, tile_size=16)

    assert set(grid.neighbors(0, 0)) == {(1, 0, 0), (0, 1, 0)}
    grid.resize(3, 2)
    assert set(grid.neighbors(1, 0)) == {(0, 0, 0), (2, 0, 0), (1, 1, 0)}


def test_upgrade_bonus_cache_invalidates_after_purchase() -> None:
    sim = demo_simulation()
    manager = sim.upgrade_manager
    upgrade = manager.upgrades[0]
    bonus = upgrade.bonuses[0]

    before = manager.get_upgrade_stat_bonus(bonus.component_type, bonus.stat_category)
    revision = manager.revision
    manager.purchase(upgrade.index, money=1e100, exotic_particles=1e100)
    after = manager.get_upgrade_stat_bonus(bonus.component_type, bonus.stat_category)

    assert manager.revision == revision + 1
    assert after != before


def test_clean_live_preview_does_not_recompute() -> None:
    sim = demo_simulation()
    calls = 0
    original = sim._estimate_generation_preview

    def counted_preview():
        nonlocal calls
        calls += 1
        return original()

    sim._estimate_generation_preview = counted_preview
    sim.refresh_live_preview()
    sim.refresh_live_preview()
    assert calls == 1

    sim._preview_dirty = True
    sim.refresh_live_preview()
    assert calls == 2


def test_catch_up_advances_ticks_and_respects_pause_and_cap() -> None:
    sim = demo_simulation()
    assert sim.catch_up(2.5) == 2
    assert sim.total_ticks == 2

    sim.paused = True
    assert sim.catch_up(100.0) == 0
    assert sim.total_ticks == 2

    capped = demo_simulation()
    assert capped.catch_up(24 * 60 * 60) == MAX_CATCH_UP_TICKS
    assert capped.total_ticks == MAX_CATCH_UP_TICKS


def test_timestamped_save_catches_up_on_restore() -> None:
    source = demo_simulation()
    data = _build_save_dict(source)
    data["saved_at_unix_ms"] = 1_000

    restored = demo_simulation()
    restored.pending_catch_up_seconds = 99.0  # owed to the previous game: dropped
    assert _restore_with_catch_up(restored, data, now_ms=3_500)
    # Left for main.py to run on the next frame, after showing the overlay
    assert restored.pending_catch_up_seconds == 2.5
    assert restored.total_ticks == 0
    assert restored.catch_up(restored.pending_catch_up_seconds) == 2
    assert restored.total_ticks == 2

    data["paused"] = True
    paused = demo_simulation()
    assert _restore_with_catch_up(paused, data, now_ms=30_000)
    assert paused.pending_catch_up_seconds == 0.0
    assert paused.total_ticks == 0


def test_save_before_pending_catch_up_runs_keeps_the_time_owed() -> None:
    sim = demo_simulation()
    sim.pending_catch_up_seconds = 120.0
    saved_ms = int(time.time() * 1000.0)
    data = _build_save_dict(sim)
    restored = demo_simulation()
    # Loaded 30 s after saving: the 120 s not yet run plus the 30 s since.
    assert _restore_with_catch_up(restored, data, now_ms=saved_ms + 30_000)
    assert abs(restored.pending_catch_up_seconds - 150.0) < 1.0


def test_iter_catch_up_in_slices_matches_catch_up() -> None:
    whole = demo_simulation()
    sliced = demo_simulation()
    assert whole.catch_up(600.4) == 600
    progress = list(sliced.iter_catch_up(600.4))
    assert progress[0] == (1, 600) and progress[-1] == (600, 600)
    assert sliced.total_ticks == whole.total_ticks == 600
    assert sliced._tick_accumulator == whole._tick_accumulator
    assert sliced.last_catch_up_ticks == whole.last_catch_up_ticks
    assert sliced.reactor_heat == whole.reactor_heat
    assert sliced.stored_power == whole.stored_power


def test_iter_catch_up_stopped_early_drops_the_rest() -> None:
    sim = demo_simulation()
    steps = sim.iter_catch_up(600.0)
    for done, _total in steps:
        if done == 100:
            break
    steps.close()
    assert sim.total_ticks == 100
    assert sim.last_catch_up_ticks == 100
    assert sim._tick_accumulator < 1.0  # not left to burst through step()


def test_tick_layout_cache_follows_layout_changes() -> None:
    """Replacing a part keeps the part count the same, and the live preview
    (refreshed every frame) consumes the layout-changed flag before the next
    tick; the cached tick layout must still be rebuilt."""
    from game.simulation import ReactorComponent

    def build():
        sim = demo_simulation()
        sim.grid = Grid(width=6, height=4, tile_size=16)
        by = {c.name: c for c in sim.shop_components}
        layout = ["VXVXVI", "XF2FXV", "VXCXVX", "OXVXFX"]
        names = {"V": "Vent2", "X": "Exchanger2", "I": "Inlet2", "O": "Outlet2", "F": "Fuel2-4",
                 "2": "Reflector2", "C": "Coolant2"}
        for y, row in enumerate(layout):
            for x, ch in enumerate(row):
                sim.place_component(x, y, ReactorComponent(stats=by[names[ch]]))
        return sim, by

    cached, by = build()
    fresh, _ = build()
    for step in range(120):
        if step in (30, 70):  # replace a vent next to an exchanger with a coolant cell, and back
            name = "Coolant3" if step == 30 else "Vent2"
            for sim in (cached, fresh):
                sim.remove_component(2, 0, 0)
                sim.place_component(2, 0, ReactorComponent(stats=by[name]))
                sim.refresh_live_preview()  # as the game does every frame
        fresh._layout_cache = None  # rebuilt from scratch every tick
        cached.catch_up(1.0)
        fresh.catch_up(1.0)
        assert [(c.grid_x, c.grid_y, c.heat, c.durability) for c in cached.components] == \
               [(c.grid_x, c.grid_y, c.heat, c.durability) for c in fresh.components]
        assert cached.reactor_heat == fresh.reactor_heat and cached.stored_power == fresh.stored_power
