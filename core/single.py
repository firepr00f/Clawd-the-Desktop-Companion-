"""
One Clawd at a time.

Two copies running is not a cosmetic problem. They both put an icon in the
tray, so quitting one takes an icon away and leaves an orphan behind. They both
sit always-on-top and shove each other around. They both write `state.json`, so
the focused-minute count is whatever the loser wrote last. And every nag,
tidbit and screen check happens twice, at twice the API cost.

Starting Clawd twice is easy to do by accident — a shortcut, the .bat file, a
double-click on the .pyw, or forgetting one is already running because he is
parked in a corner.

The lock is a named mutex on Windows, which the OS releases even if the process
is killed, and a pid file everywhere else. Both answer one question: is a live
Clawd already running?
"""

from __future__ import annotations

import os
import sys
import tempfile

_HELD = None                     # the mutex handle / open pid file, kept alive
LOCK_NAME = "Local\\ClawdDesktopPetSingleInstance"
PID_FILE = os.path.join(tempfile.gettempdir(), "clawd.pid")


def _windows_lock() -> bool:
    """
    True if we got the lock. A named mutex, so Windows cleans it up for us —
    a pid file left behind by a crash would lock him out until it was deleted
    by hand, which is a worse failure than the one being prevented.
    """
    global _HELD
    import ctypes
    from ctypes import wintypes

    ERROR_ALREADY_EXISTS = 183
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = wintypes.HANDLE
    handle = k32.CreateMutexW(None, True, LOCK_NAME)
    if not handle:
        return True                       # cannot tell: let him run
    if k32.GetLastError() == ERROR_ALREADY_EXISTS:
        k32.CloseHandle(handle)
        return False
    _HELD = handle
    return True


def _pid_lock() -> bool:
    """A pid file, for everywhere that is not Windows. Stale files are reclaimed."""
    global _HELD
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, encoding="utf-8") as f:
                old = int((f.read() or "0").strip() or 0)
            if old and old != os.getpid():
                try:
                    os.kill(old, 0)       # signal 0: does that process exist?
                    return False
                except (ProcessLookupError, ValueError):
                    pass                  # stale: whoever wrote it is gone
                except PermissionError:
                    return False          # alive, just not ours to signal
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        _HELD = PID_FILE
        return True
    except Exception:
        return True                       # never let the lock be why he won't start


def acquire() -> bool:
    """
    True if this is the only Clawd. False means one is already running and this
    copy should say so and quit.
    """
    try:
        if sys.platform == "win32":
            return _windows_lock()
        return _pid_lock()
    except Exception:
        return True


def release():
    """Give the lock up. Not strictly needed — the OS does it — but tidy."""
    global _HELD
    held, _HELD = _HELD, None
    if held is None:
        return
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.CloseHandle(held)
        elif os.path.exists(held):
            os.remove(held)
    except Exception:
        pass


def already_running_notice():
    """
    Tell whoever launched the second copy why it is closing.

    A message box rather than a print: this is a .pyw with no console, so a
    printed line goes nowhere and the second copy would look like it silently
    failed to start.
    """
    msg = ("Clawd is already running.\n\n"
           "Look for him in the notification area, bottom-right — "
           "click the icon for his menu.")
    if sys.platform == "win32":
        try:
            import ctypes
            MB_OK, MB_ICONINFORMATION = 0x0, 0x40
            ctypes.windll.user32.MessageBoxW(
                None, msg, "Clawd", MB_OK | MB_ICONINFORMATION)
            return
        except Exception:
            pass
    print(msg)
