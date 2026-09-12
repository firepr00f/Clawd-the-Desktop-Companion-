"""
When he is allowed to say something unprompted, and which line he uses.

The old rule was one line every five minutes, forever. Two of those and you
have learned the rhythm; once you have learned it he is background noise, and
an hour on one window is twelve interruptions, which is not company, it is a
dripping tap.

Three things replace it, and they matter in this order:

  * **Jitter.** The gap is multiplied by a random 0.7–1.3 every time. This is
    the one that actually stops the rhythm being learnable, and if only one of
    these survived it should be this one.
  * **Decay.** Each line on the same window pushes the next one further out —
    5, 8, 13, 20, then 30 minutes and no further. He introduces himself to a
    new window and then leaves you alone in it.
  * **Memory of where you have been.** Alt-tabbing away and back would reset
    the counter and start the nagging over, which is the single most irritating
    way this could fail. A window you left less than ten minutes ago comes back
    with its count intact.

Plus two mutes that override all of the above: he does not speak into a
full-screen window, and he does not speak while you are mid-keystroke.
"""

from __future__ import annotations

import random
import time
from collections import deque


def key_for(act) -> tuple[str, int]:
    """
    What counts as 'the same window'.

    The title is hashed rather than kept: the counter only ever needs to know
    whether this is the same window as last time, and a hash cannot be read
    back out of memory as a list of what you had open.
    """
    return ((act.process or "").lower(), hash((act.title or "").strip().lower()))


class Chatter:
    def __init__(self, cfg: dict, log=lambda *a: None):
        self.cfg = cfg
        self.log = log
        self.here: tuple | None = None          # the window he is watching now
        self._seen: dict[tuple, dict] = {}      # key -> {n, left_at, next_at, pool}
        self._recent: deque[str] = deque(maxlen=self._tune("recent_lines_buffer", 20))

    # -- config ---------------------------------------------------------

    def _tune(self, name, default):
        node = (self.cfg.get("chatter") or {})
        try:
            return type(default)(node.get(name, default))
        except (TypeError, ValueError):
            return default

    def wait(self, n: int) -> float:
        """
        How long to stay quiet after the nth line on this window.

        min(base * growth**n, cap), then jittered. The cap is what stops the
        exponential running away to a gap so long it may as well be never.
        """
        base = self._tune("base_interval_sec", 300.0)
        growth = self._tune("growth", 1.6)
        cap = self._tune("cap_sec", 1800.0)
        jitter = max(0.0, min(0.9, self._tune("jitter", 0.3)))
        gap = min(base * (growth ** max(0, n)), cap)
        return gap * random.uniform(1.0 - jitter, 1.0 + jitter)

    # -- where he is ----------------------------------------------------

    def arrive(self, now: float, key: tuple):
        """
        He is looking at `key` now. Returns nothing; sets the next due time.

        A window he left recently keeps its count. Anything older than
        window_memory_sec is forgotten, so a window you genuinely came back to
        tomorrow gets a fresh introduction.
        """
        if key == self.here:
            return
        if self.here is not None:
            self._seen.setdefault(self.here, {"n": 0})["left_at"] = now
        # Prune BEFORE adopting the new window. The other order looks the same
        # and is not: `_forget` spares whatever `here` points at, so setting it
        # first makes the window you are arriving at permanently unforgettable
        # — it keeps a count from hours ago and greets you mid-decay.
        self._forget(now)
        self.here = key

        slot = self._seen.get(key)
        if slot is None:
            slot = self._seen[key] = {"n": 0, "left_at": 0.0, "pool": ""}
        slot["next_at"] = now + self.wait(slot["n"])

    def _forget(self, now: float):
        memory = self._tune("window_memory_sec", 600.0)
        for k, slot in list(self._seen.items()):
            if k == self.here:
                continue
            left = slot.get("left_at", 0.0)
            if left and now - left > memory:
                del self._seen[k]

    def count(self, key=None) -> int:
        return self._seen.get(key or self.here, {}).get("n", 0)

    # -- may he speak ---------------------------------------------------

    def muted(self, act, bounds=None) -> str:
        """A reason to stay quiet regardless of the timer, or ''."""
        hush = self._tune("silence_after_input_sec", 30.0)
        if hush and getattr(act, "idle_seconds", 0.0) < hush:
            return "mid-keystroke"
        if bounds and self._fullscreen(act, bounds):
            return "full screen"
        return ""

    @staticmethod
    def _fullscreen(act, bounds) -> bool:
        """
        The foreground window covers the whole desktop.

        A few pixels of slack: a maximised window and a genuinely full-screen
        one differ by the odd border, and for this purpose they are the same
        thing — you are watching something, not working in a window.
        """
        r = getattr(act, "rect", None)
        if not r or not bounds:
            return False
        l, t, rr, b = r
        bl, bt, br, bb = bounds
        return (l <= bl + 2 and t <= bt + 2 and rr >= br - 2 and b >= bb - 2)

    def due(self, now: float, key=None) -> bool:
        slot = self._seen.get(key or self.here)
        if slot is None:
            return False
        return now >= slot.get("next_at", 0.0)

    def spoke(self, now: float, pool: str = "", key=None):
        """Record a line: the count goes up and the next gap is drawn."""
        slot = self._seen.setdefault(key or self.here, {"n": 0, "left_at": 0.0})
        slot["n"] = slot.get("n", 0) + 1
        slot["pool"] = pool
        slot["next_at"] = now + self.wait(slot["n"])

    def engaged(self, now: float = 0.0, key=None):
        """
        You touched him. Interest earns back one step of the decay.

        Not a reset: one step, so a single click does not undo an hour of him
        learning to leave you alone.
        """
        slot = self._seen.get(key or self.here)
        if slot:
            slot["n"] = max(0, slot.get("n", 0) - 1)
            if now:
                slot["next_at"] = now + self.wait(slot["n"])

    def last_pool(self, key=None) -> str:
        return self._seen.get(key or self.here, {}).get("pool", "")

    # -- which line -----------------------------------------------------

    def fresh(self, lines, fallback=None):
        """
        A line he has not used lately.

        The ring buffer holds the last N he said. Candidates outside it are
        preferred; when a pool is small enough that they are all in there, the
        buffer is cleared rather than the line repeated — running out is not a
        reason to say nothing.
        """
        pool = [ln for ln in (lines or []) if ln]
        if not pool:
            return fallback
        unused = [ln for ln in pool if ln not in self._recent]
        if not unused:
            self._recent.clear()
            unused = pool
        pick = random.choice(unused)
        self._recent.append(pick)
        return pick

    def remember(self, line: str):
        """Record a line chosen elsewhere, so it is not immediately repeated."""
        if line:
            self._recent.append(line)
