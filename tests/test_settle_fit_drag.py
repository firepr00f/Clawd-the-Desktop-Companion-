"""
Three fixes:

  * a window must hold still before he reacts to it (a KLAS lecture page
    mid-load is not the page it becomes)
  * a long line resizes the bubble instead of losing its ending
  * being dragged by the mouse makes him kick, without changing his mood

    xvfb-run -a python tests/test_settle_fit_drag.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import app as appmod, capture, watcher            # noqa: E402
from core.classify import STRAY, STUDY                      # noqa: E402
from core.sprite import FLAIL, GRID_H, KICK_STEPS, Clawd    # noqa: E402
from core.watcher import Activity                           # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


SCRIPT = {"act": Activity(title="KLAS - 광운대학교", process="chrome.exe",
                          rect=(0, 0, 1200, 800))}
watcher.foreground = lambda: SCRIPT["act"]
watcher.cursor_pos = lambda: (10, 10)
capture.available = lambda: False
capture.signature = lambda *a, **k: None
appmod._save_json = lambda *a, **k: None

a = appmod.App()
a.cfg["api"]["api_key"] = ""
a.cfg["window_settle_seconds"] = 2.0


def step(t, title=None, proc="chrome.exe"):
    if title is not None:
        SCRIPT["act"] = Activity(title=title, process=proc, rect=(0, 0, 1200, 800))
    a._mouse_moved = t
    a._woke_at = t
    a.last_poll = 0.0
    appmod.time.time = lambda: t
    try:
        a.poll()
    finally:
        appmod.time.time = time.time


print("\n--- a window has to hold still for 2s ---")
T = 900000.0
step(T, "KLAS - 광운대학교")
step(T + 5, "KLAS - 광운대학교")
ok("settled on the lecture page", a.state == STUDY, a.state)

# the KLAS viewer loading: a blank/placeholder title for a moment
step(T + 10, "", "chrome.exe")
ok("a blank title mid-load does NOT flip him", a.state == STUDY, a.state)
step(T + 11, "새 탭", "chrome.exe")
ok("nor does a one-poll placeholder", a.state == STUDY, a.state)
step(T + 12, "KLAS - 광운대학교")
ok("and he is still on the lecture when it finishes loading",
   a.state == STUDY, a.state)

print("\n--- but a real switch still lands, after the settle ---")
for i in range(6):
    step(T + 20 + i * 5, "skibidi toilet - YouTube")
ok("a window you actually stay on does flip him", a.state == STRAY, a.state)

print("\n--- ...and it took about the settle time, not one poll ---")
a2_states = []
for i in range(6):
    step(T + 100 + i * 5, "KLAS - 광운대학교")
    a2_states.append(a.state)
ok("the first poll after the change is still the old verdict",
   a2_states[0] == STRAY, str(a2_states))
ok("and it commits shortly after", a2_states[-1] == STUDY, str(a2_states))
ok("settle is configurable", a.tune("window_settle_seconds", default=None) == 2.0)

print("\n--- a long line resizes the bubble instead of losing its end ---")
LONG = ("tidbit: watching videos at 1.5x speed makes your brain work harder to "
        "process audio, so you retain less despite feeling more efficient. the "
        "fluency illusion makes faster playback feel like it is working.")
a.ui.say(LONG, 60, time.time())
a.ui.render(0.07, time.time(), "curious")
drawn = [i for i in a.ui._bubble_items if a.ui.cv.type(i) == "text"]
shown = a.ui.cv.itemcget(drawn[0], "text") if drawn else ""
ok("the whole line is rendered", shown == LONG, repr(shown[-30:]))
ok("nothing was truncated", "…" not in shown, repr(shown[-30:]))

boxes = [a.ui.cv.bbox(i) for i in a.ui._bubble_items if a.ui.cv.bbox(i)]
bottom = max(b[3] for b in boxes)
ok("it still sits above him", bottom <= a.ui.CLAWD_OY, f"{bottom} vs {a.ui.CLAWD_OY}")
ok("and stays on the canvas",
   min(b[0] for b in boxes) >= 0 and max(b[2] for b in boxes) <= a.ui.W)

a.ui.say("short one", 60, time.time())
a.ui.render(0.07, time.time(), "curious")
ok("the font is restored for the next short line",
   a.ui.font.cget("size") == a.ui.font_size,
   f"{a.ui.font.cget('size')} vs {a.ui.font_size}")

huge = "가나다라마바사 " * 200
a.ui.say(huge, 60, time.time())
a.ui.render(0.07, time.time(), "curious")
boxes = [a.ui.cv.bbox(i) for i in a.ui._bubble_items if a.ui.cv.bbox(i)]
ok("something genuinely enormous is still trimmed rather than overflowing",
   max(b[3] for b in boxes) <= a.ui.CLAWD_OY and min(b[1] for b in boxes) >= 0,
   f"{min(b[1] for b in boxes)}..{max(b[3] for b in boxes)}")

print("\n--- and the source lines got shorter too ---")
from core import bank                                       # noqa: E402
for code in ("en", "ko"):
    tips = bank.pool("TIDBITS", code)
    longest = max(len(x) for x in tips)
    ok(f"{code}: every offline tidbit fits a bubble", longest <= 145, f"longest {longest}")

b = a.brain
b.cfg = {"api": {"max_line_chars": 200}}
cut = b.shorten(LONG + " and then some more text that runs well past the cap.")
ok("an over-long api line is cut at a sentence break",
   cut.endswith(".") and len(cut) <= 200, f"{len(cut)}: {cut[-40:]!r}")
ok("not mid-word", not cut.endswith("…") or " " not in cut[-3:])

print("\n--- dragging: he kicks ---")


class _Cv:
    def __init__(self): self.boxes = []
    def create_rectangle(self, x0, y0, x1, y1, fill="", outline=""):
        self.boxes.append((x0, y0, x1, y1, fill)); return len(self.boxes)
    def delete(self, _i): pass


cv = _Cv()
c = Clawd(cv, 0, 0, 10.0)
c.set_mood("annoyed")

c.dragging = False
c.frame = 0
_, _, _, _, _, calm = c._pose()
ok("standing still, no kicks", all(k == 0 for _, _, k in calm), str(calm))

c.dragging = True
seen_dirs, shapes = set(), set()
for f in range(len(FLAIL) * 3):
    c.frame = f
    dx, dy, al, ar, sq, legs = c._pose()
    for _, _, k in legs:
        seen_dirs.add(k)
    shapes.add(tuple(k for _, _, k in legs))
    vals = [dx, dy, al, ar, sq] + [v for leg in legs for v in leg]
    if any(v != int(v) for v in vals):
        fails.append("fractional drag offset")
ok("every leg kicks", 0 not in seen_dirs, str(seen_dirs))
ok("in both directions", {-1, 1} <= seen_dirs, str(seen_dirs))
ok("and the pattern changes frame to frame", len(shapes) == len(FLAIL), str(len(shapes)))
ok("all on the pixel grid", "fractional drag offset" not in fails)

cv.boxes.clear()
c.frame = 0
c.draw()
# the flail lifts the body a cell, so the top stair sits a cell higher
legs_drawn = [b for b in cv.boxes if b[1] >= c.oy + (GRID_H - 4) * c.cell]
ok("the legs are drawn as diagonal staircases",
   len(legs_drawn) >= 4 * KICK_STEPS, f"{len(legs_drawn)} blocks")
xs = sorted({b[0] for b in legs_drawn})
ok("which means they reach sideways, not straight down", len(xs) > 4, str(len(xs)))

print("\n--- mood and options survive being picked up ---")
for mood in ("annoyed", "sleepy", "happy", "quiz"):
    c.set_mood(mood)
    c.dragging = True
    cv.boxes.clear()
    c.draw()
    ok(f"{mood}: mood is kept while dragging", c.mood == mood, c.mood)
    black = [b for b in cv.boxes if b[4] == "#141414"]
    ok(f"{mood}: the eyes still render", len(black) >= 2, f"{len(black)} dark blocks")

c.set_mood("happy")
c.dragging = True
c.hold(["................"] * 16)
c.fireworks(3.0)
cv.boxes.clear()
c.draw()
ok("a held item is still shown while dragging", c.held is not None)
ok("and the fireworks keep going", c.boom_until > c.t)

from core.sprite import FLAIL_TEMPO, TEMPO, WALK_TEMPO      # noqa: E402
ok("kicking is slower than walking, not a blur",
   FLAIL_TEMPO > WALK_TEMPO, f"{FLAIL_TEMPO} / {WALK_TEMPO}")
ok("but still a real animation, not a crawl", FLAIL_TEMPO <= 0.25, str(FLAIL_TEMPO))
ok("the body never slides sideways while he kicks",
   all(entry[0] == 0 for entry in FLAIL), str([e[0] for e in FLAIL]))
ok("the kicking legs are stubby", KICK_STEPS <= 2, str(KICK_STEPS))

print("\n--- the ui sets and clears the flag ---")


class _E:
    x_root = y_root = 300


a.ui._press(_E())
a.ui._motion(_E())
ok("dragging him turns it on", a.ui.clawd.dragging)
a.ui._release(_E())
ok("letting go turns it off", not a.ui.clawd.dragging)

print("\n--- there is no menu on the sprite any more ---")
for gone in ("on_menu", "_right", "_right_double", "begin_menu", "end_menu",
             "menu_is_up", "frozen", "freeze_motion", "menu_widget"):
    ok(f"Overlay.{gone} is gone", not hasattr(a.ui, gone))
bound = set(a.ui.cv.bind())
ok("and nothing is bound to the right button",
   not any("Button-3" in b for b in bound), str(sorted(bound)))
ok("the app has no popup either",
   not any(hasattr(a, n) for n in ("on_menu", "close_menu", "tray_clicked")))
ok("the menu it does have is data, for the tray",
   isinstance(a.menu_spec(), list) and all(
       x is None or (isinstance(x, tuple) and callable(x[1])) for x in a.menu_spec()))

print("\n--- and now nothing stops him moving ---")
a.motion.pos = (a.ui.x + 400.0, float(a.ui.y))
a.motion.walking = True
before = (a.ui.x, a.ui.y)
a.last_tick = time.time() - 0.03
a._frame()
ok("the window moves with no menu to hold it back", (a.ui.x, a.ui.y) != before,
   f"{before} -> {(a.ui.x, a.ui.y)}")
ok("and he is animated mid-stride", a.ui.clawd.walking)
ok("place() has nothing left to defer to", not hasattr(a.ui, "_deferred_pos"))

print("\n--- escape still drops an open question ---")
a.start_quiz("q?", "ans")
ok("the box is open", a.ui.entry_open)
a.ui._escape()
ok("escape closes it", not a.ui.entry_open)
ok("and leaves quiz mode", a.quiz is None)

print("\n--- every command drops the one before it ---")
# The rule, and it has no exceptions: TrackPopupMenu returns one id, so a
# double-delivered item is no longer a thing that can happen — but a command
# arriving while the last one is still in flight very much is.
a.start_quiz("still waiting for this", "answer")
a._look_pending = True
before_id = getattr(a, "_check_id", 0)
ran = []
a.command(lambda: ran.append(1))()
ok("the new command runs", len(ran) == 1)
ok("the open question is gone", a.quiz is None and not a.ui.entry_open)
ok("the in-flight look is disowned", not a._look_pending)
ok("and a capture already scheduled is invalidated",
   getattr(a, "_check_id", 0) != before_id)

print("\n--- the frame loop cannot double up ---")
calls = []
real_after = a.ui.root.after
a.ui.root.after = lambda ms, fn=None, *rest: (calls.append(ms), 1)[1]
a._in_frame = True
a.frame()                                # re-entrant: from inside a posted menu
ok("a re-entrant frame schedules nothing", not calls, str(calls))
a._in_frame = False
a.frame()
ok("a normal frame schedules exactly one", len(calls) == 1, str(calls))
a.ui.root.after = real_after

a.ui.root.destroy()
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
