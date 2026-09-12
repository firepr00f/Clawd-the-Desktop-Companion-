"""
The double-click check, and the bubble geometry.

Double-clicking Clawd is now the ONLY thing in the app that reads your screen.
He looks once, decides studying / straying / can't-tell, and reacts in kind —
including a 'confused' face with a question mark when he genuinely cannot call
it. This pins down all three landings, in both languages, online and off.

Also still checks that the title normaliser strips the noise that used to make
a ticking video clock look like a brand new window.

    xvfb-run -a python tests/test_watch_ui.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import app as appmod, capture, lang, watcher   # noqa: E402
from core import screenwatch as sw                       # noqa: E402
from core.sprite import EYE_FOR_MOOD, IDLE, MOODS, TEMPO  # noqa: E402
from core.watcher import Activity                        # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


print("\n--- titles: noise stripped, real changes kept ---")
same = [
    ("KLAS - 광운대학교 - Google Chrome", " (12) KLAS - 광운대학교 — Google Chrome"),
    ("lecture 3  12:03 / 48:20 - Chrome", "lecture 3  31:57 / 48:20 - Chrome"),
    ("* main.py - Visual Studio Code", "main.py - Visual Studio Code"),
]
for a_t, b_t in same:
    ok(f"{a_t[:34]:36} == the noisy version",
       sw.normalise(a_t) == sw.normalise(b_t),
       f"{sw.normalise(a_t)!r} vs {sw.normalise(b_t)!r}")
ok("but a real page change still reads as one",
   sw.normalise("KLAS - 광운대") != sw.normalise("YouTube - 광운대"))
ok("nothing but normalise survived the watcher",
   not hasattr(sw, "ScreenWatch") and not hasattr(sw, "Look"),
   str([n for n in dir(sw) if not n.startswith("_")]))


# ---------------------------------------------------------------- the check

def act_of(title, proc="chrome.exe"):
    return Activity(title=title, process=proc, idle_seconds=0.0,
                    rect=(0, 0, 1920, 1080))


SCRIPT = {"act": act_of("KLAS - 광운대학교")}
watcher.foreground = lambda: SCRIPT["act"]
watcher.cursor_pos = lambda: (10, 10)
capture.available = lambda: True
capture.grab_jpeg_b64 = lambda *a, **k: "ZmFrZQ=="
capture.signature = lambda *a, **k: None
appmod._save_json = lambda *a, **k: None

a = appmod.App()
a.cfg["api"]["api_key"] = "test-key"
a.cfg["api"]["hide_self_while_capturing"] = False
a.budget.over = lambda: False


def check_with(verdict, line="", topic="ch4 electromagnetics"):
    """Run one whole double-click, with the model answering `verdict`."""
    a.reset_neutral("test")
    a.last_line_at = 0.0
    a._look_mode = "check"
    a.apply_look({"topic": topic, "detail": "", "item": topic,
                  "verdict": verdict, "line": line})


print("\n--- the three ways a look can land ---")
WANT = {"study": "proud", "stray": "annoyed", "unsure": "confused"}
for verdict, mood in WANT.items():
    check_with(verdict, f"a line about {verdict}")
    ok(f"{verdict:6} -> {mood}", a.mood == mood, a.mood)
    ok(f"{verdict:6} -> he says the model's line",
       f"about {verdict}" in a.ui._msg, repr(a.ui._msg[:40]))

print("\n--- and he still speaks when the model sends no line ---")
for verdict, mood in WANT.items():
    check_with(verdict, "")
    ok(f"{verdict:6} -> falls back to the bank", bool(a.ui._msg.strip()),
       repr(a.ui._msg[:50]))
    ok(f"{verdict:6} -> with the right face", a.mood == mood, a.mood)

print("\n--- an unreadable screen is 'unsure', never a guess ---")
for topic in ("unreadable", "a browser", ""):
    check_with("study", "", topic=topic)
    ok(f"topic={topic!r:14} -> confused, not proud", a.mood == "confused", a.mood)
check_with("nonsense-verdict", "")
ok("so is a verdict he made up", a.mood == "confused", a.mood)

print("\n--- in Korean too ---")
lang.set("ko")
for verdict, mood in WANT.items():
    check_with(verdict, "")
    hangul = any("가" <= c <= "힣" for c in a.ui._msg)
    ok(f"{verdict:6} -> Korean line", hangul, repr(a.ui._msg[:40]))
    ok(f"{verdict:6} -> same face", a.mood == mood, a.mood)
lang.set("en")

print("\n--- with no api key he still judges, from the title alone ---")
a.cfg["api"]["api_key"] = ""
for title, proc, mood in (("KLAS - 광운대학교", "chrome.exe", "proud"),
                          ("skibidi toilet - YouTube", "chrome.exe", "annoyed"),
                          ("바탕 화면", "explorer.exe", "confused")):
    a.reset_neutral("test")
    a.last_line_at = 0.0
    a.last_act = act_of(title, proc)
    a.offline_check()
    ok(f"offline {title[:22]:24} -> {mood}", a.mood == mood, a.mood)
    ok(f"offline {title[:22]:24} -> says something", bool(a.ui._msg.strip()))
a.cfg["api"]["api_key"] = "test-key"

print("\n--- a look can let a hated window off ---")
# The point of being able to check: a lecture that lives on YouTube is judged
# by what is ON the screen, not by the word in the title.
LECTURE = "전자기학 특강 풀강의 - YouTube"
lect = act_of(LECTURE)

a.reset_neutral("test")
a._pardoned.clear()
a.stray_tier = 2
a.state = "stray"
a.last_act = lect
a.topic = "electromagnetics lecture"
# Before the look, the title alone says nothing useful: a lecture on YouTube
# is off the allowlist and no longer on the blacklist, so tier 1 shrugs. That
# shrug is the whole point of the double-click — it is what the look resolves.
_pre = __import__("core.classify", fromlist=["classify"]).classify(lect, a.cfg)
ok("before the look he has no opinion", _pre.state == "neutral", _pre.state)
ok("and says so, rather than guessing", _pre.reason == "unknown", _pre.reason)

a.last_line_at = 0.0
a._look_mode = "check"
a.apply_look({"topic": "electromagnetics lecture", "detail": "", "item": "book",
              "verdict": "study", "line": ""})
ok("the look forgives that window", a.is_pardoned(lect))
ok("and he says so", bool(a.ui._msg.strip()), repr(a.ui._msg[:44]))
ok("the anger comes off with it", a.stray_tier == 0, str(a.stray_tier))
ok("he treats it as studying now", a.state == "study", a.state)
ok("with a face to match", a.mood == "proud", a.mood)

v = a.settled_verdict(1000.0, lect)
ok("and the keyword rules no longer override him", v.is_study, v.state)
ok("the reason is on the record", v.reason == "pardoned", v.reason)

print("\n--- but the pardon is for that window only ---")
other = act_of("skibidi toilet - YouTube")
from core.classify import classify as _classify                # noqa: E402
ok("another YouTube tab is still hated",
   _classify(other, a.cfg).hated == "YouTube", _classify(other, a.cfg).hated)
ok("and is not pardoned", not a.is_pardoned(other))
ok("a ticking clock does not un-pardon the lecture",
   a.is_pardoned(act_of("▶ " + LECTURE + "  12:03 / 48:20")),
   a.pardon_key(lect))

print("\n--- and a later look can take it back ---")
a.last_act = lect
a.last_line_at = 0.0
a._look_mode = "check"
a.apply_look({"topic": "a music video", "detail": "", "item": "tv",
              "verdict": "stray", "line": ""})
ok("checking again and finding otherwise revokes it", not a.is_pardoned(lect))
ok("and he is cross again", a.mood == "annoyed", a.mood)

print("\n--- pardons expire, and do not pile up ---")
a._pardoned.clear()
a._pardoned[a.pardon_key(lect)] = 1.0          # long past
ok("an expired pardon does not count", not a.is_pardoned(lect))
ok("and is forgotten", not a._pardoned)
for i in range(60):
    a._pardoned[f"window {i}"] = 9e9
a.last_act = lect
a.pardon(lect)
ok("the list is capped rather than growing forever", len(a._pardoned) <= 41,
   str(len(a._pardoned)))
a._pardoned.clear()
a.reset_neutral("cleanup")

print("\n--- the confused sprite exists and is its own thing ---")
ok("it is a real mood", "confused" in MOODS)
ok("with its own eyes", EYE_FOR_MOOD["confused"] != EYE_FOR_MOOD["quiz"])
ok("its own idle loop", IDLE["confused"] != IDLE["quiz"])
ok("and its own tempo", "confused" in TEMPO)
ok("every offset is a whole cell",
   all(all(v == int(v) for v in fr) for fr in IDLE["confused"]),
   str(IDLE["confused"]))


class _Cv:
    def __init__(self): self.boxes = []
    def create_rectangle(self, x0, y0, x1, y1, fill="", outline=""):
        self.boxes.append((x0, y0, x1, y1, fill)); return len(self.boxes)
    def delete(self, _i): pass


from core.sprite import Clawd                             # noqa: E402
cv = _Cv()
c = Clawd(cv, 0, 0, 10.0)


def marks_above(mood, frame):
    c.set_mood(mood)
    c.frame = frame
    cv.boxes.clear()
    c.draw()
    return [b for b in cv.boxes if b[1] < c.oy]           # anything over his head


conf = [len(marks_above("confused", f)) for f in range(4)]
quiz = [len(marks_above("quiz", f)) for f in range(4)]
ok("he wears question marks when confused", min(conf) > 0, str(conf))
ok("more of them than the quiz mark", max(conf) > max(quiz), f"{conf} vs {quiz}")
ok("and they blink rather than sitting still", len(set(conf)) > 1, str(conf))

a.ui.root.destroy()


# ---------------------------------------------------------------- bubble

print("\n--- bubble geometry ---")
try:
    import tkinter  # noqa: F401
    from core.ui import Overlay

    cfg = {"appearance": {"pixel_size": 9, "font_size": 16, "bubble_width": 640,
                          "bubble_max_height": 460, "auto_dpi_scale": False}}
    o = Overlay(cfg, lambda: None, lambda e: None, lambda t: None)

    old_w, old_h, old_bubble = 470, 330, 292
    ok("canvas is wider than the old build", o.W > old_w, f"{o.W} > {old_w}")
    ok("canvas is taller than the old build", o.H > old_h, f"{o.H} > {old_h}")
    ok("bubble text column is ~2.2x the old one",
       2.0 <= o.bubble_w / old_bubble <= 2.4, f"{o.bubble_w}/{old_bubble}")
    ok("bubble has room to grow without clipping",
       o.anchor_bottom - o.bubble_max_h > 0,
       f"top would be {o.anchor_bottom - o.bubble_max_h}")
    ok("clawd fits inside the canvas with his decorations",
       o.CLAWD_OX > 0 and o.CLAWD_OY + o.clawd.height_px < o.H,
       f"ox={o.CLAWD_OX} oy={o.CLAWD_OY} H={o.H}")

    long_text = ("tidbit: the first transatlantic telegraph cable failed because "
                 "the operators pushed 2000 volts through it trying to go faster, "
                 "which cooked the insulation in three weeks. " * 3)
    o.say(long_text, 30, time.time())
    o.render(0.07, time.time(), "curious")
    xs = [o.cv.bbox(i) for i in o._bubble_items if o.cv.bbox(i)]
    ok("a long line renders inside the canvas",
       xs and min(b[1] for b in xs) >= 0 and max(b[3] for b in xs) <= o.H,
       f"top={min(b[1] for b in xs)} bottom={max(b[3] for b in xs)} H={o.H}")
    ok("a long line uses the full bubble width",
       max(b[2] for b in xs) - min(b[0] for b in xs) > old_bubble,
       f"width={max(b[2] for b in xs) - min(b[0] for b in xs)}")

    o.say("short one", 10, time.time())
    o.render(0.07, time.time(), "happy")
    ok("a short line still draws a bubble", len(o._bubble_items) > 5)

    o.root.destroy()
except ImportError as e:
    print(f"  skip  tkinter unavailable ({e})")


print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
