"""Headless checks for the parts that don't need a screen."""
import os, sys, json, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.watcher import Activity
from core.classify import classify, STUDY, STRAY, NEUTRAL, IDLE
from core.brain import Brain
from core import bank

fails = []
def check(name, cond, extra=""):
    print(("  ok  " if cond else "  FAIL") + f"  {name}" + (f"   [{extra}]" if not cond and extra else ""))
    if not cond:
        fails.append(name)

def A(title, proc="chrome.exe", idle=0.0):
    return Activity(title=title, process=proc, idle_seconds=idle)

print("\n--- classifier ---")
cases = [
    ("skibidi toilet season 20 all episodes - YouTube", "chrome.exe", STRAY, True),
    ("MIT 6.002 Circuits Lecture 4 - YouTube", "chrome.exe", STUDY, False),
    ("전자기학 강의노트 ch3.pdf - Adobe Acrobat Reader", "acrord32.exe", STUDY, False),
    ("Instagram", "chrome.exe", STRAY, False),
    ("무신사 - 가을 신상", "chrome.exe", STRAY, False),
    ("League of Legends", "league of legends.exe", STRAY, False),
    ("hw3.tex - Overleaf, Online LaTeX Editor", "chrome.exe", STUDY, False),
    ("Untitled - Notepad", "notepad.exe", NEUTRAL, False),
    ("ltspice - opamp_test.asc", "ltspice.exe", STUDY, False),
    ("우리 학교 e-Class 로그인", "chrome.exe", STUDY, False),
    ("rizz tier list reaction 🤫🧏", "chrome.exe", STRAY, True),
]
for title, proc, want, want_rot in cases:
    v = classify(A(title, proc))
    check(f"{title[:44]:<46} -> {want}", v.state == want, f"got {v.state} ({v.reason})")
    if want_rot:
        check(f"    brainrot flag on {title[:28]}", v.brainrot, "not flagged")

v = classify(A("anything", "chrome.exe", idle=400))
check("idle detection", v.state == IDLE)
v = classify(A("Discord | #circuits-study", "discord.exe"))
check("discord not auto-stray", v.state != STRAY, f"got {v.state}")
v = classify(A("Cat videos", "chrome.exe"), {"extra_stray_keywords": ["cat videos"]})
check("user override -> stray", v.state == STRAY)
v = classify(A("YouTube - my prof's recording", "chrome.exe"), {"extra_study_keywords": ["my prof"]})
check("user override beats youtube", v.state == STUDY)

print("\n--- the schedule, and what he nags about ---")
import json as _json                                          # noqa: E402
import tempfile                                               # noqa: E402
from datetime import datetime, timedelta                      # noqa: E402

from core.scheduler import Schedule, humanize                 # noqa: E402

src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "core", "app.py"), encoding="utf-8").read()
check("the app is wired to it", "self.sched" in src and "humanize" in src)
check("the briefing is reachable", "def show_briefing" in src)
check("and deadlines are nagged about on their own", "def handle_schedule" in src)
for pool in ("DUE_TODAY", "DUE_SOON", "OVERDUE", "TODO_POKE", "CLASS_SOON"):
    check(f"{pool} pool exists in both languages",
          pool in bank.EN and pool in bank.KO)

# A calendar built around *now*, so the test says the same thing in any month.
_now = datetime.now()
_fixture = {
    "courses": [{"name": "회로이론", "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                 "start": f"{min(23, _now.hour + 1):02d}:00"}],
    "deadlines": [
        {"title": "online lecture", "due": f"{_now:%Y-%m-%d} 23:59"},
        {"title": "physics quiz", "due": f"{_now + timedelta(days=2):%Y-%m-%d} 10:00"},
        {"title": "lab report", "due": f"{_now - timedelta(days=1):%Y-%m-%d} 12:00"},
        {"title": "next month's thing", "due": f"{_now + timedelta(days=30):%Y-%m-%d}"},
        {"title": "already handed in", "due": f"{_now:%Y-%m-%d} 23:59", "done": True},
    ],
    "todos": [{"title": "email the prof"}, {"title": "done thing", "done": True}],
}
_fd, _path = tempfile.mkstemp(suffix=".json")
with os.fdopen(_fd, "w", encoding="utf-8") as _f:
    _json.dump(_fixture, _f, ensure_ascii=False)
sched = Schedule(_path)

titles = lambda rows: [r["title"] for r in rows]              # noqa: E731
check("due today is due today", titles(sched.due_today(_now)) == ["online lecture"],
      str(titles(sched.due_today(_now))))
check("yesterday is overdue", titles(sched.overdue(_now)) == ["lab report"],
      str(titles(sched.overdue(_now))))
check("two days out is 'soon'", titles(sched.due_within(3, _now)) == ["physics quiz"],
      str(titles(sched.due_within(3, _now))))
check("a month out is not", "next month's thing" not in titles(sched.due_within(3, _now)))
check("done deadlines are forgotten",
      "already handed in" not in titles(sched.deadlines(_now)))
check("done todos too", titles(sched.todos()) == ["email the prof"],
      str(titles(sched.todos())))

lines = sched.briefing(_now)
check("the briefing leads with what is late", any("OVERDUE" in l for l in lines), str(lines[:2]))
check("and names today's deadline", any("DUE TODAY" in l for l in lines))
check("and today's class", any("회로이론" in l for l in lines))
check("an empty calendar still says something", Schedule(os.devnull).briefing(_now))

check("humanize: days", humanize(timedelta(days=2, hours=3)) == "2 days")
check("humanize: hours", humanize(timedelta(hours=3, minutes=20)) == "3h 20m",
      humanize(timedelta(hours=3, minutes=20)))
check("humanize: never zero", humanize(timedelta(seconds=5)) == "1 min")
os.unlink(_path)

print("\n--- brain (offline) ---")
brain = Brain({"api": {"enabled": False, "api_key": ""}})
check("api off without key", not brain.api_on)
check("api off with enabled but no key", not Brain({"api": {"enabled": True, "api_key": ""}}).api_on)
check("api on with key", Brain({"api": {"enabled": True, "api_key": "sk-test"}}).api_on)
seen = {brain.line(bank.STRAY_ANNOYED, mins=7, what="YouTube") for _ in range(12)}
check("no-repeat rotation gives variety", len(seen) >= 5, f"{len(seen)} unique")
check("placeholders filled", all("{mins}" not in x for x in seen))
line = brain.line(bank.QUIZ_WRONG, answer="tau = RC")
check("quiz wrong includes answer", "tau = RC" in line, line)
q, a = brain.offline_quiz()
check("offline quiz returns pair", bool(q and a))

print("\n--- every bank line formats ---")
sample = dict(what="YouTube", mins=9, task="pset 1", due="3 days", course="회로이론",
              streak=120, hour="2", answer="because reasons")
bad = []
for name in dir(bank):
    if name.startswith("_") or name == "QUIZ_OFFLINE":
        continue
    val = getattr(bank, name)
    if isinstance(val, list) and val and isinstance(val[0], str):
        for line in val:
            try:
                line.format(**sample)
            except Exception as e:
                bad.append(f"{name}: {line!r} ({e})")
check("all bank lines format cleanly", not bad, "; ".join(bad[:3]))
total = sum(len(getattr(bank, n)) for n in dir(bank)
            if not n.startswith("_") and isinstance(getattr(bank, n), list) and n != "QUIZ_OFFLINE")
print(f"     {total} lines in the offline bank")

print("\n--- offline grading ---")
from core.app import App
g = App._offline_grade
check("accepts a good answer",
      g("τ = RC; response has covered about 63.2% of its final change",
        "it's RC and you get to 63.2 percent"))
check("rejects nonsense", not g("τ = RC; 63.2% of final change", "uhh purple monkey"))
check("rejects empty", not g("τ = RC", ""))

print("\n--- pixel items ---")
from core import items as I
bad = []
for nm, g in I.ITEMS.items():
    if len(g) != I.SIZE or any(len(r) != I.SIZE for r in g):
        sizes = sorted({len(r) for r in g})
        bad.append(f"{nm}: {len(g)} rows, widths {sizes}")
    for r in g:
        for c in r:
            if c != "." and c not in I.PALETTE:
                bad.append(f"{nm}: bad char {c!r}")
check(f"all {len(I.ITEMS)} icons are valid {I.SIZE}x{I.SIZE}", not bad, "; ".join(bad[:3]))

# an icon made only of black disappears against a dark desktop
washed = [nm for nm, g in I.ITEMS.items()
          if {c for r in g for c in r if c != "."} <= {"1"}]
check("no icon is a pure-black silhouette", not washed, str(washed))

routing = [("skibidi toilet compilation", "tv"), ("RC transient response", "capacitor"),
           ("League of Legends", "controller"), ("무신사 가을 신상", "cart"),
           ("푸리에 변환", "wave"), ("MOSFET small signal", "transistor"),
           ("전자기학 3장", "magnet"), ("pset 3 due", "pencil"),
           ("verilog testbench", "chip"), ("spotify playlist", "music"),
           ("깃허브 pull request", "code"), ("2026-09-10 마감", "deadline")]
for probe, want in routing:
    got = I.builtin_for(probe)
    check(f"{probe[:30]:<32} -> {want}", got == want, f"got {got}")
check("unknown topic falls back on stray", I.resolve("완전 처음 보는 것", None, "stray") is not None)
check("_valid rejects a bad grid", not I._valid(["short", "rows"]))
check("an old 8x8 cache entry still loads",
      I._valid(I.upscale(["........", ".111111.", ".122221.", ".122221.",
                          ".122221.", ".122221.", ".111111.", "........"])))

print("\n--- sprite animation ---")
from core import sprite as SP  # noqa: E402


class _Cv:
    def __init__(self): self.boxes = []
    def create_rectangle(self, x0, y0, x1, y1, fill="", outline=""):
        self.boxes.append((x0, y0, x1, y1, fill)); return len(self.boxes)
    def delete(self, _i): pass


_cv = _Cv()
_c = SP.Clawd(_cv, 0, 0, 10.0)

# the whole point of the art style: he only ever moves in whole pixels
fractional = []
for mood in SP.MOODS:
    for walking in (False, True):
        for facing in (-1, 1):
            _c.set_mood(mood); _c.walking = walking; _c._was_walking = walking
            _c.facing = facing
            for f in range(12):
                _c.frame = f
                dx, dy, al, ar, sq, legs = _c._pose()
                vals = [dx, dy, al, ar, sq] + [v for pair in legs for v in pair]
                if any(v != int(v) for v in vals):
                    fractional.append((mood, walking, f, vals))
check("every animation offset is a whole pixel", not fractional, str(fractional[:2]))

check("the walk cycle has 4 beats", len(SP.WALK) == 4)
check("every mood has an idle loop",
      all(m in SP.IDLE for m in SP.MOODS),
      str([m for m in SP.MOODS if m not in SP.IDLE]))
check("idle loops are longer than the old 2-frame bob",
      all(len(v) >= 4 for v in SP.IDLE.values()),
      str({k: len(v) for k, v in SP.IDLE.items() if len(v) < 4}))
check("walking runs at its own faster beat", SP.WALK_TEMPO < min(SP.TEMPO.values()))

# arms must stay welded to the body through squash and stretch
detached = []
for squash in (-1, 0, 1):
    body_x0 = SP.BODY[0] - squash
    body_x1 = body_x0 + SP.BODY[2] + 2 * squash
    if SP.ARM_L[0] - squash + SP.ARM_L[2] < body_x0:
        detached.append(("left", squash))
    if SP.ARM_R[0] + squash > body_x1:
        detached.append(("right", squash))
check("arms stay attached when he squashes or stretches", not detached, str(detached))

_c.walking = False
_c._was_walking = False
_c.set_mood("neutral")
_c.frame = 0
_cv.boxes.clear()
_c.draw()
check("he actually renders", len(_cv.boxes) >= 7, f"{len(_cv.boxes)} blocks")
_c.hold(I.ITEMS["book"])
_cv.boxes.clear()
_c.draw()
check("a held 16x16 icon renders at the same footprint as the old 8x8",
      max(b[2] for b in _cv.boxes) - min(b[0] for b in _cv.boxes)
      >= (SP.GRID_W + SP.ITEM_CELLS) * 10.0 - 1)

print("\n--- motion ---")
from core.motion import BLOCK, FOLLOW, HOME, PATROL, Motion
m = Motion({"motion": {"speed_px_per_sec": 900}}, (248, 212), (470, 330), (1920, 1080))
m.start_at(1440, 690)
m.set_mode(BLOCK, (100, 100, 1800, 1000))
for _ in range(200):
    p = m.update(0.07)
body = (p[0] + 248, p[1] + 212)
check("block puts him near screen centre", 700 < body[0] < 1100 and 400 < body[1] < 700, str(body))
m.set_mode(PATROL, (100, 100, 1800, 1000))
xs = {m.update(0.07)[0] for _ in range(600)}
check("patrol sweeps a wide range", max(xs) - min(xs) > 600, f"{min(xs)}..{max(xs)}")
check("patrol stays on screen", min(xs) >= -248 and max(xs) <= 1920 - 470 + 248)
m.set_mode(HOME)
for _ in range(400):
    p = m.update(0.07)
check("returns home exactly", p == (1440, 690), str(p))
m.set_mode(FOLLOW)
check("follow off-Windows falls back to home", m.update(0.07) == (1440, 690))

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}"))
sys.exit(1 if fails else 0)
