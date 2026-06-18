import pyautogui
import time

pyautogui.FAILSAFE = False

# ── Zoom state ────────────────────────────────────────────────────────────────
current_zoom_level = 0
MIN_ZOOM = -5
MAX_ZOOM = 5


def zoom_in():
    global current_zoom_level
    if current_zoom_level < MAX_ZOOM:
        pyautogui.hotkey('ctrl', '+')
        current_zoom_level += 1
        print(f"Zoom In  → level {current_zoom_level}")
        time.sleep(0.1)


def zoom_out():
    global current_zoom_level
    if current_zoom_level > MIN_ZOOM:
        pyautogui.hotkey('ctrl', '-')
        current_zoom_level -= 1
        print(f"Zoom Out → level {current_zoom_level}")
        time.sleep(0.1)


def reset_zoom():
    """Reset zoom to 100% — called when camera turns OFF."""
    global current_zoom_level
    pyautogui.hotkey('ctrl', '0')
    current_zoom_level = 0
    print("Zoom Reset → 100%")
    time.sleep(0.1)


def get_zoom_level():
    return current_zoom_level


# ── Rule-based fallback (only used if no ML model) ────────────────────────────
_last_zoom_time = 0
ZOOM_COOLDOWN = 5.0

def auto_adjust(face_width):
    global _last_zoom_time
    now = time.time()
    if now - _last_zoom_time >= ZOOM_COOLDOWN:
        if face_width > 280:
            zoom_out()
            _last_zoom_time = now
        elif 0 < face_width < 150:
            zoom_in()
            _last_zoom_time = now


# ── Dark mode stubs — coming later ────────────────────────────────────────────
def enable_dark_mode():
    pass

def disable_dark_mode():
    pass

def toggle_dark_mode(enable=True):
    pass


# ── Font size ─────────────────────────────────────────────────────────────────
font_sizes = [8, 10, 12, 14, 16, 18, 20, 24, 28, 32]
current_font_index = 4

def increase_font():
    global current_font_index
    if current_font_index < len(font_sizes) - 1:
        current_font_index += 1

def decrease_font():
    global current_font_index
    if current_font_index > 0:
        current_font_index -= 1

def get_font_size():
    return font_sizes[current_font_index]