"""
The five-minute check-in, and the fireworks after ten minutes without the mouse.

Both must work with the API completely off: the check-in is company on a timer,
not a fresh opinion, so it may never cost a call or take a screenshot.

    xvfb-run -a python tests/test_keepalive.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import app as appmod, capture, lang, watcher      # noqa: E402
from core.classify import IDLE, NEUTRAL, STRAY, STUDY       # noqa: E402
from core.watcher import Activity                           # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


GRABS = {"jpeg": 0, "sig": 0}
capture.grab_jpeg_b64 = lambda *a, **k: GRABS.__setitem__("jpeg", GRABS["jpeg"] + 1)
capture.signature = lambda *a, **k: GRABS.__setitem__("sig", GRABS["sig"] + 1)
capture.available = lambda: True
appmod._save_json = lambda *a, **k: None

MOUSE = {"pos": (100, 100)}
watcher.cursor_pos = lambda: MOUSE["pos"]
# idle_seconds matters now: Chatter refuses to speak over someone who is still
# typing, and the default 0.0 would mute him for the whole run.
SCRIPT = {"act": Activity(title="skibidi toilet - YouTube", process="chrome.exe",
                          rect=(0, 0, 1200, 800), idle_seconds=60)}
watcher.foreground = lambda: SCRIPT["act"]

lang.set("ko")
a = appmod.App()
a.cfg["api"]["api_key"] = ""            # everything below must work offline
a.cfg["language"] = "ko"
lang.set("ko")                          # App() applies config.json's language
CALLS = []
a.brain.request_look = lambda *args, **kw: CALLS.append(args) or True


def step(t, act=None, quiet_mouse=False):
    if act:
        SCRIPT["act"] = act
    if not quiet_mouse:                 # keep the fireworks out of the way
        a._mouse_moved = t
        a._woke_at = t
    a.last_poll = 0.0
    appmod.time.time = lambda: t
    try:
        a.poll()
        a.drain_brain()
    finally:
        appmod.time.time = time.time


print("\n--- the check-in, now that its timer wanders ---")
T = 500000.0
# That epoch lands at four in the morning local time, and the late-night line
# is a different trigger with its own pool — it would land in `said` and fail
# the check below for a reason that has nothing to do with the check-in.
a.cfg["late_night_hour"] = 99
step(T)
a.ui.clear_msg()
a.last_line_at = T
said = []
# Two hours at a minute a poll. The gap is jittered and grows with every line,
# so a fixed short window would catch one line on a good seed and none on a
# bad one; the point of the run is WHICH lines come out, not when.
for i in range(1, 121):
    now = T + i * 60
    step(now)                           # mouse "moves" each poll by default
    if a.ui._msg and a.ui._msg not in said:
        said.append(a.ui._msg)
        a.ui.clear_msg()
        a.last_line_at = now - 300      # let the next one through immediately

ok("he says something on his own", said, str(said[:2]))
ok("in Korean", said and any("가" <= c <= "힣" for c in said[0]), repr(said[:1]))
# Match against the pools themselves, not against keywords a random sample may
# or may not happen to contain — that spelling of this check failed about one
# run in ten depending on which three lines came up.
from core import bank as _bank                                 # noqa: E402


def _from_pool(line, names):
    """Is this line one of those pools' templates, placeholders filled in?"""
    for name in names:
        for tpl in _bank.pool(name, "ko"):
            head = tpl.split("{")[0].strip()
            tail = tpl.rsplit("}", 1)[-1].strip()
            if tpl == line or (head and line.startswith(head)) \
                    or (tail and line.endswith(tail)):
                return True
    return False


# The off-task vocabulary: the stray nagging pools plus the flavour pools that
# get mixed into them for whatever he caught you on (youtube, games, shopping).
_stray_pools = [n for n in _bank.EN if "STRAY" in n] + \
    ["BRAINROT", "GAMING", "SHOPPING", "SOCIAL"]
strayish = [s for s in said if _from_pool(s, _stray_pools)]
ok("about straying, since that's the state",
   len(strayish) == len(said),
   str([s for s in said if s not in strayish][:2]))
ok("without a single screenshot", GRABS["jpeg"] == 0 and GRABS["sig"] == 0, str(GRABS))
ok("and without an api call", not CALLS, str(CALLS))
ok("it rotates rather than repeating one line", len(set(said)) > 1, str(len(set(said))))

print("\n--- it follows what you're doing ---")
a.state = STUDY
a.state_since = T
a.last_line_at = 0.0
a.ui.clear_msg()
step(T + 10000, Activity(title="KLAS - 광운대학교", process="chrome.exe",
                         rect=(0, 0, 1200, 800), idle_seconds=60))
# A new window starts its own timer, so bring it forward rather than waiting
# out a jittered five minutes of simulated clock.
a.chatter._seen[a.chatter.here]["next_at"] = 0.0
step(T + 10060)
study_line = a.ui._msg
ok("a study window gets an encouraging line", bool(study_line), repr(study_line))
ok("not a nagging one", "공부하라고" not in study_line, repr(study_line))

a.last_line_at = 0.0
a.ui.clear_msg()
a.state = IDLE
step(T + 20000)
ok("nothing while you're away", "공부하라고" not in a.ui._msg)

print("\n--- fireworks after ten minutes without the mouse ---")
a.state = STUDY
a.ui.clawd.boom_until = 0.0
a._woke_at = 0.0
MOUSE["pos"] = (100, 100)
step(T + 30000)
a._mouse_moved = T + 30000
a._woke_at = 0.0
ok("nothing yet", a.ui.clawd.boom_until <= a.ui.clawd.t)

for i in range(1, 130):                 # ~11 minutes of a still cursor
    step(T + 30000 + i * 5, quiet_mouse=True)
ok("the fireworks go off", a.ui.clawd.boom_until > a.ui.clawd.t,
   f"boom_until={a.ui.clawd.boom_until:.1f} t={a.ui.clawd.t:.1f}")
ok("and he says something", bool(a.ui._msg.strip()), repr(a.ui._msg))
ok("still no screenshot", GRABS["jpeg"] == 0, str(GRABS))

fired = a.ui.clawd.boom_until
for i in range(1, 40):
    step(T + 31000 + i * 5, quiet_mouse=True)
ok("he doesn't set them off again immediately",
   a.ui.clawd.boom_until == fired, "re-fired")

MOUSE["pos"] = (400, 400)               # you move the mouse
a._woke_at = 0.0
step(T + 40000)
ok("moving the mouse resets the timer",
   abs(a._mouse_moved - (T + 40000)) < 1, str(a._mouse_moved))
before = a.ui.clawd.boom_until
for i in range(1, 60):                  # only 5 minutes this time
    step(T + 40000 + i * 5, quiet_mouse=True)
ok("and five quiet minutes is not enough", a.ui.clawd.boom_until == before)

print("\n--- the fireworks draw as whole pixels, above and left of him ---")
from core.sprite import GRID_W, Clawd    # noqa: E402


class _Cv:
    def __init__(self): self.boxes = []
    def create_rectangle(self, x0, y0, x1, y1, fill="", outline=""):
        self.boxes.append((x0, y0, x1, y1, fill)); return len(self.boxes)
    def delete(self, _i): pass


cv = _Cv()
c = Clawd(cv, 0, 0, 10.0)
c.fireworks(4.0)
lit, frames = 0, 0
for i in range(40):
    c.t = i * 0.12
    cv.boxes.clear()
    c._draw_fireworks(0, 0)
    if cv.boxes:
        frames += 1
        lit += len(cv.boxes)
    for x0, y0, x1, y1, _ in cv.boxes:
        if x0 != int(x0) or y0 != int(y0):
            fails.append("fractional firework pixel")
ok("they animate over many frames", frames > 20, f"{frames} frames")
ok("with plenty of sparks", lit > 100, f"{lit} cells")
ok("every spark is on the pixel grid", "fractional firework pixel" not in fails)

cv.boxes.clear()
c.t = 0.5
c._draw_fireworks(0, 0)
ok("they sit above him", all(y1 <= 0 for _, _, _, y1, _ in cv.boxes),
   str(max(b[3] for b in cv.boxes)))
ok("and clear of the speech bubble to his right",
   all(x0 < GRID_W * c.cell * 0.5 for x0, _, _, _, _ in cv.boxes))

a.ui.root.destroy()
lang.set("en")
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
