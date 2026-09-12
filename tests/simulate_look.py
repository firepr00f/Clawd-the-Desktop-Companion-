"""
End-to-end dry run of the screen-reading path, with no network and no real
screen.

The contract this locks down: screenshots are MANUAL and there is no longer any
code path that could make them otherwise. Nothing captures the screen in the
background — not a JPEG, not even the local fingerprint — and one DOUBLE-CLICK
produces exactly one look and one reaction, with no delayed repeat.

Run:  xvfb-run -a python tests/simulate_look.py
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


# ---- stub out everything that touches the world ---------------------------

def act_of(title, proc="chrome.exe"):
    return Activity(title=title, process=proc, idle_seconds=0.0,
                    rect=(0, 0, 1920, 1080))


SCRIPT = {"act": act_of("Fourier series - YouTube - Google Chrome")}
watcher.foreground = lambda: SCRIPT["act"]

GRABS = {"jpeg": 0, "sig": 0}


def _grab(*a, **k):
    GRABS["jpeg"] += 1
    return "ZmFrZS1qcGVn"


def _sig(*a, **k):
    GRABS["sig"] += 1
    return tuple([8] * 144)


capture.grab_jpeg_b64 = _grab
capture.signature = _sig
capture.available = lambda: True

appmod._save_json = lambda *a, **k: None   # keep the real config.json untouched

CALLS = []

app = appmod.App()
app.cfg["api"]["api_key"] = "test-key"
app.cfg["api"]["hide_self_while_capturing"] = False
app.cfg["api"]["manual_delay_seconds"] = 0.4     # keep the test quick
app.budget.over = lambda: False


def fake_look(title, shot, context, mode="quiet"):
    CALLS.append({"title": title, "shot": bool(shot), "mode": mode})
    app.brain.results.put(("look", {
        "topic": "minecraft parkour compilation",
        "detail": "some channel",
        "item": "controller",
        "verdict": "stray",
        "line": "" if mode == "quiet" else "that's the third one in a row btw",
    }))
    return True


app.brain.request_look = fake_look


def step(t, act=None):
    if act:
        SCRIPT["act"] = act
    app.last_poll = 0.0
    _now = time.time
    time.time = lambda: t
    appmod.time.time = lambda: t
    try:
        app.poll()
        app.drain_brain()
    finally:
        time.time = _now
        appmod.time.time = _now


def settle(seconds):
    """Let Tk's `after` callbacks run for real."""
    end = time.time() + seconds
    while time.time() < end:
        app.ui.root.update()
        time.sleep(0.02)
    app.drain_brain()


print("\n--- background: he must never capture on his own ---")
ok("there is no background watcher left to switch on",
   not hasattr(app, "watch") and not hasattr(app, "toggle_auto_look"))
ok("and no auto_look settings to turn one on with",
   "auto_look" not in app.cfg, str(app.cfg.get("auto_look")))

T = 100000.0
titles = ["Fourier series - YouTube - Google Chrome",
          "minecraft parkour 10 hours - YouTube - Google Chrome",
          "pset3.pdf - Adobe Acrobat", "Untitled - Notepad"]
for i in range(24):
    step(T + i * 5, act_of(titles[i % len(titles)],
                           "notepad.exe" if i % 7 == 0 else "chrome.exe"))

ok("no screenshots taken in the background", GRABS["jpeg"] == 0, str(GRABS))
ok("not even a local fingerprint", GRABS["sig"] == 0, str(GRABS))
ok("no api calls made on its own", not CALLS, str(CALLS))
ok("he holds up an icon matching the window title",
   app.ui.clawd.held is not None)

print("\n--- one double-click, one look ---")
SCRIPT["act"] = act_of("minecraft parkour 10 hours - YouTube - Google Chrome")
app.last_line_at = 0.0
app.ui._double(None)                     # exactly what a double-click does
ok("he shows dots, not chatter, while looking",
   app.ui._msg.strip() == "....", repr(app.ui._msg))
ok("but hasn't captured yet", GRABS["jpeg"] == 0, str(GRABS))

settle(0.9)
ok("exactly one capture after the delay", GRABS["jpeg"] == 1, str(GRABS))
ok("exactly one api call", len(CALLS) == 1, str(CALLS))
ok("it asks for a verdict", CALLS and CALLS[0]["mode"] == "check")
ok("with a screenshot attached", CALLS and CALLS[0]["shot"])
ok("and it answers out loud", "third one in a row" in app.ui._msg, repr(app.ui._msg))
ok("what he saw is remembered",
   app.topic == "minecraft parkour compilation", app.topic)
ok("and the verdict shows on his face", app.mood == "annoyed", app.mood)

print("\n--- and then nothing, until the next click ---")
before = dict(GRABS)
for i in range(40):                      # 200 simulated seconds of polling
    step(T + 500 + i * 5)
settle(0.3)
ok("no repeat look", GRABS == before, f"{before} -> {GRABS}")
ok("no second api call", len(CALLS) == 1, str(len(CALLS)))

print("\n--- it reads whatever is in front WHEN it fires ---")
CALLS.clear()
app.ui.clear_msg()
app.last_line_at = 0.0
SCRIPT["act"] = act_of("Clawd", "pythonw.exe")     # his own window at click time
app.check_screen()
SCRIPT["act"] = act_of("ch4 electromagnetics.pdf - Adobe Acrobat", "acrord32.exe")
settle(0.9)
ok("the delay lets you switch to the window you meant",
   CALLS and "electromagnetics" in CALLS[0]["title"], str(CALLS))

print("\n--- the check always answers, even when the api does not ---")
CALLS.clear()
app.ui.clear_msg()
app.last_line_at = 0.0
app.brain.request_look = lambda *a, **k: (CALLS.append({"mode": "check"}), True)[1]
app.cfg["api"]["check_timeout_seconds"] = 0.4
app.ui._double(None)                     # a double-click that never comes back
settle(0.25)                             # before the watchdog is due
ok("he is showing dots while it is out", app.ui._msg.strip() == "....",
   repr(app.ui._msg))
settle(1.6)
ok("the watchdog answers from the title instead of going silent",
   app.ui._msg.strip() not in ("", "...."), repr(app.ui._msg[:50]))
ok("and it still gives him a face", app.mood in ("proud", "annoyed", "confused"),
   app.mood)
ok("it did not go quiet on its own", not app._look_pending)

# an answer that DOES land must stand the watchdog down, not be overwritten
CALLS.clear()
app.cfg["api"]["check_timeout_seconds"] = 0.4
app.brain.request_look = fake_look
app.last_line_at = 0.0
app.ui._double(None)
settle(1.6)
answered = app.ui._msg
settle(0.8)                              # past where the watchdog would have fired
ok("a real answer is not clobbered by the watchdog", app.ui._msg == answered,
   repr(app.ui._msg[:40]))
app.cfg["api"]["check_timeout_seconds"] = 18

print("\n--- with no api key ---")
app.cfg["api"]["api_key"] = ""
app.ui.clear_msg()
CALLS.clear()
before = dict(GRABS)
app.check_screen()
settle(0.9)
ok("he says why instead of going silent",
   "api key" in app.ui._msg.lower(), repr(app.ui._msg))
ok("and captures nothing", GRABS == before, f"{before} -> {GRABS}")

app.ui.root.destroy()
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
