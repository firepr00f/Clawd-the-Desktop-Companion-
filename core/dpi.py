"""
Windows DPI awareness.

This is the single most important fix for "Clawd only sees a browser".

If the process is DPI-*unaware* and the display is scaled (125% / 150% / 175%,
which is the Windows default on most laptops), then:

    * GetWindowRect() hands back *logical* coordinates    -> e.g. 1280x720
    * mss / BitBlt grab *physical* pixels                 -> screen is 1920x1080

...so asking for the window rect crops the top-left ~2/3 of the real screen.
On a maximised browser that lands squarely on the tab strip and the address
bar, which is exactly why Clawd could tell it was a browser and nothing else.

Calling SetProcessDpiAwarenessContext() before Tk starts makes both sides speak
physical pixels, and the crop lines up with the window again.

Side effect: once aware, Tk geometry is in physical pixels too, so Clawd would
render 1/scale smaller than before. `scale()` gives the factor back so the
sprite and font can be multiplied by it and end up looking identical.
"""

from __future__ import annotations

import sys

_enabled = False
_scale = 1.0

# SetProcessDpiAwarenessContext values
_PER_MONITOR_AWARE_V2 = -4
_PER_MONITOR_AWARE = -3


def enable() -> bool:
    """
    Make this process DPI aware. Must run BEFORE the first Tk window exists.
    Returns True if awareness was successfully turned on.
    """
    global _enabled, _scale
    if _enabled or sys.platform != "win32":
        return _enabled

    import ctypes

    for attempt in (
        lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(
            ctypes.c_void_p(_PER_MONITOR_AWARE_V2)),
        lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(
            ctypes.c_void_p(_PER_MONITOR_AWARE)),
        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),   # PER_MONITOR
        lambda: ctypes.windll.user32.SetProcessDPIAware(),
    ):
        try:
            if attempt():          # 0/False from shcore means S_OK, hence `is not None`
                _enabled = True
                break
            _enabled = True        # SetProcessDpiAwareness returns 0 on success
            break
        except Exception:
            continue

    if _enabled:
        _scale = _measure_scale()
    return _enabled


def _measure_scale() -> float:
    import ctypes
    for probe in (
        lambda: ctypes.windll.user32.GetDpiForSystem(),
        lambda: ctypes.windll.gdi32.GetDeviceCaps(
            ctypes.windll.user32.GetDC(0), 88),      # LOGPIXELSX
    ):
        try:
            dpi = float(probe())
            if dpi > 0:
                return max(1.0, min(4.0, dpi / 96.0))
        except Exception:
            continue
    return 1.0


def scale() -> float:
    """Display scaling factor (1.0 at 100%, 1.5 at 150%). 1.0 if not aware."""
    return _scale if _enabled else 1.0


def active() -> bool:
    return _enabled


def virtual_screen() -> tuple[int, int, int, int] | None:
    """
    The whole virtual desktop as (left, top, right, bottom) in physical pixels,
    spanning every monitor. Used to sanity-check window rects.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        u = ctypes.windll.user32
        SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
        SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
        left = u.GetSystemMetrics(SM_XVIRTUALSCREEN)
        top = u.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = u.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = u.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        if w > 0 and h > 0:
            return (left, top, left + w, top + h)
    except Exception:
        pass
    return None


def work_area(x: int | None = None, y: int | None = None):
    """
    The usable desktop as (left, top, right, bottom) — the screen MINUS the
    taskbar. Returns None off Windows or if the call fails.

    This is the difference between "on screen" and "reachable". The virtual
    screen includes the strip the taskbar sits on, so a bottom-right corner
    computed from it puts Clawd *behind* the tray: still technically on the
    desktop, but painted over and impossible to right-click. Every corner he
    is sent to is computed from this instead.

    With x/y given, it is the work area of the monitor containing that point,
    so a second display with its own taskbar is handled properly. Without
    them, the primary monitor's.
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                    ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                    ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

    u = ctypes.windll.user32
    if x is not None and y is not None:
        try:
            MONITOR_DEFAULTTONEAREST = 2
            pt = wintypes.POINT(int(x), int(y))
            mon = u.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if mon and u.GetMonitorInfoW(mon, ctypes.byref(info)):
                w = info.rcWork
                if w.right > w.left and w.bottom > w.top:
                    return (w.left, w.top, w.right, w.bottom)
        except Exception:
            pass
    try:
        SPI_GETWORKAREA = 0x0030
        r = RECT()
        if u.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0):
            if r.right > r.left and r.bottom > r.top:
                return (r.left, r.top, r.right, r.bottom)
    except Exception:
        pass
    return None
