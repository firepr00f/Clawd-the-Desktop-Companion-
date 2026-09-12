"""
The unprompted-speech scheduler, and the verdict that no longer accuses.

Two changes, tested together because they are the same complaint: he talked too
often, and half of what he told you off for was coursework.

    xvfb-run -a python tests/test_chatter.py
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatter import Chatter, key_for                    # noqa: E402
from core.classify import NEUTRAL, STRAY, STUDY, classify    # noqa: E402
from core.watcher import Activity                            # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


CFG = {"chatter": {"base_interval_sec": 300, "growth": 1.6, "cap_sec": 1800,
                   "jitter": 0.3, "window_memory_sec": 600,
                   "recent_lines_buffer": 20, "silence_after_input_sec": 30}}
WIN = ("chrome.exe", 111)
OTHER = ("code.exe", 222)
SCREEN = (0, 0, 2880, 1800)


def act(title="t", proc="chrome.exe", idle=90, rect=(100, 100, 900, 700)):
    return Activity(title=title, process=proc, idle_seconds=idle, rect=rect)


print("\n--- the gap grows, and is never the same twice ---")
random.seed(4)
c = Chatter(CFG)
mean = [sum(c.wait(n) for _ in range(400)) / 400 / 60 for n in range(6)]
ok("it starts at about five minutes", 4.6 < mean[0] < 5.4, f"{mean[0]:.1f} min")
ok("and every step is longer than the last",
   all(b > a for a, b in zip(mean, mean[1:-1])), str([round(m, 1) for m in mean]))
ok("until the cap holds it", abs(mean[4] - mean[5]) < 1.5,
   f"{mean[4]:.1f} then {mean[5]:.1f}")
draws = {round(c.wait(0), 3) for _ in range(8)}
ok("the same n draws a different gap each time", len(draws) == 8, str(len(draws)))
lo, hi = min(c.wait(0) for _ in range(300)), max(c.wait(0) for _ in range(300))
ok("jitter stays inside 0.7-1.3", lo >= 300 * 0.69 and hi <= 300 * 1.31,
   f"{lo:.0f}..{hi:.0f}s")


print("\n--- an hour on one window ---")
random.seed(11)
c = Chatter(CFG)
c.arrive(0.0, WIN)
now, said = 0.0, []
while now < 3600:
    now += 10
    if c.due(now):
        said.append(now / 60)
        c.spoke(now, "KEEP_STUDY")
ok("far fewer than the twelve a fixed five minutes gave", len(said) <= 6, str(len(said)))
ok("but he does not go silent either", len(said) >= 3, str(len(said)))
gaps = [round(b - a, 2) for a, b in zip(said, said[1:])]
ok("and no two gaps are the same", len(set(gaps)) == len(gaps), str(gaps))


print("\n--- alt-tabbing away and back ---")
c = Chatter(CFG)
c.arrive(0.0, WIN)
for i in range(3):
    c.spoke(3000.0 * (i + 1), "x")
before = c.count(WIN)
c.arrive(9100.0, OTHER)
c.arrive(9190.0, WIN)                      # back 90 seconds later
ok("a window you just left keeps its count", c.count(WIN) == before,
   f"{c.count(WIN)} vs {before}")
c.arrive(9200.0, OTHER)
c.arrive(9200.0 + 700, WIN)                # back after eleven minutes
ok("one you left long ago starts fresh", c.count(WIN) == 0, str(c.count(WIN)))
ok("and the window he is on now is never pruned out from under him",
   c.here == WIN and WIN in c._seen)


print("\n--- interest earns attention back ---")
c = Chatter(CFG)
c.arrive(0.0, WIN)
for i in range(4):
    c.spoke(float(i), "x")
ok("four lines in", c.count() == 4)
c.engaged(100.0)
ok("touching him steps the decay back by one", c.count() == 3, str(c.count()))
for _ in range(9):
    c.engaged(100.0)
ok("but it never goes below zero", c.count() == 0, str(c.count()))


print("\n--- the two mutes ---")
c = Chatter(CFG)
ok("not a word while you are still typing",
   c.muted(act(idle=3), SCREEN) == "mid-keystroke", repr(c.muted(act(idle=3), SCREEN)))
ok("fine once you have stopped", c.muted(act(idle=90), SCREEN) == "",
   repr(c.muted(act(idle=90), SCREEN)))
ok("nor into a full-screen window",
   c.muted(act(idle=90, rect=SCREEN), SCREEN) == "full screen")
ok("a maximised-but-bordered window still counts as full screen",
   c.muted(act(idle=90, rect=(1, 1, 2879, 1799)), SCREEN) == "full screen")


print("\n--- he does not repeat himself ---")
c = Chatter(CFG)
lines = [f"line {i}" for i in range(20)]
picked = [c.fresh(lines) for _ in range(20)]
ok("twenty lines, twenty different", len(set(picked)) == 20, str(len(set(picked))))
ok("and the twenty-first is allowed to reuse one", c.fresh(lines) in lines)
small = ["only one"]
ok("a pool of one still answers", c.fresh(small) == "only one")
ok("an empty pool answers with nothing", c.fresh([]) is None)


print("\n--- tier 1: unknown is not a crime ---")
FOCUS = {"focus": {"allowlist_mode": True}}


def verdict(title, proc):
    return classify(Activity(title=title, process=proc, idle_seconds=60,
                             rect=(0, 0, 900, 700)), FOCUS)


for title, proc in (("Draft1.asc - LTspice XVII", "ltspice.exe"),
                    ("MATLAB R2024b", "matlab.exe"),
                    ("user/clawd: a desktop pet - GitHub", "chrome.exe"),
                    ("opamp 반전 증폭기 - Google 검색", "chrome.exe"),
                    ("계산기", "calculator.exe")):
    v = verdict(title, proc)
    ok(f"{title[:34]:36} is left alone", v.state == NEUTRAL, f"{v.state} ({v.reason})")
    ok("   ...and marked for a second opinion", v.reason == "unknown", v.reason)

for title, proc in (("Shorts - YouTube", "chrome.exe"),
                    ("TikTok - Make Your Day", "chrome.exe"),
                    ("Steam", "steam.exe")):
    v = verdict(title, proc)
    ok(f"{title[:34]:36} still gets it", v.state == STRAY, f"{v.state} ({v.reason})")

for title, proc in (("KLAS - 광운대학교", "chrome.exe"),
                    ("LM358 datasheet.pdf", "chrome.exe")):
    v = verdict(title, proc)
    ok(f"{title[:34]:36} is still study", v.state == STUDY, f"{v.state} ({v.reason})")

v = verdict("전기공학 3강 - YouTube", "chrome.exe")
ok("a lecture on YouTube is not hated by name", not v.hated, v.hated)


print("\n--- the key is the window, and keeps nothing readable ---")
a1 = act(title="secret document.docx", proc="WINWORD.EXE")
a2 = act(title="secret document.docx", proc="winword.exe")
ok("same window, same key", key_for(a1) == key_for(a2))
ok("different title, different key", key_for(a1) != key_for(act(title="other")))
ok("the title is not kept in it",
   all("secret" not in str(part) for part in key_for(a1)), str(key_for(a1)))

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
