"""
Watches what window you're actually looking at.

Pure ctypes / stdlib on Windows -- no pywin32 needed. On non-Windows it
degrades to a stub so the rest of the app can still be imported and tested.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


@dataclass
class Activity:
    """One observation of what the user is doing right now."""

    title: str = ""
    process: str = ""          # e.g. "chrome.exe"
    idle_seconds: float = 0.0
    rect: tuple[int, int, int, int] | None = None   # left, top, right, bottom
    at: float = field(default_factory=time.time)

    @property
    def blob(self) -> str:
        """Lowercased haystack used by the classifier."""
        return f"{self.title} :: {self.process}".lower()

    @property
    def is_browser(self) -> bool:
        return self.process.lower() in {
            "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
            "opera.exe", "whale.exe", "arc.exe", "vivaldi.exe",
        }

    def short(self, n: int = 70) -> str:
        t = self.title.strip() or self.process or "something"
        return t if len(t) <= n else t[: n - 1] + "…"


def _win_foreground() -> Activity:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return Activity(idle_seconds=_win_idle_seconds())

    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    process = ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if handle:
        try:
            size = wintypes.DWORD(1024)
            name_buf = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(
                handle, 0, name_buf, ctypes.byref(size)
            ):
                process = os.path.basename(name_buf.value)
        finally:
            kernel32.CloseHandle(handle)

    rect = None
    r = wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(r)):
        rect = (r.left, r.top, r.right, r.bottom)

    return Activity(
        title=title,
        process=process,
        idle_seconds=_win_idle_seconds(),
        rect=rect,
    )


def _win_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    millis = kernel32.GetTickCount() - info.dwTime
    return max(0.0, millis / 1000.0)


def foreground() -> Activity:
    """Current foreground window, or an empty Activity off-Windows."""
    if IS_WINDOWS:
        try:
            return _win_foreground()
        except Exception:
            return Activity()
    return Activity(title="(watcher unavailable on this platform)")


def cursor_pos() -> tuple[int, int] | None:
    """Mouse position in screen pixels, or None off-Windows."""
    if not IS_WINDOWS:
        return None
    try:
        pt = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            return int(pt.x), int(pt.y)
    except Exception:
        pass
    return None


def is_own_window(act: Activity, own_titles: set[str]) -> bool:
    """Don't let Clawd react to his own windows."""
    return act.title in own_titles
