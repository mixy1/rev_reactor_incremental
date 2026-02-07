try:
    from raylib import *  # type: ignore
except Exception:
    try:
        from pyray import *  # type: ignore
    except Exception as exc:
        raise ImportError(
            "Could not import raylib bindings. Install 'raylib' or 'pyray'."
        ) from exc

# Some bindings expose Color/Vector2 as structs, others use plain tuples.
if "Color" not in globals():
    def Color(r: int, g: int, b: int, a: int):  # type: ignore
        return (r, g, b, a)

if "Vector2" not in globals():
    def Vector2(x: float, y: float):  # type: ignore
        return (x, y)

if "Rectangle" not in globals():
    def Rectangle(x: float, y: float, width: float, height: float):  # type: ignore
        return (x, y, width, height)

# Some bindings don't expose Texture2D as a public symbol; provide a placeholder for type hints.
if "Texture2D" not in globals():
    class Texture2D:  # type: ignore
        pass

# Map common snake_case names to CamelCase raylib bindings if needed.
_CAMEL_MAP = {
    "init_window": "InitWindow",
    "set_target_fps": "SetTargetFPS",
    "window_should_close": "WindowShouldClose",
    "begin_drawing": "BeginDrawing",
    "clear_background": "ClearBackground",
    "end_drawing": "EndDrawing",
    "get_frame_time": "GetFrameTime",
    "is_key_pressed": "IsKeyPressed",
    "load_texture": "LoadTexture",
    "unload_texture": "UnloadTexture",
    "draw_text": "DrawText",
    "draw_rectangle": "DrawRectangle",
    "draw_rectangle_lines": "DrawRectangleLines",
    "draw_texture_ex": "DrawTextureEx",
    "draw_texture_pro": "DrawTexturePro",
    "close_window": "CloseWindow",
    "get_mouse_position": "GetMousePosition",
    "is_mouse_button_pressed": "IsMouseButtonPressed",
    "is_mouse_button_down": "IsMouseButtonDown",
    "measure_text": "MeasureText",
    "get_time": "GetTime",
    "take_screenshot": "TakeScreenshot",
    "set_exit_key": "SetExitKey",
    "begin_scissor_mode": "BeginScissorMode",
    "end_scissor_mode": "EndScissorMode",
    "get_mouse_wheel_move": "GetMouseWheelMove",
    "is_mouse_button_released": "IsMouseButtonReleased",
}

for snake, camel in _CAMEL_MAP.items():
    if snake not in globals() and camel in globals():
        globals()[snake] = globals()[camel]

if "MOUSE_BUTTON_MIDDLE" not in globals():
    MOUSE_BUTTON_MIDDLE = 2


def _encode_text(value):  # type: ignore
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


# Wrap common functions that expect const char*
if "init_window" in globals():
    _init_window = globals()["init_window"]

    def init_window(width, height, title):  # type: ignore
        return _init_window(width, height, _encode_text(title))

    globals()["init_window"] = init_window

if "draw_text" in globals():
    _draw_text = globals()["draw_text"]

    def draw_text(text, x, y, size, color):  # type: ignore
        return _draw_text(_encode_text(text), x, y, size, color)

    globals()["draw_text"] = draw_text

if "measure_text" in globals():
    _measure_text = globals()["measure_text"]

    def measure_text(text, size):  # type: ignore
        return _measure_text(_encode_text(text), size)

    globals()["measure_text"] = measure_text
else:
    def measure_text(text, size):  # type: ignore
        return None

    globals()["measure_text"] = measure_text

if "take_screenshot" in globals():
    _take_screenshot = globals()["take_screenshot"]

    def take_screenshot(path):  # type: ignore
        return _take_screenshot(_encode_text(path))

    globals()["take_screenshot"] = take_screenshot

if "load_texture" in globals():
    _load_texture = globals()["load_texture"]

    def load_texture(path):  # type: ignore
        return _load_texture(_encode_text(path))

    globals()["load_texture"] = load_texture
