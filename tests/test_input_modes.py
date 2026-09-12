"""
The answer box must never be able to trap him.

`quiz` gates can_speak(), so any way of closing the box
that doesn't clear them leaves Clawd permanently mute and unable to change mode.

    xvfb-run -a python tests/test_input_modes.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import app as appmod, capture, watcher     # noqa: E402
from core.watcher import Activity                    # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


watcher.foreground = lambda: Activity(title="t", process="chrome.exe", rect=(0, 0, 900, 700))
capture.grab_jpeg_b64 = lambda *a, **k: None
capture.signature = lambda *a, **k: None
capture.available = lambda: False

# never let a test write over the real config.json / state.json — the menu
# actions below (teach, toggle_auto_look, quit) all persist by default
appmod._save_json = lambda *a, **k: None

a = appmod.App()
a.cfg["api"]["api_key"] = ""


def stuck() -> bool:
    """
    The symptom: a mode flag left set, so can_speak() is false forever.

    Clear the bubble and the rate limit first — being mid-sentence is a normal
    reason to be quiet, and it is not what we're testing.
    """
    a.ui.clear_msg()
    a.last_line_at = 0.0
    return not a.can_speak(0) or a.ui.entry_open


print("\n--- talking to him is gone entirely ---")
ok("no chat state on the app",
   not any(hasattr(a, n) for n in ("chat", "chat_open", "handle_chat")),
   str([n for n in ("chat", "chat_open", "handle_chat") if hasattr(a, n)]))
ok("and no way to ask for it", not hasattr(a.brain, "request_chat"))
ok("there is no single-click action left either", not hasattr(a, "on_click"))
bound = set(a.ui.cv.bind())
ok("the sprite answers to two gestures and no more",
   bound == {"<Button-1>", "<B1-Motion>", "<ButtonRelease-1>", "<Double-Button-1>"},
   str(sorted(bound)))
ok("no right-click on him at all",
   not any("Button-3" in b for b in bound), str(sorted(bound)))
ok("he is not left stuck by any of that", not stuck())

print("\n--- escape ---")
a.start_quiz("q?", "a")
ok("a quiz opens the box", a.ui.entry_open)
a.ui.cancel_entry()
ok("escape closes the box", not a.ui.entry_open)
ok("escape actually leaves quiz mode", a.quiz is None)
ok("and he can speak again", not stuck())

print("\n--- empty enter ---")
a.start_quiz("q?", "a")
a.ui.entry_var.set("   ")
a.ui._submit()
ok("an empty answer is treated as 'never mind'",
   a.quiz is None and not a.ui.entry_open)
ok("not left stuck", not stuck())

print("\n--- 'never mind' from the tray ---")
a.start_quiz("q?", "a")
ok("box is open", a.ui.entry_open)
item = dict((x[0], x[1]) for x in a.menu_spec() if x)
never = [v for k, v in item.items() if "never mind" in k or "됐어" in k]
ok("the menu offers a way out while a question is open", len(never) == 1,
   str(list(item)))
never[0]()
ok("and it closes the box", not a.ui.entry_open and a.quiz is None)
ok("not left stuck", not stuck())

print("\n--- quiz ---")
a.start_quiz("what is the time constant of an RC circuit?", "tau = RC")
ok("quiz opens the box", a.quiz is not None and a.ui.entry_open)
ok("he is deliberately quiet during a quiz", not a.can_speak(0))
a.ui.cancel_entry()
ok("escape drops the quiz", a.quiz is None and not a.ui.entry_open)
ok("and tells you the answer", "RC" in a.ui._msg, repr(a.ui._msg))
ok("not left stuck", not stuck())

print("\n--- the bubble timing out ---")
a.start_quiz("q?", "a")
t = time.time()
a.ui.say("q?", 0.01, t)
a.ui.render(0.07, t + 1.0, "quiz")
ok("an unanswered question expires cleanly",
   a.quiz is None and not a.ui.entry_open)
ok("silently — no skip line", not a.ui._msg, repr(a.ui._msg))
ok("not left stuck", not stuck())

print("\n--- switching mode straight from the menu ---")
for label, switch in (
    ("fun tidbit", lambda: a.fire_tidbit("")),
    ("check my screen", a.check_screen),
    ("language toggle", a.toggle_language),
):
    a.quiz = None
    a.start_quiz("stuck question?", "answer")
    a.cancel_input(silent=True)          # what every menu item now does first
    switch()
    ok(f"'{label}' works with a question open",
       a.quiz is None, f"quiz={a.quiz}")

a.cancel_input(silent=True)
ok("nothing left stuck at the end", not stuck())

print("\n--- answering a quiz still works ---")
a.start_quiz("what is tau in an RC circuit?", "tau = RC")
a.entry_answers = []
a.grade_answer = lambda text: a.entry_answers.append(text)
a.ui.entry_var.set("tau = RC")
a.ui._submit()
ok("a real answer is still delivered", a.entry_answers == ["tau = RC"],
   str(a.entry_answers))
ok("and closes the box", not a.ui.entry_open)

a.ui.root.destroy()
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
