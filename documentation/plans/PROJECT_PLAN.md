# Rev Reactor: Decompile + Reimplement Plan

## Goals
- Recover assets and serialized data from the Unity WebGL build.
- Reconstruct script structure (classes, fields, methods) from IL2CPP metadata.
- Understand core gameplay systems and data flow.
- Reimplement the game in Python with a deterministic core and a modern UI stack.
- Translate the Python prototype to Rust + Bevy for long-term maintainability and deployment.

## Assumptions
- Source project is lost; only WebGL build artifacts are available.
- Build uses IL2CPP (confirmed by global-metadata + Il2CppCodeRegistration).
- Text/UI strings and serialized data live in Build.data; code in wasm/asm.js.

## Phase 0 — Inventory & Ground Truth
Deliverables:
- [x] Build artifact map (what files, what they contain).
- [x] Versioning notes (Unity/IL2CPP build strings).

Steps:
- [x] Verify file list and sizes (hashes pending).
- [x] Note Unity/IL2CPP build version strings from wasm.
- [x] Capture offsets of key data (UnityFS, metadata, etc.).

## Phase 1 — Asset Recovery
Deliverables:
- [x] Exported textures/sprites.
- [ ] Exported audio/fonts (not present or not yet extracted).
- [x] Asset index (type, name, path_id, source file).
- [x] Scene and prefab inventory (names + hierarchy where possible).

Steps:
- [x] Extract UnityFS from Build.data.
- [x] Export assets with UnityPy.
- [x] Build a CSV index (name/type/path_id/refs).
- [x] Map scenes/prefabs to GameObjects + components.

## Phase 2 — Script Surface Reconstruction
Deliverables:
- [x] Assembly-CSharp class list.
- [x] Field lists (names + types), method names + arities.
- [x] MonoBehaviour index with class + GameObject attachment info.
- [x] Initial C#-like stubs (for reference).

Steps:
- [x] Parse global-metadata.dat for type/field/method tables.
- [x] Decode MonoBehaviour typetrees and attach to class names.
- [x] Build class → fields/methods tables.
- [x] Generate stubs to guide reimplementation.

## Phase 3 — Code-Path Recovery (Wasm / IL2CPP)
Deliverables:
- [ ] Mapped IL2CPP registration tables (CodeRegistration, MetadataRegistration).
- [ ] Method index → wasm address mapping (partial is OK).
- [x] High-level pseudocode for core systems.

Steps:
- [ ] Locate and annotate Il2CppCodeRegistration / MetadataRegistration in wasm.
- [ ] Identify method table and string literal tables.
- [x] Link method indices to metadata method definitions (core classes).
- [x] Decompile high-value methods in Ghidra (initial pass: gameplay loop, UI updates).

## Phase 4 — Gameplay Model Extraction
Deliverables:
- [x] Data model spec (entities, components, resources).
- [x] System list (reactor, upgrades, economy, UI, save/load, progression).
- [x] State machine or tick flow.

Steps:
- [x] Start from UI strings and MonoBehaviours to find systems.
- [x] Trace dependencies between components using serialized fields.
- [x] Reconstruct constants and curves from serialized data.
- [x] Document update order and interactions.

## Phase 5 — Reimplementation Architecture (Python + Raylib)
Deliverables:
- [x] Python project skeleton + module layout.
- [ ] Core simulation (deterministic, testable).
- [ ] Serialization format for save/load.
- [ ] UI/rendering layer plan (raylib via Python bindings).

Steps:
- [ ] Define core data structures and systems.
- [ ] Implement deterministic tick loop + event system.
- [ ] Port constants/curves and data tables.
- [ ] Rebuild UI and rendering using raylib (2D).

## Phase 6 — Validation & Parity
Deliverables:
- [ ] Behavior parity checklist.
- [ ] Automated tests for systems (economy, upgrades, heat dynamics).
- [ ] Playable milestone builds.

Steps:
- [ ] Validate core numbers vs original (where recoverable).
- [ ] Compare UI outputs (labels, numbers, states).
- [ ] Iterate system-by-system to match gameplay feel.

## Phase 7 — Rust + Bevy Translation
Reference:
- `documentation/plans/BEVY_TRANSLATION_PLAN.md`

Deliverables:
- [x] Concrete Python->Bevy migration plan with phases, risks, and milestones.
- [x] Rust workspace scaffold under `implementation_bevy/`.
- [x] Core simulation harness in Rust with deterministic tests.
- [x] Playable Bevy app shell with grid/HUD/input/save loop.
- [ ] Save/import compatibility parity (current JSON/base64 and legacy encrypted import path).

Steps:
- [x] Audit `implementation/src` module boundaries and migration dependencies.
- [x] Port data models/loaders (components, upgrades, saves) to Rust.
- [ ] Port full tick pipeline and placement/prestige rules to headless Rust simulation.
- [x] Port playable view state/input/render flow from raylib loop to Bevy states/systems.
- [ ] Validate parity against captured Python fixtures before cutover.

## Risks / Unknowns
- Full method mapping in wasm can be time-consuming.
- Some runtime behavior may be data-driven but opaque.
- UI text references might not map cleanly back to code.

## Current Status Snapshot
- [x] Assets exported (sprites/textures).
- [x] MonoBehaviours indexed with class names.
- [x] Metadata parsed for Assembly-CSharp types.
- [x] wasm generated and loaded in Ghidra MCP.
- [x] MethodIndex → wasm function name mapping confirmed for core classes.
- [x] Core Simulation + UI methods renamed in Ghidra and documented.
- [x] Python project packaging migrated to `pyproject.toml` + `uv.lock`.

## Next Actions
- [x] Extracted all 75 component types with complete stats (costs, fuel CellData, vent/exchange rates).
- [x] Decoded full 10-step tick pipeline from WASM (see wasm-decompilation-notes.md).
- [x] Mapped memory layouts: Simulation, Reactor, Component, ComponentType objects.
- [x] Identified special fuel mechanics: Kymium pulsation, Monastium density penalty, Protium scaling, Discurrium row+column pulses.
- [x] Updated Python simulation to match decoded tick pipeline.
- [x] Added web iframe watchdog host (`index.html` + `game.html`) to recover from renderer hangs/crashes without clearing localStorage saves.
- [x] Added host↔iframe postMessage save/theme bridge to support `sandbox="allow-scripts"` without `allow-same-origin`.
- [x] Added `implementation_bevy/` with data loaders, deterministic core tests, playable Bevy grid loop, and save/load/autosave to `save.json`.
- [x] Added dual export paths in Python options UI: `Export Old` (legacy-bounded encrypted format) and `Export New` (unbounded base64-JSON).
- [ ] Implement upgrade system (stat bonuses, prestige).
- [ ] Implement save/load (import/export).
- [ ] Wire remaining UI elements (heat/power bars, info banner, stats panel).
- [ ] Validate simulation numbers against original game behavior.
