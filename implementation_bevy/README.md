# implementation_bevy

Bevy scaffold for the Rev Reactor reimplementation. This crate currently defines
the application shell, state flow placeholders, and resource placeholders only.
Gameplay systems are intentionally not implemented yet.

## Requirements

- Rust toolchain (stable)
- Cargo

## Build and Run

```bash
cd implementation_bevy
cargo check
cargo run
```

## Project Layout Intent

- `src/main.rs`:
  - Bevy app bootstrap and plugin configuration
  - App state enum placeholders (`Boot`, `MainMenu`, `InGame`, `Paused`)
  - Resource placeholders for runtime/session data
  - `AppShellPlugin` with startup and state-transition stub systems

As this scaffold grows, modules can be moved into dedicated files (`state.rs`,
`resources.rs`, `plugins/`, `systems/`) without changing the startup contract.

## Data Layer

- `src/data/component_types.rs` and `src/data/upgrade_data.rs` define serde models
  matching:
  - `implementation/src/game/component_types.json`
  - `implementation/src/game/upgrade_data.json`
- `src/data/loader.rs` provides engine-agnostic loader APIs:
  - `load_component_types[_from_path]()`
  - `load_upgrade_data[_from_path]()`

## Save Layer

- `src/save/model.rs` defines a serde-compatible save payload matching the Python
  save schema.
- `src/save/codec.rs` provides engine-agnostic codec APIs:
  - JSON: `save_to_json_string()`, `load_from_json_string()`
  - Base64: `export_to_base64()`, `import_from_base64()`
