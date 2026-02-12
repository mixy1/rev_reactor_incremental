# Bevy Translation Plan (Python + raylib -> Rust + Bevy)

## Objective
- Translate the current playable Python prototype into a Rust + Bevy codebase without losing simulation behavior, save compatibility, or web deployment support.

## Current Baseline (implementation/src)
- `main.py` + `ui.py`: monolithic frame loop, panel routing (`reactor`, `upgrades`, `prestige`, `options`, `statistics`, `help`), and widget rendering/input.
- `simulation.py`: deterministic-ish tick pipeline, component placement/selling, prestige flow, explosion effects, and derived preview metrics.
- `catalog.py` + `component_types.json`: data loading/building for 75 component definitions with shop layout and metadata fallbacks.
- `upgrades.py` + `upgrade_data.json`: 51 upgrade definitions and multiplicative/additive stat bonus logic.
- `save.py`: JSON save/load, base64 export/import, and original encrypted Reactor Idle import path.
- `grid.py` + `layout.py` + `assets.py` + `raylib_compat.py`: grid viewport/scroll state, absolute UI layout values, asset lookup, and native/web backend split.

## Migration Principles
- Keep simulation logic engine-agnostic: port gameplay into pure Rust modules first, then bind into Bevy systems.
- Preserve save compatibility during migration: Rust side must read Python save JSON and exported base64 payloads before cutover.
- Replace behavior in thin vertical slices (data -> sim -> UI) to maintain continuous parity checks.

## Phased Plan

### Phase 0 - Baseline Lock + Parity Harness
Deliverables:
- [ ] Frozen Python baseline snapshot for comparison.
- [ ] Golden scenario fixtures (tick-by-tick outputs for money/power/heat/component states).
- [ ] Minimal parity checker spec (what must match exactly vs. approximately).

Work:
- [ ] Capture canonical fixtures from Python simulation for empty grid, early game, heat-heavy, and prestige scenarios.
- [ ] Define tolerance policy (`f64` exact for counters, epsilon for derived display values).
- [ ] Record known non-determinism sources (iteration order, float rounding, frame-time coupling).

### Phase 1 - Rust Workspace + Data Layer
Deliverables:
- [ ] Rust workspace under `implementation/` with crates for `core_sim`, `game_data`, and `bevy_app`.
- [ ] `serde` models for component, upgrade, and save payload schemas.
- [ ] Runtime loaders for `component_types.json`, `upgrade_data.json`, and string literal assets.

Work:
- [ ] Port `ComponentTypeStats`, upgrade structs, and save DTOs from Python dataclasses.
- [ ] Validate all 75 components and 51 upgrades deserialize with strict schema checks.
- [ ] Add CLI sanity command to print catalog/upgrades counts and required-upgrade locks.

### Phase 2 - Core Simulation Port (No Rendering)
Deliverables:
- [ ] Pure Rust tick pipeline equivalent to Python `Simulation._do_tick`.
- [ ] Ported systems: pulse distribution, durability drain, generation, heat exchange, hull exchange, venting, auto-sell, explosions.
- [ ] Parity tests against Phase 0 fixtures.

Work:
- [ ] Port grid/component state and placement/replacement/sell rules.
- [ ] Port prestige/reset logic and multiplier preparation path from upgrade manager.
- [ ] Add deterministic stepping API (`step_seconds`, `step_ticks`) for tests and headless verification.

### Phase 3 - Save/Import Compatibility
Deliverables:
- [ ] Rust save/load parity for current JSON schema.
- [ ] Export/import parity for base64 text format.
- [ ] Original encrypted import support parity decision (native Rust crypto vs. compatibility bridge).

Work:
- [ ] Port `_build_save_dict` / `_restore_from_dict` equivalents and version tagging.
- [ ] Validate backward compatibility with existing `save.json` and `save_export.txt`.
- [ ] Document encrypted import tradeoff and implementation path before UI wiring.

### Phase 4 - Bevy App Shell + UI Migration
Deliverables:
- [ ] Bevy app state machine matching current view modes.
- [ ] Grid rendering, component sprites, hover/selection, place/sell interactions.
- [ ] Upgrades/prestige/options/statistics/help panels with equivalent actions.

Work:
- [ ] Replace `main.py` input loop with Bevy schedules/states and event readers.
- [ ] Port absolute layout constants from `layout.py` into configurable Bevy UI resources.
- [ ] Port scroll/drag behavior for larger grids (Subspace expansion).

### Phase 5 - Web Build + Cutover
Deliverables:
- [ ] WebAssembly Bevy build integrated with existing site host.
- [ ] Native and web persistence parity.
- [ ] Python prototype deprecation checklist and handoff notes.

Work:
- [ ] Implement web save bridge equivalent to current localStorage/host bridge behavior.
- [ ] Profile frame time and memory on target browsers.
- [ ] Define cutover gate: fixture parity + manual gameplay checklist + save migration pass.

## Milestones
- [x] M0: Python module audit complete and migration plan documented.
- [ ] M1: Rust workspace + data loading parity (components/upgrades/save schema).
- [ ] M2: Headless simulation parity on golden fixtures.
- [ ] M3: Save/import compatibility validated on legacy and new saves.
- [ ] M4: Bevy UI/play loop reaches feature parity with Python prototype.
- [ ] M5: Web build accepted and Python runtime retired from active development.

## Risks and Mitigations
- Deterministic drift from float math/order changes: fixture-based tests at subsystem boundaries per phase.
- UI migration scope (`ui.py` + `main.py` are large): split by panel mode and ship panel-by-panel parity.
- Save compatibility regressions: keep schema versioning explicit and run migration tests on real save samples.
- Web target instability: validate wasm + persistence early (Phase 3/4), not at final cutover.
- Reverse-engineered edge-case regressions (experimental fuels, outlet bottlenecks, auto-replace): add dedicated scenario fixtures before ECS porting.

## Immediate Next Sprint (1 sprint)
- [ ] Create `implementation/` Rust workspace skeleton and crate boundaries.
- [ ] Port datamodel structs (`ComponentTypeStats`, upgrades, save payload) with serde.
- [ ] Implement loaders for `component_types.json` and `upgrade_data.json` with count/assert checks.
- [ ] Port grid primitives and component placement/removal/sell-value logic.
- [ ] Implement headless tick runner for a subset: multipliers, pulses, generation, vent/auto-sell.
- [ ] Generate and commit first golden fixtures from Python for 3 representative reactor layouts.
- [ ] Add CI command for parity test execution (headless, no Bevy rendering).

