"""
Full-screen pixel fireworks.

A separate always-on-top, click-through window the size of the whole desktop,
which draws for a few seconds and then takes itself down. It is deliberately
NOT part of the overlay: Clawd's window is only a few hundred pixels wide and
has to stay exactly where it is, and a show that covered the screen from inside
it would mean resizing and moving him mid-celebration.

Everything is whole cells on a fixed grid. No curves, no easing, no fractional
positions — a ray grows by one cell per frame and a spark is one square. The
shells here are built from a small vocabulary (an orthogonal ray, a 2:1 stepped
diagonal, a detached square spark) rather than copied from any one drawing, and
each shell picks its own spoke set and rhythm, so two bursts on screen at once
do not look like the same stamp twice.

Colour: the core and the sparks are always yellow — that is what reads as
"firework" at a glance — and only the rays take one of the accent colours.
"""

from __future__ import annotations

import os
import random
import sys
import tkinter as tk

KEY = "#010203"            # transparency key — must not appear in the artwork

# The core and every loose spark. Yellow is the through-line of the whole show.
CORE = "#FFE14D"
SPARK = "#FECF7D"

# Accent colours for the rays. Yellow is in the list twice on purpose: it keeps
# coming back, so the show reads as gold with colour in it, not as a rainbow.
ACCENTS = ["#FECF7D", "#F99A48", "#FECF7D", "#DD6B8F",
           "#61AACB", "#8FC97F", "#7883DD", "#F99A48"]

# Ray directions, in cells per step. The (2, 1) family is the staircase that
# reads as a shallow diagonal on a grid without ever needing half a pixel.
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
STEEP = [(1, 2), (-1, 2), (1, -2), (-1, -2)]
SHALLOW = [(2, 1), (-2, 1), (2, -1), (-2, -1)]

# Three shells. `spokes` is which directions get a ray, `reach` how far they
# grow, `gap` draws every Nth cell only (2 = a dotted ray), `tip` adds a
# detached spark past the end.
SHELLS = [
    {"name": "cross", "spokes": ORTHO + DIAG, "reach": 9, "gap": 1, "tip": True},
    {"name": "star", "spokes": ORTHO + DIAG + SHALLOW + STEEP, "reach": 7,
     "gap": 1, "tip": True},
    {"name": "ring", "spokes": ORTHO + DIAG + SHALLOW, "reach": 10, "gap": 2,
     "tip": True},
]

FRAME_MS = 55
RISE_CELLS = 4             # how far the trail climbs each frame
HOLD_FRAMES = 2            # full-size pause between growing and fading


class _Burst:
    """One shell: it climbs, opens, and burns out."""

    def __init__(self, gx: int, gy: int, ground: int, delay: int):
        self.gx, self.gy, self.ground = gx, gy, ground
        self.delay = delay
        self.shell = random.choice(SHELLS)
        self.color = random.choice(ACCENTS)
        self.lean = random.choice((-1, 0, 0, 1))     # the trail drifts as it climbs
        self.rise_frames = max(1, (ground - gy) // RISE_CELLS)
        self.grow = self.shell["reach"]
        self.fade = self.shell["reach"] // 2 + 2

    @property
    def length(self) -> int:
        return self.delay + self.rise_frames + self.grow + HOLD_FRAMES + self.fade

    def cells(self, f: int):
        """Yield (cell_x, cell_y, colour) for frame `f`. Empty once burnt out."""
        f -= self.delay
        if f < 0:
            return

        if f < self.rise_frames:
            # A stepped trail, drawn as the staircase it climbed rather than a
            # straight line — the kink is what makes it read as launched.
            for k in range(f + 1):
                y = self.ground - k * RISE_CELLS
                for dy in range(RISE_CELLS):
                    yield self.gx + self.lean * (k // 2), y - dy, SPARK
            return

        f -= self.rise_frames
        if f < self.grow + HOLD_FRAMES:
            reach = min(self.grow, f + 1)
            inner = 1                       # the core stays lit while it opens
        else:
            f -= self.grow + HOLD_FRAMES
            reach = self.grow
            inner = 2 + f * 2               # burns out from the middle first
            if inner > reach:
                return

        gap = self.shell["gap"]
        for dx, dy in self.shell["spokes"]:
            for k in range(inner, reach + 1):
                if (k - inner) % gap:
                    continue
                yield self.gx + dx * k, self.gy + dy * k, self.color
            if self.shell["tip"] and reach >= self.grow:
                k = reach + 2
                yield self.gx + dx * k, self.gy + dy * k, SPARK

        if inner <= 2:
            for dx, dy in ORTHO:
                yield self.gx + dx, self.gy + dy, CORE
            yield self.gx, self.gy, CORE


def _play(path: str, log=lambda *a: None) -> bool:
    """
    Fire the sound and return immediately.

    A .wav sibling first, through winsound. winsound is in the standard
    library, WAV decoding is in the OS itself, and neither needs a media
    driver to be installed — which turned out to matter: MCI on this machine
    answers "there was a problem initializing MCI", because the legacy
    mpegvideo driver that plays MP3 is not something you can count on being
    present any more. It is deprecated on Windows 11 and absent entirely from
    the N editions.

    So `assets/firework_sound.wav` is what actually plays, and the .mp3 stays
    beside it as the source. MCI is kept as a fallback for the mp3, for a
    machine that does have the driver and no wav.

    Failure is never fatal: a silent firework is still a firework.
    """
    if sys.platform != "win32" or not path:
        return False

    wav = path if path.lower().endswith(".wav") else os.path.splitext(path)[0] + ".wav"
    if os.path.exists(wav):
        try:
            import winsound
            winsound.PlaySound(wav, winsound.SND_FILENAME | winsound.SND_ASYNC
                               | winsound.SND_NODEFAULT)
            return True
        except Exception as e:
            log(f"fireworks: winsound would not play the wav ({e!r})")

    if not os.path.exists(path):
        return False
    try:
        import ctypes
        from ctypes import wintypes

        mci = ctypes.windll.winmm.mciSendStringW
        mci.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR,
                        wintypes.UINT, wintypes.HWND]
        mci.restype = wintypes.DWORD
        err = ctypes.windll.winmm.mciGetErrorStringW
        err.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.UINT]

        def why(code):
            buf = ctypes.create_unicode_buffer(256)
            err(code, buf, 256)
            return buf.value or f"MCI error {code}"

        real = _playable(path, log)
        mci("close clawdfw", None, 0, None)          # whatever was there before

        last = 0
        for opener in (f'open "{real}" type mpegvideo alias clawdfw',
                       f'open "{real}" alias clawdfw'):
            last = mci(opener, None, 0, None)
            if not last:
                break
        else:
            log(f"fireworks: no wav, and MCI could not open the mp3 — {why(last)}")
            return False

        rc = mci("play clawdfw from 0", None, 0, None)
        if rc:
            log(f"fireworks: opened but would not play — {why(rc)}")
            return False
        return True
    except Exception as e:
        log(f"fireworks: no sound ({e!r})")
        return False


class Fireworks:
    """
    One show at a time, over the whole desktop.

    The window is created when a show starts and destroyed when it ends, so
    nothing of this is on screen — or in the way — the rest of the time.
    """

    def __init__(self, root, bounds, cell: float, log=lambda *a: None):
        self.root = root
        self.bounds = bounds            # (left, top, right, bottom) of the desktop
        self.cell = max(4.0, min(float(cell), 20.0))
        self.log = log
        self.win = None
        self.cv = None
        self._after = None
        self._bursts: list[_Burst] = []
        self._frame = 0
        self._end = 0

    @property
    def running(self) -> bool:
        return self.win is not None

    def show(self, seconds: float = 6.0, count: int = 9, sound: str = ""):
        """Launch a show. Calling this during one restarts it."""
        self.stop()
        left, top, right, bottom = self.bounds
        w, h = int(right - left), int(bottom - top)
        cols, rows = int(w / self.cell), int(h / self.cell)
        if cols < 20 or rows < 20:
            return

        try:
            self.win = tk.Toplevel(self.root)
            self.win.overrideredirect(True)
            self.win.attributes("-topmost", True)
            try:
                self.win.attributes("-transparentcolor", KEY)
            except tk.TclError:
                pass
            self.win.configure(bg=KEY)
            self.win.geometry(f"{w}x{h}+{int(left)}+{int(top)}")
            self.cv = tk.Canvas(self.win, width=w, height=h, bg=KEY,
                                highlightthickness=0, bd=0)
            self.cv.pack()
            self.win.update_idletasks()
            self._click_through()
        except Exception as e:
            self.log(f"fireworks: no window ({e!r})")
            self.stop()
            return

        # Spread them across the upper two thirds and stagger the launches, so
        # it is a show rather than one simultaneous bang.
        frames = max(20, int(seconds * 1000 / FRAME_MS))
        self._bursts = []
        for i in range(max(1, count)):
            gx = random.randint(int(cols * 0.10), int(cols * 0.90))
            gy = random.randint(int(rows * 0.12), int(rows * 0.55))
            delay = int(i * frames / (count + 2)) + random.randint(0, 4)
            self._bursts.append(_Burst(gx, gy, rows + 2, delay))

        self._frame = 0
        self._end = max(b.length for b in self._bursts) + 2
        if sound:
            _play(sound, self.log)
        self._tick()

    def _click_through(self):
        """
        Make the whole window invisible to the mouse.

        Without this a full-screen overlay eats every click for the length of
        the show — including the click you were about to make on the thing you
        were working on. WS_EX_TRANSPARENT passes them through; NOACTIVATE
        keeps it from stealing focus when it appears.
        """
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            GWL_EXSTYLE, WS_EX_LAYERED = -20, 0x00080000
            WS_EX_TRANSPARENT, WS_EX_NOACTIVATE = 0x00000020, 0x08000000

            u = ctypes.windll.user32
            # argtypes are not optional here: an HWND is a 64-bit value and an
            # undeclared ctypes argument goes out as a C int, which fails with
            # "OverflowError: int too long to convert" and nothing else.
            u.GetParent.argtypes = [wintypes.HWND]
            u.GetParent.restype = wintypes.HWND
            u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            u.GetWindowLongW.restype = wintypes.LONG
            u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
            u.SetWindowLongW.restype = wintypes.LONG

            hwnd = self.win.winfo_id()
            hwnd = u.GetParent(hwnd) or hwnd      # the toplevel, not the frame
            style = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            u.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
        except Exception as e:
            self.log(f"fireworks: not click-through ({e!r})")

    def _tick(self):
        if self.cv is None:
            return
        try:
            self.cv.delete("all")
            c = self.cell
            for b in self._bursts:
                for gx, gy, colour in b.cells(self._frame):
                    x, y = gx * c, gy * c
                    self.cv.create_rectangle(x, y, x + c, y + c,
                                             fill=colour, outline="")
        except Exception:
            self.stop()
            return

        self._frame += 1
        if self._frame > self._end:
            self.stop()
            return
        try:
            self._after = self.root.after(FRAME_MS, self._tick)
        except Exception:
            self.stop()

    def stop(self):
        if self._after is not None:
            try:
                self.root.after_cancel(self._after)
            except Exception:
                pass
            self._after = None
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:
                pass
        self.win = self.cv = None
        self._bursts = []
