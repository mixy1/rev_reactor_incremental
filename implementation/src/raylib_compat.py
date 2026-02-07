"""raylib compatibility layer for Pyodide/Canvas2D web port.

All raylib drawing functions are reimplemented to collect draw commands into a
flat array.array('d') buffer.  At end_drawing(), the buffer is sent to JavaScript
via a single zero-copy to_js() call, where renderer.js iterates and executes
Canvas2D commands natively.

Command opcodes:
  0  CLEAR_BG        r,g,b,a
  1  FILL_RECT        x,y,w,h,r,g,b,a
  2  STROKE_RECT      x,y,w,h,r,g,b,a
  3  DRAW_TEXT         strIdx,x,y,size,r,g,b,a
  4  TEXTURE_PRO       texId,sx,sy,sw,sh,dx,dy,dw,dh,r,g,b,a
  5  TEXTURE_EX        texId,x,y,rot,scale,r,g,b,a
  6  BEGIN_SCISSOR     x,y,w,h
  7  END_SCISSOR       (none)
"""
from __future__ import annotations

import array
import time as _time

# ── Opcodes ───────────────────────────────────────────────────────────
OP_CLEAR_BG = 0
OP_FILL_RECT = 1
OP_STROKE_RECT = 2
OP_DRAW_TEXT = 3
OP_TEXTURE_PRO = 4
OP_TEXTURE_EX = 5
OP_BEGIN_SCISSOR = 6
OP_END_SCISSOR = 7

# ── Command buffer (module-level) ─────────────────────────────────────
_cmds: array.array = array.array('d')
_strings: list[str] = []

# ── Input state (polled once per frame from JS) ──────────────────────
_input_state: dict = {}
_prev_input_state: dict = {}
_frame_time: float = 1.0 / 60.0
_start_time: float = _time.time()

# ── JS bridge (set by loader.js after Pyodide boots) ─────────────────
_js_render_batch = None
_js_measure_text = None
_js_get_texture_info = None
_js_poll_input = None


def _set_js_bridge(render_batch, measure_text_fn, get_texture_info, poll_input):
    """Called from loader.js to provide JS function references."""
    global _js_render_batch, _js_measure_text, _js_get_texture_info, _js_poll_input
    _js_render_batch = render_batch
    _js_measure_text = measure_text_fn
    _js_get_texture_info = get_texture_info
    _js_poll_input = poll_input


# ── Type surrogates ───────────────────────────────────────────────────

def Color(r: int, g: int, b: int, a: int) -> tuple:
    return (r, g, b, a)


def Vector2(x: float, y: float) -> tuple:
    return (x, y)


def Rectangle(x: float, y: float, width: float, height: float) -> tuple:
    return (x, y, width, height)


class Texture2D:
    """Lightweight texture handle.  JS manages actual Image objects."""
    __slots__ = ('id', 'width', 'height', '_name')

    def __init__(self, tex_id: int = 0, width: int = 0, height: int = 0, name: str = ''):
        self.id = tex_id
        self.width = width
        self.height = height
        self._name = name


# ── Key / mouse constants ────────────────────────────────────────────
KEY_F1 = 112
KEY_F2 = 113
KEY_F3 = 114
KEY_F4 = 115
KEY_F5 = 116
KEY_SPACE = 32
KEY_ESCAPE = 27
KEY_X = 88
KEY_Y = 89

MOUSE_BUTTON_LEFT = 0
MOUSE_BUTTON_RIGHT = 2
MOUSE_BUTTON_MIDDLE = 1


# ── Window management (no-ops) ──────────────────────────────────────

def init_window(width: int, height: int, title: str) -> None:
    pass


def close_window() -> None:
    pass


def set_target_fps(fps: int) -> None:
    pass


def set_exit_key(key: int) -> None:
    pass


def WindowShouldClose() -> bool:
    return False


# ── Frame timing ─────────────────────────────────────────────────────

def get_frame_time() -> float:
    return _frame_time


def get_time() -> float:
    return _time.time() - _start_time


# ── Drawing frame ────────────────────────────────────────────────────

def begin_drawing() -> None:
    global _cmds, _strings, _prev_input_state, _input_state, _frame_time
    _cmds = array.array('d')
    _strings.clear()

    # Poll input state from JS once per frame
    _prev_input_state = _input_state
    if _js_poll_input is not None:
        raw = _js_poll_input()
        # raw is a JS object; convert to Python dict
        _input_state = raw.to_py() if hasattr(raw, 'to_py') else dict(raw)
        _frame_time = _input_state.get('dt', 1.0 / 60.0)
    else:
        _input_state = {}
        _frame_time = 1.0 / 60.0


def end_drawing() -> None:
    if _js_render_batch is not None:
        from pyodide.ffi import to_js  # type: ignore
        # Zero-copy Float64Array transfer
        js_cmds = to_js(_cmds, dict_converter=None)
        js_strings = to_js(_strings)
        _js_render_batch(js_cmds, js_strings)


# ── Background ───────────────────────────────────────────────────────

def clear_background(color: tuple) -> None:
    _cmds.append(OP_CLEAR_BG)
    _cmds.append(color[0])
    _cmds.append(color[1])
    _cmds.append(color[2])
    _cmds.append(color[3])


# ── Rectangle drawing ────────────────────────────────────────────────

def draw_rectangle(x: int, y: int, width: int, height: int, color: tuple) -> None:
    _cmds.append(OP_FILL_RECT)
    _cmds.append(float(x))
    _cmds.append(float(y))
    _cmds.append(float(width))
    _cmds.append(float(height))
    _cmds.append(color[0])
    _cmds.append(color[1])
    _cmds.append(color[2])
    _cmds.append(color[3])


def draw_rectangle_lines(x: int, y: int, width: int, height: int, color: tuple) -> None:
    _cmds.append(OP_STROKE_RECT)
    _cmds.append(float(x))
    _cmds.append(float(y))
    _cmds.append(float(width))
    _cmds.append(float(height))
    _cmds.append(color[0])
    _cmds.append(color[1])
    _cmds.append(color[2])
    _cmds.append(color[3])


# ── Text ─────────────────────────────────────────────────────────────

def draw_text(text: str, x: int, y: int, size: int, color: tuple) -> None:
    str_idx = len(_strings)
    _strings.append(str(text))
    _cmds.append(OP_DRAW_TEXT)
    _cmds.append(float(str_idx))
    _cmds.append(float(x))
    _cmds.append(float(y))
    _cmds.append(float(size))
    _cmds.append(color[0])
    _cmds.append(color[1])
    _cmds.append(color[2])
    _cmds.append(color[3])


def measure_text(text: str, size: int) -> int:
    """Synchronous FFI call to ctx.measureText()."""
    if _js_measure_text is not None:
        return int(_js_measure_text(str(text), size))
    # Fallback approximation
    return int(len(str(text)) * size * 0.6)


# ── Textures ─────────────────────────────────────────────────────────

_texture_cache: dict[str, Texture2D] = {}


def load_texture(path: str) -> Texture2D:
    # Extract just the filename from the path
    import os
    name = os.path.basename(str(path))

    # Check cache
    if name in _texture_cache:
        return _texture_cache[name]

    # Get texture info (including the JS-assigned ID) from pre-loaded images
    tid, w, h = 0, 32, 32
    if _js_get_texture_info is not None:
        info = _js_get_texture_info(name)
        if info is not None:
            info_py = info.to_py() if hasattr(info, 'to_py') else dict(info)
            tid = int(info_py.get('id', 0))
            w = int(info_py.get('width', 32))
            h = int(info_py.get('height', 32))

    tex = Texture2D(tid, w, h, name)
    _texture_cache[name] = tex
    return tex


def unload_texture(texture) -> None:
    pass


def draw_texture_pro(texture, src_rect: tuple, dst_rect: tuple,
                     origin: tuple, rotation: float, tint: tuple) -> None:
    _cmds.append(OP_TEXTURE_PRO)
    _cmds.append(float(texture.id))
    # Source rect
    _cmds.append(float(src_rect[0]))
    _cmds.append(float(src_rect[1]))
    _cmds.append(float(src_rect[2]))
    _cmds.append(float(src_rect[3]))
    # Dest rect
    _cmds.append(float(dst_rect[0]))
    _cmds.append(float(dst_rect[1]))
    _cmds.append(float(dst_rect[2]))
    _cmds.append(float(dst_rect[3]))
    # Tint
    _cmds.append(tint[0])
    _cmds.append(tint[1])
    _cmds.append(tint[2])
    _cmds.append(tint[3])


def draw_texture_ex(texture, position: tuple, rotation: float,
                    scale: float, tint: tuple) -> None:
    _cmds.append(OP_TEXTURE_EX)
    _cmds.append(float(texture.id))
    _cmds.append(float(position[0]))
    _cmds.append(float(position[1]))
    _cmds.append(float(rotation))
    _cmds.append(float(scale))
    _cmds.append(tint[0])
    _cmds.append(tint[1])
    _cmds.append(tint[2])
    _cmds.append(tint[3])


# ── Scissor mode ─────────────────────────────────────────────────────

def begin_scissor_mode(x: int, y: int, w: int, h: int) -> None:
    _cmds.append(OP_BEGIN_SCISSOR)
    _cmds.append(float(x))
    _cmds.append(float(y))
    _cmds.append(float(w))
    _cmds.append(float(h))


def end_scissor_mode() -> None:
    _cmds.append(OP_END_SCISSOR)


# ── Input ────────────────────────────────────────────────────────────

def get_mouse_position():
    """Returns a namespace-like object with .x and .y attributes."""
    mx = _input_state.get('mouseX', 0)
    my = _input_state.get('mouseY', 0)

    class _Pos:
        __slots__ = ('x', 'y')
        def __init__(self, x, y):
            self.x = x
            self.y = y
    return _Pos(mx, my)


def is_mouse_button_pressed(button: int) -> bool:
    """True on the frame a button was first pressed (edge-triggered)."""
    pressed = _input_state.get('mousePressed', [])
    return button in pressed


def is_mouse_button_down(button: int) -> bool:
    """True while button is held."""
    down = _input_state.get('mouseDown', [])
    return button in down


def is_mouse_button_released(button: int) -> bool:
    """True on the frame a button was released."""
    released = _input_state.get('mouseReleased', [])
    return button in released


def get_mouse_wheel_move() -> float:
    return _input_state.get('wheelDelta', 0.0)


def is_key_pressed(key: int) -> bool:
    """True on the frame a key was first pressed."""
    pressed = _input_state.get('keysPressed', [])
    return key in pressed


# ── Utilities (no-ops) ───────────────────────────────────────────────

def take_screenshot(path: str) -> None:
    pass


def get_pending_file_import():
    """Return file content queued by the JS file input, or None."""
    return _input_state.get('fileImport', None)
