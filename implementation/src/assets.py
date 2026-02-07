"""Asset path resolution — works for both native (filesystem) and web (Pyodide) builds.

Native mode: resolves sprite/texture/reference paths against the repository
filesystem, with an optional REV_REACTOR_ASSETS_DIR environment override.

Web mode: returns bare filenames — actual image loading is handled by JS,
Python only needs filenames for texture lookup.
"""
from __future__ import annotations

import sys

_WEB = sys.platform == "emscripten"

if _WEB:
    def sprite_path(name: str) -> str:
        """Return the sprite filename for JS texture lookup."""
        if not name.lower().endswith(".png"):
            name = f"{name}.png"
        return name

else:
    from pathlib import Path
    import os

    def repo_root() -> Path:
        here = Path(__file__).resolve()
        # .../implementation/src/assets.py -> repo root is 2 levels up
        return here.parents[2]

    def assets_root() -> Path:
        override = os.environ.get("REV_REACTOR_ASSETS_DIR")
        if override:
            return Path(override).resolve()
        return repo_root() / "decompilation" / "recovered" / "recovered_assets"

    def sprites_dir() -> Path:
        return assets_root() / "sprites"

    def textures_dir() -> Path:
        return assets_root() / "textures"

    def reference_dir() -> Path:
        return repo_root() / "documentation" / "knowledge-base" / "reference"

    def reference_path(name: str) -> Path:
        if not name.lower().endswith(".png"):
            name = f"{name}.png"
        p = reference_dir() / name
        if p.exists():
            return p
        raise FileNotFoundError(f"Reference image not found: {name}")

    def sprite_path(name: str) -> Path:
        if not name.lower().endswith(".png"):
            name = f"{name}.png"
        p = sprites_dir() / name
        if p.exists():
            return p
        p = textures_dir() / name
        if p.exists():
            return p
        raise FileNotFoundError(f"Sprite not found: {name}")
