"""
Where Clawd stands, and how he gets there.

He moves the whole overlay window around the screen. Modes:

    home     back to his corner
    follow   shadows your mouse cursor, just off to the side
    block    walks to the middle of the window you're slacking in and sits there
    patrol   paces back and forth across the top of that window

He never intercepts your clicks — the transparent parts of the window are
click-through, and he steps aside on his own every so often so he is annoying
rather than actually obstructive.
"""

from __future__ import annotations

import random

from . import watcher

HOME, FOLLOW, BLOCK, PATROL = "home", "follow", "block", "patrol"


class Motion:
    def __init__(self, cfg, clawd_offset, win_size, screen_size, log=lambda *a: None,
                 sprite_size=(0, 0), screen_rect=None):
        self.cfg = cfg
        self.ox, self.oy = clawd_offset          # Clawd's origin inside the window
        self.ww, self.wh = win_size
        self.sw, self.sh = screen_size
        # what actually has to stay visible: the sprite, not the window, most of
        # which is transparent bubble space above him
        self.spw, self.sph = sprite_size or (win_size[0], win_size[1])
        self.screen_rect = screen_rect or (0, 0, screen_size[0], screen_size[1])
        self.log = log

        self.mode = HOME
        self.home = (0.0, 0.0)                   # window top-left
        self.pos = (0.0, 0.0)
        self.target_rect: tuple[int, int, int, int] | None = None
        self.walking = False
        self._patrol_dir = 1
        self._aside_until = 0.0
        self._t = 0.0

    # ------------------------------------------------------------------

    def start_at(self, x: float, y: float):
        self.home = (float(x), float(y))
        self.pos = (float(x), float(y))

    def set_mode(self, mode: str, rect=None):
        if rect:
            self.target_rect = rect
        if mode != self.mode:
            self.mode = mode
            self._aside_until = 0.0
            if mode == PATROL:
                self._patrol_dir = random.choice((-1, 1))

    def step_aside(self, seconds: float = 15.0):
        self._aside_until = self._t + seconds

    @property
    def speed(self) -> float:
        return float(self.cfg.get("motion", {}).get("speed_px_per_sec", 260))

    # ------------------------------------------------------------------

    def _clamp(self, x, y):
        """
        Keep the SPRITE inside the desktop.

        The old version bounded the window, which on a scaled display let him
        walk 600+ px below the bottom edge and vanish — the window's top half is
        transparent bubble space, so "the window is on screen" is not remotely
        the same as "you can see him".
        """
        l, t, r, b = self.screen_rect
        margin = 6
        lo_x, hi_x = l + margin - self.ox, r - margin - self.spw - self.ox
        lo_y, hi_y = t + margin - self.oy, b - margin - self.sph - self.oy
        if hi_x < lo_x:
            lo_x = hi_x = (lo_x + hi_x) / 2.0
        if hi_y < lo_y:
            lo_y = hi_y = (lo_y + hi_y) / 2.0
        return max(lo_x, min(hi_x, x)), max(lo_y, min(hi_y, y))

    def _sane_rect(self, r):
        """
        Reject a window rect we shouldn't chase.

        A minimised window on Windows reports (-32000, -32000, ...), and walking
        to the middle of that is exactly how he ends up in another postcode.
        """
        if not r:
            return None
        try:
            left, top, right, bottom = (int(v) for v in r)
        except (TypeError, ValueError):
            return None
        left, right = min(left, right), max(left, right)
        top, bottom = min(top, bottom), max(top, bottom)
        if right - left < 80 or bottom - top < 80:
            return None
        sl, st, sr, sb = self.screen_rect
        # must actually overlap the desktop by a meaningful amount
        if right <= sl + 40 or left >= sr - 40 or bottom <= st + 40 or top >= sb - 40:
            return None
        return (left, top, right, bottom)

    def _window_for_clawd(self, cx, cy):
        """Window top-left that puts Clawd's grid origin at screen (cx, cy)."""
        return cx - self.ox, cy - self.oy

    def _target(self) -> tuple[float, float]:
        r = self._sane_rect(self.target_rect)
        if self.mode == FOLLOW:
            c = watcher.cursor_pos()
            if c:
                # sit just below-right of the cursor, out of the way of typing
                return self._window_for_clawd(c[0] + 40, c[1] + 46)
            return self.home

        if self.mode in (BLOCK, PATROL) and r:
            left, top, right, bottom = r
            left, right = min(left, right), max(left, right)
            top, bottom = min(top, bottom), max(top, bottom)
            if self._aside_until > self._t:
                return self._window_for_clawd(right - 150, bottom - 140)
            if self.mode == BLOCK:
                return self._window_for_clawd((left + right) / 2 - 80,
                                              (top + bottom) / 2 - 50)
            span = max(120, (right - left) - 260)
            x = left + 130 + (span if self._patrol_dir > 0 else 0)
            return self._window_for_clawd(x, top + (bottom - top) * 0.35)

        if self.mode == BLOCK:                    # no rect known -> screen centre
            return self._window_for_clawd(self.sw / 2 - 80, self.sh / 2 - 50)

        return self.home

    # ------------------------------------------------------------------

    def update(self, dt: float) -> tuple[int, int]:
        """Advance one frame. Returns the window position to place."""
        self._t += dt
        tx, ty = self._clamp(*self._target())
        x, y = self.pos
        dx, dy = tx - x, ty - y
        dist = (dx * dx + dy * dy) ** 0.5

        if dist < 2.0:
            self.walking = False
            if self.mode == PATROL:               # reached the end, turn around
                self._patrol_dir *= -1
            self.pos = (tx, ty)
        else:
            step = min(dist, self.speed * dt)
            self.pos = (x + dx / dist * step, y + dy / dist * step)
            self.walking = dist > 6.0

        # in block mode, get out of the way now and then so he stays comedic
        if self.mode == BLOCK and self._aside_until <= self._t:
            cycle = float(self.cfg.get("motion", {}).get("block_seconds", 40))
            if cycle and (self._t % (cycle + 14)) > cycle:
                self.step_aside(14)

        return int(round(self.pos[0])), int(round(self.pos[1]))
