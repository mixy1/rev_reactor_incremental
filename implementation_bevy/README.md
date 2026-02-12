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
