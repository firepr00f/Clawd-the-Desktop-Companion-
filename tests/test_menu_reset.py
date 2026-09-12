"""
A command always wins over the one before it.

The rule, in one line: whatever you ask for next drops whatever is happening
now — immediately, unconditionally, and whether or not the old thing was
finished. There is exactly one place that rule lives, `App.command`, and every
entry point goes through it: every tray item, and the double-click.

Two bugs this pins down, one old and one that the popup's removal made
possible.

  * 'fun tidbit' silently did nothing while a question was open. The wrapper
    cancelled the *mode* but left the old bubble up, so `ui.talking` was still
    true, so `can_speak()` refused, so it returned without a word — no error,
    no line, nothing at all.
  * A screen check started a second earlier would land *after* the command you
    asked for instead, overwriting it, because the capture and its API call
    were still in flight and nothing had told them they were obsolete.

    xvfb-run -a python tests/test_menu_reset.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import app as appmod, capture, watcher      # noqa: E402
from core.watcher import Activity                     # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


watcher.foreground = lambda: Activity(title="t", process="chrome.exe", rect=(0, 0, 900, 700))
watcher.cursor_pos = lambda: (10, 10)
capture.available = lambda: False
capture.signature = lambda *a, **k: None
appmod._save_json = lambda *a, **k: None

a = appmod.App()
a.cfg["api"]["api_key"] = ""            # offline: every line comes from the bank

items = lambda: dict((e[0], e[1]) for e in a.menu_spec() if e)   # noqa: E731


def pick(*words):
    """The menu item whose label contains any of these, already wrapped."""
    for label, fn in items().items():
        if any(w in label for w in words):
            return fn
    raise AssertionError(f"no menu item matching {words}: {list(items())}")


print("\n--- there is one menu, and the tray has it ---")
ok("the sprite has no popup", not hasattr(a.ui, "on_menu"))
ok("nor a right button at all",
   not any("Button-3" in b for b in a.ui.cv.bind()), str(sorted(a.ui.cv.bind())))
ok("the app has no Tk menu either",
   not any(hasattr(a, n) for n in ("on_menu", "close_menu", "_menu", "tray_clicked")))
ok("the tray builds it from menu_spec", a.tray.build_menu == a.menu_spec)
ok("and every entry is a label and something to run",
   all(e is None or (isinstance(e[0], str) and callable(e[1]))
       for e in a.menu_spec()))


print("\n--- a command with a question already on screen ---")
a.start_quiz("what is tau in an RC circuit?", "tau = RC")
ok("the quiz is up", a.quiz is not None and a.ui.talking)
ok("and he is deliberately quiet", not a.can_speak(5))

pick("fun tidbit", "잡지식")()
ok("the quiz is dropped", a.quiz is None)
ok("the answer box is gone", not a.ui.entry_open)
ok("and the tidbit actually appears",
   "tidbit" in a.ui._msg or "잡지식" in a.ui._msg, repr(a.ui._msg[:60]))


print("\n--- a command with work still in flight ---")
a.start_quiz("another one", "answer")
a._look_pending = True
a._check_id = getattr(a, "_check_id", 0)
before = a._check_id
dropped = []
a.brain.cancel_pending = lambda: dropped.append(1) or 0

ran = []
a.command(lambda: ran.append("new"))()
ok("the new command ran", ran == ["new"])
ok("the question went with it", a.quiz is None and not a.ui.entry_open)
ok("the pending look is disowned", not a._look_pending)
ok("a scheduled capture is invalidated", a._check_id != before, str(a._check_id))
ok("and the API answer already on its way is thrown away", dropped, str(dropped))


print("\n--- the rate limiter cannot swallow the answer ---")
# Without the reset, a command issued seconds after he last spoke produced
# nothing at all: can_speak() refused and the caller returned quietly.
a.reset_neutral("setup")
a.say("something he said a moment ago")
recent = a.last_line_at
ok("he has just spoken", recent > 0 and not a.can_speak())
pick("fun tidbit", "잡지식")()
ok("the very next command still gets a word out",
   a.ui._msg.strip() and a.ui._msg != "something he said a moment ago",
   repr(a.ui._msg[:50]))


print("\n--- the double-click is a command too ---")
ok("it is wrapped, not raw", a.ui.on_double != a.check_screen)
a.start_quiz("open question", "answer")
a._look_pending = True
a.ui.on_double()
ok("double-clicking him drops the open question", a.quiz is None)
ok("and the look that was in flight", not a._look_pending)


print("\n--- and one command never runs twice ---")
# TrackPopupMenu with TPM_RETURNCMD hands back one id and posts nothing, so
# the old 'the dismiss click re-invokes the item' problem cannot arise. What
# has to hold is the simpler thing: asking twice does the thing twice.
count = []
twice = a.command(lambda: count.append(1))
twice()
twice()
ok("two asks, two runs", len(count) == 2, str(len(count)))


print("\n--- he is never left mute afterwards ---")
for label in ("fun tidbit", "잡지식", "briefing", "브리핑"):
    try:
        pick(label)()
    except AssertionError:
        continue
    time.sleep(0.01)
ok("still able to speak at the end of all that", a.can_speak(0) or a.ui.talking)

a.ui.root.destroy()
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
