from __future__ import annotations

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
    assert _restore_with_catch_up(restored, data, now_ms=3_500)
    assert restored.total_ticks == 2
    assert restored.last_catch_up_ticks == 2

    data["paused"] = True
    paused = demo_simulation()
    assert _restore_with_catch_up(paused, data, now_ms=30_000)
    assert paused.total_ticks == 0
    assert paused.last_catch_up_ticks == 0
