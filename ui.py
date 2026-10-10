"""Presentation-only state and OpenCV layout for gesture control."""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class UIState:
    status: str
    tone: str
    steps: Tuple[str, str, str, str]
    guidance: str
    current: str
    next_action: str
    progress: Optional[float] = None
    timer: str = ""
    direction: Optional[str] = None


def derive_ui_state(paused, target_available, fist_enabled, fist_visible,
                    hold_seconds, required_hold_seconds, scrolling_direction,
                    hand_count, finger_label, fist_latched=False):
    """Map current runtime facts to UI; never alter control state."""
    upcoming = ("upcoming",) * 4
    if paused:
        return UIState("PAUSED", "amber", upcoming,
                       "Paused. Press F8 to resume.", "Paused", "Press F8 to resume")
    if not target_available:
        return UIState("BROWSER NEEDED", "red", ("current",) + upcoming[1:],
                       "Click your browser and move the pointer over the page.",
                       "Browser not selected", "Select browser")

    observing = fist_visible and hand_count == 1
    pending = observing and not fist_latched
    progress = min(1.0, max(0.0, hold_seconds / required_hold_seconds)) if pending else None
    timer = f"{hold_seconds:.2f} / {required_hold_seconds:.2f} seconds" if pending else ""
    if scrolling_direction:
        direction = scrolling_direction
        return UIState("ACTIVE", "green", ("complete", "complete", "complete", "current"),
                       "Keep holding your fist to stop..." if pending else
                       f"Scrolling {direction}. Hold a fist to stop.",
                       f"Scrolling {direction}", "Hold fist to stop", progress, timer, direction)

    if not fist_enabled:
        guidance = "Hold a closed fist to activate."
        if pending:
            guidance = "Keep holding your fist to activate..."
        elif observing and fist_latched:
            guidance = "Release your fist before activating again."
        elif hand_count != 1:
            guidance = "Show one hand to the camera."
        return UIState("INACTIVE", "red", ("complete", "current", "upcoming", "upcoming"),
                       guidance, "Fist tracking" if pending else
                       "Fist recognized - Inactive" if observing and fist_latched else "Browser selected",
                       "Keep holding fist" if pending else
                       "Release fist" if observing and fist_latched else "Make a fist",
                       progress, timer)

    # A new fist hold also disables control before any direction is selected.
    if pending:
        return UIState("ACTIVE", "green", ("complete", "complete", "upcoming", "current"),
                       "Keep holding your fist to stop...", "Fist tracking - Active",
                       "Hold fist to stop", progress, timer)
    guidance = "Raise index: hold 1s for up, return quickly for down."
    next_action = "Gesture to scroll"
    if hand_count != 1:
        return UIState("NOT READY", "amber", ("complete", "complete", "current", "upcoming"),
                       "Show one hand to the camera.", "Control enabled - need one hand",
                       "Show one hand")
    elif finger_label.startswith("Finger up:"):
        guidance = f"{finger_label} - hold for up or return for down."
        next_action = "Hold up or return down"
    elif finger_label == "Close fist to set start pose":
        guidance = "Close your fist to set the starting pose."
        next_action = "Close fist briefly"
    return UIState("ACTIVE", "green", ("complete", "complete", "current", "upcoming"),
                   guidance, "Fist recognized - Active", next_action)


DEFAULT_SIZE = (550, 550)


def enable_windows_dpi_awareness():
    """Avoid Windows bitmap scaling; call before creating any application HWND."""
    import ctypes
    import os
    if os.name != "nt":
        return False
    user = ctypes.WinDLL("user32", use_last_error=True)
    try:
        process = user.SetProcessDpiAwarenessContext
        process.argtypes, process.restype = [ctypes.c_void_p], ctypes.c_bool
        if process(ctypes.c_void_p(-4)):
            return True
        # A host may already have set process awareness. Set our UI thread too.
        thread = user.SetThreadDpiAwarenessContext
        thread.argtypes, thread.restype = [ctypes.c_void_p], ctypes.c_void_p
        return bool(thread(ctypes.c_void_p(-4)))
    except AttributeError:
        # Older Windows: system-DPI awareness is preferable to bitmap scaling.
        fallback = user.SetProcessDPIAware
        fallback.argtypes, fallback.restype = [], ctypes.c_bool
        return bool(fallback())


def window_render_size(title):
    """Read the actual image viewport, including monitor-DPI/resizing changes."""
    import cv2
    try:
        _, _, width, height = cv2.getWindowImageRect(title)
        if width >= 100 and height >= 100:
            return width, height
    except (AttributeError, cv2.error):
        pass
    return DEFAULT_SIZE


def wrap_text(value, max_width, scale, measure):
    """Wrap at word boundaries instead of shrinking text to fit."""
    lines = []
    line = ""
    for word in value.split():
        candidate = f"{line} {word}".strip()
        if line and measure(candidate, scale) > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def compose_frame(camera_image, state, size=DEFAULT_SIZE):
    """Draw at the final viewport dimensions; resize only the camera image.

    A compact 550-square layout is laid out in pixel coordinates. When resized,
    coordinates/font strokes are recomputed, never a completed UI bitmap scaled.
    """
    import cv2
    import numpy as np

    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError("Viewport dimensions must be positive")
    bg, panel = (39, 24, 17), (55, 41, 31)
    text, muted = (251, 250, 249), (175, 163, 156)
    green, red, amber = (183, 231, 110), (113, 113, 248), (77, 191, 251)
    colors = {"green": green, "red": red, "amber": amber}
    canvas = np.full((height, width, 3), bg, dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    unit = min(width / 550, height / 550)
    ox, oy = (width - 550 * unit) / 2, (height - 550 * unit) / 2
    aa = cv2.LINE_AA

    def point(x, y):
        return round(ox + x * unit), round(oy + y * unit)

    def stroke(n=1):
        return max(1, round(n * unit))

    def measure(value, scale):
        return cv2.getTextSize(value, font, scale * unit, stroke())[0][0] / unit

    def words(value, x, y, scale=.46, color=text, thickness=1):
        cv2.putText(canvas, value, point(x, y), font, scale * unit,
                    color, stroke(thickness), aa)

    def box(x, y, w, h, color=panel, thickness=-1):
        cv2.rectangle(canvas, point(x, y), point(x + w, y + h), color,
                      thickness if thickness == -1 else stroke(thickness), aa)

    def line(x1, y1, x2, y2, color, thickness=1):
        cv2.line(canvas, point(x1, y1), point(x2, y2), color, stroke(thickness), aa)

    def circle(x, y, radius, color, thickness=1):
        cv2.circle(canvas, point(x, y), round(radius * unit), color,
                   thickness if thickness == -1 else stroke(thickness), aa)

    def check(x, y, color):
        line(x - 4, y, x - 1, y + 3, color, 2)
        line(x - 1, y + 3, x + 5, y - 4, color, 2)

    def arrow(x1, y1, x2, y2, color, thickness=1):
        cv2.arrowedLine(canvas, point(x1, y1), point(x2, y2), color,
                        stroke(thickness), aa, tipLength=.3)

    def fist_icon(x, y, color):
        box(x - 10, y - 3, 19, 15, color, 1)
        for dx in (-10, -5, 0, 5):
            box(x + dx, y - 10, 4, 9, color, 1)
        box(x + 4, y + 3, 9, 5, color, 1)
        line(x - 5, y + 12, x - 5, y + 17, color)
        line(x + 5, y + 12, x + 5, y + 17, color)

    words("Gesture Control", 14, 29, .65, thickness=2)
    words("F8: pause/resume   F9: exit", 14, 49, .37, muted)
    badge_color = colors[state.tone]
    box(345, 10, 191, 32)
    if state.status == "ACTIVE":
        check(360, 26, badge_color)
    elif state.status == "PAUSED":
        line(357, 20, 357, 32, badge_color, 2)
        line(363, 20, 363, 32, badge_color, 2)
    else:
        circle(360, 26, 7, badge_color)
        words("!", 358, 30, .4, badge_color)
    words(state.status, 375, 31, .43, badge_color)

    box(10, 61, 530, 165)
    words("Getting Started", 22, 84, .49, thickness=1)
    names = ("Browser", "Make a fist", "Gesture", "Stop")
    for step, (name, stage) in enumerate(zip(names, state.steps)):
        x, y = 77 + step * 132, 113
        color = green if stage == "complete" else amber if stage == "current" else muted
        circle(x, y, 21, (71, 55, 40), -1)
        circle(x, y, 21, color, 2 if stage == "current" else 1)
        if step == 0:
            box(x - 13, y - 10, 26, 18, color, 1)
            line(x - 13, y - 5, x + 13, y - 5, color)
            coords = [(x, y), (x, y + 15), (x + 4, y + 11),
                      (x + 8, y + 17), (x + 11, y + 15), (x + 7, y + 9), (x + 14, y + 9)]
            cv2.fillPoly(canvas, [np.array([point(a, b) for a, b in coords], dtype=np.int32)], color, aa)
        elif step in (1, 3):
            fist_icon(x, y - 2, color)
        else:
            arrow(x - 6, y + 12, x - 6, y - 12, color)
            arrow(x + 6, y - 12, x + 6, y + 12, color)
        words(name, x - measure(name, .47) / 2, 151, .47, color)
        if stage == "complete":
            check(x + 29, y, color)
        elif stage == "current":
            words("NOW", x - measure("NOW", .32) / 2, 166, .32, color)

    for row, value in enumerate(wrap_text(state.guidance, 506, .55, measure)):
        words(value, 22, 185 + row * 19, .55)
    if state.progress is not None:
        box(22, 211, 285, 9, (71, 55, 40))
        if state.progress > 0:
            box(22, 211, 285 * state.progress, 9, green)
        words(state.timer, 319, 219, .49, green)

    box(10, 234, 530, 238)
    # The only raster resampling is the video, before any UI text is drawn.
    h, w = camera_image.shape[:2]
    left, top = point(16, 240)
    right, bottom = point(534, 466)
    area_w, area_h = right - left, bottom - top
    video_scale = min(area_w / w, area_h / h)
    video_w, video_h = max(1, round(w * video_scale)), max(1, round(h * video_scale))
    interpolation = cv2.INTER_AREA if video_scale < 1 else cv2.INTER_LINEAR
    video = cv2.resize(camera_image, (video_w, video_h), interpolation=interpolation)
    x, y = left + (area_w - video_w) // 2, top + (area_h - video_h) // 2
    # Normally the aspect-ratio padding provides the arrow's right gutter.
    # Reserve a gutter for unusually wide feeds too, without stretching video.
    gutter = round(64 * unit)
    if state.direction and right - (x + video_w) < gutter:
        video_scale = min((area_w - gutter) / w, area_h / h)
        video_w, video_h = max(1, round(w * video_scale)), max(1, round(h * video_scale))
        interpolation = cv2.INTER_AREA if video_scale < 1 else cv2.INTER_LINEAR
        video = cv2.resize(camera_image, (video_w, video_h), interpolation=interpolation)
        x = left + (area_w - gutter - video_w) // 2
        y = top + (area_h - video_h) // 2
    canvas[y:y + video_h, x:x + video_w] = video
    if state.direction:
        camera_right = x + video_w
        arrow_x = (camera_right + right) // 2
        center_y = y + video_h // 2
        arrow_half = round(min(video_h * .28, (right - camera_right) * .75))
        arrow_top, arrow_bottom = center_y - arrow_half, center_y + arrow_half
        start, end = ((arrow_x, arrow_bottom), (arrow_x, arrow_top)) if state.direction == "up" else ((arrow_x, arrow_top), (arrow_x, arrow_bottom))
        cv2.arrowedLine(canvas, start, end, green, stroke(6), aa, tipLength=.25)

    for x, heading, value in ((10, "CURRENT / COMPLETED", state.current),
                              (280, "NEXT ACTION", state.next_action)):
        box(x, 480, 260, 60)
        words(heading, x + 10, 496, .37, muted)
        for row, label in enumerate(wrap_text(value, 240, .5, measure)):
            words(label, x + 10, 516 + row * 17, .5)
    return canvas
