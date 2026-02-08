# AGENTS.md

## Project Structure
- `documentation/` — All markdown documentation
  - `documentation/plans/` — Plans, milestones, and roadmaps
  - `documentation/knowledge-base/` — Ongoing notes, reverse‑engineering findings, and decisions
- `decompilation/` — All reverse‑engineering artifacts, tools, and extracted data
- `implementation/` — The reimplementation codebase (Python + raylib)

## Documentation Rules
- Write **all** docs as markdown under `documentation/` only.
- Add new findings to `documentation/knowledge-base/` and keep them concise.
- Update or append to existing docs instead of creating duplicates.
- On startup, **read** `documentation/plans/PROJECT_PLAN.md` first, then `documentation/knowledge-base/INDEX.md`.
- Keep plan progress updated using checkboxes in `documentation/plans/PROJECT_PLAN.md`.

## Artifact Hygiene
- Keep build artifacts, extracted assets, metadata, and analysis outputs under `decompilation/`.
- Keep tooling (Il2CppDumper, Il2CppInspector, binaryen, etc.) under `decompilation/tools/`.
- Keep Python/.NET environments under `decompilation/env/`.

## Git
- **Always use git.** Commit after completing meaningful units of work.
- After each local commit, **push to `origin/master` automatically** unless explicitly told not to push.
- Write clear commit messages that describe the *why*, not just the *what*.
- Never force-push, amend published commits, or skip hooks without explicit permission.

## Implementation
- All new source code goes under `implementation/`.

## Web Changelog
- Maintain `web/changelog.txt` as the user-facing changelog source.
- Generate the site changelog UI from `web/changelog.txt`; do not hardcode changelog entries in `web/index.html`.
- For meaningful changes, append concise dated entries to `web/changelog.txt` using `YYYY-MM-DD<TAB>message`.
