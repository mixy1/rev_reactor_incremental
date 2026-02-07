"""Asset path resolution for Pyodide web port.

In the web build, actual image loading is handled by JS.  Python only needs
filenames for texture lookup — the sprite_path function simply returns the
filename (with .png extension) for the JS renderer to find.
"""
from __future__ import annotations


def sprite_path(name: str) -> str:
    """Return the sprite filename for JS texture lookup.

    Accepts names with or without .png extension.
    """
    if not name.lower().endswith(".png"):
        name = f"{name}.png"
    return name
