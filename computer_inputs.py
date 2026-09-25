"""Windows wheel input and a nonblocking, time-based scroll controller."""
import ctypes
from ctypes import wintypes as wt
import os
from time import perf_counter

SCROLL_SECONDS = 0.45
SCROLL_AMOUNT = 120  # One wheel notch, delivered in small increments.
MAX_STEP = 12
STALL_SECONDS = 0.15
BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class InputUnion(ctypes.Union):
    _fields_ = [("mi", MouseInput)]  # Mouse is the largest INPUT union member.


class Input(ctypes.Structure):
    _anonymous_ = ("value",)
    _fields_ = [("type", wt.DWORD), ("value", InputUnion)]


class WindowsInput:
    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Computer input currently requires Windows.")
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = [
            (self.user, "GetForegroundWindow", [], wt.HWND),
            (self.user, "GetCursorPos", [ctypes.POINTER(wt.POINT)], wt.BOOL),
            (self.user, "WindowFromPoint", [wt.POINT], wt.HWND),
            (self.user, "GetAncestor", [wt.HWND, wt.UINT], wt.HWND),
            (self.user, "GetWindowThreadProcessId", [wt.HWND, ctypes.POINTER(wt.DWORD)], wt.DWORD),
            (self.user, "GetAsyncKeyState", [ctypes.c_int], wt.SHORT),
            (self.user, "FindWindowW", [wt.LPCWSTR, wt.LPCWSTR], wt.HWND),
            (self.user, "SetWindowPos", [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, wt.UINT], wt.BOOL),
            (self.user, "SendInput", [wt.UINT, ctypes.POINTER(Input), ctypes.c_int], wt.UINT),
            (self.kernel, "OpenProcess", [wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
            (self.kernel, "QueryFullProcessImageNameW", [wt.HANDLE, wt.DWORD, wt.LPWSTR,
                                                       ctypes.POINTER(wt.DWORD)], wt.BOOL),
            (self.kernel, "CloseHandle", [wt.HANDLE], wt.BOOL),
        ]
        for library, name, args, result in signatures:
            function = getattr(library, name)
            function.argtypes, function.restype = args, result
        self.previous_keys = set()

    def pin_preview(self, title):
        window = self.user.FindWindowW(None, title)
        # TOPMOST, NOSIZE | NOMOVE | NOACTIVATE. Clicking still activates it.
        if not window or not self.user.SetWindowPos(window, wt.HWND(-1), 0, 0, 0, 0, 0x13):
            raise ctypes.WinError(ctypes.get_last_error())

    def target(self):
        """Only allow a supported foreground browser also under the pointer."""
        # Ctrl+wheel zooms; Shift/Alt can also change the browser action.
        if any(self.user.GetAsyncKeyState(key) & 0x8000 for key in (0x10, 0x11, 0x12)):
            return None
        window = self.user.GetForegroundWindow()
        point = wt.POINT()
        if not window or not self.user.GetCursorPos(ctypes.byref(point)):
            return None
        if self.user.GetAncestor(self.user.WindowFromPoint(point), 2) != window:
            return None
        pid = wt.DWORD()
        self.user.GetWindowThreadProcessId(window, ctypes.byref(pid))
        process = self.kernel.OpenProcess(0x1000, False, pid.value)
        if not process:
            return None
        try:
            size = wt.DWORD(32768)
            path = ctypes.create_unicode_buffer(size.value)
            if not self.kernel.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)):
                return None
            return window if os.path.basename(path.value).lower() in BROWSERS else None
        finally:
            self.kernel.CloseHandle(process)

    def shortcuts(self):
        """F8 toggles pause, F9 exits, even while the browser is focused."""
        held = {key for key in (0x77, 0x78) if self.user.GetAsyncKeyState(key) & 0x8000}
        pressed = held - self.previous_keys
        self.previous_keys = held
        return 0x77 in pressed, 0x78 in pressed

    def wheel(self, delta):
        event = Input(type=0, mi=MouseInput(mouseData=delta & 0xffffffff, dwFlags=0x0800))
        if self.user.SendInput(1, ctypes.byref(event), ctypes.sizeof(Input)) != 1:
            raise OSError("Windows could not send scroll input. Check browser permissions.")


class ScrollController:
    """No sleeping, held keys, or queued swipes; advance once per camera frame."""
    def __init__(self, backend, clock=perf_counter):
        self.backend, self.clock = backend, clock
        self.direction = None
        self.target = None

    def cancel(self):
        self.direction = self.target = None

    def start(self, gesture, target):
        if self.direction or not target or gesture not in ("SWIPE_UP", "SWIPE_DOWN"):
            return False
        self.direction = "up" if gesture == "SWIPE_UP" else "down"
        self.target = target
        self.started = self.last_tick = self.clock()
        self.sent = 0
        return True

    def tick(self, allowed=True):
        if not self.direction:
            return
        now = self.clock()
        if not allowed or now - self.last_tick > STALL_SECONDS or self.backend.target() != self.target:
            self.cancel()
            return
        self.last_tick = now
        progress = min(1.0, max(0.0, (now - self.started) / SCROLL_SECONDS))
        eased = progress * progress * (3 - 2 * progress)
        desired = round(SCROLL_AMOUNT * eased)
        delta = min(MAX_STEP, max(0, desired - self.sent))
        if delta:
            try:
                self.backend.wheel(delta if self.direction == "up" else -delta)
            except OSError:
                self.cancel()
                raise
            self.sent += delta
        if progress >= 1:
            # Never flush a large remainder after slow frames.
            self.cancel()
