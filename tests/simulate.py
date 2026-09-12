"""
Fast-forward demo. Runs the real Clawd with a fake watcher so you can watch the
whole escalation ladder in about a minute instead of half an hour.

    python tests/simulate.py

Timeline: studying -> praise -> wanders to YouTube brainrot -> the ladder ->
comes back to the PDF.  Nothing on your real screen is read.
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import watcher
from core.watcher import Activity

START = time.time()

# (seconds from start, window title, process)
SCRIPT = [
    (0,   "전자기학 lecture3.pdf - Adobe Acrobat Reader", "acrord32.exe"),
    (14,  "skibidi toilet ultimate compilation - YouTube", "chrome.exe"),
    (60,  "rizz tier list reaction - YouTube", "chrome.exe"),
    (95,  "전자기학 lecture3.pdf - Adobe Acrobat Reader", "acrord32.exe"),
]


def fake_foreground():
    t = time.time() - START
    title, proc = SCRIPT[0][1], SCRIPT[0][2]
    for at, ti, pr in SCRIPT:
        if t >= at:
            title, proc = ti, pr
    return Activity(title=title, process=proc, idle_seconds=0.0)


watcher.foreground = fake_foreground

from core.app import App  # noqa: E402

app = App()
app.cfg.update({
    "poll_seconds": 1,
    "min_seconds_between_lines": 6,
    "praise_every_minutes": 0.15,
    "break_after_minutes": 0,
    "quiz_every_minutes": 0,
    "stray": {"grace_minutes": 0.01, "annoyed_minutes": 0.02,
              "disappointed_minutes": 0.03, "concerned_minutes": 0.04},
})
app.can_speak = lambda gap=None: (        # type: ignore[assignment]
    not app.ui.talking and not app.quiz
    and time.time() - app.last_line_at >= 6
)
print(__doc__)
app.run()
