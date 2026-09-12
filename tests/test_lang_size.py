"""
The 한/영 switch, the one fixed size, the idle rule, and the menu removals.

    xvfb-run -a python tests/test_lang_size.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import app as appmod, bank, capture, lang, watcher   # noqa: E402
from core.classify import IDLE                                 # noqa: E402
from core.watcher import Activity                              # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


watcher.foreground = lambda: Activity(title="t", process="chrome.exe", rect=(0, 0, 900, 700))
capture.available = lambda: False
capture.signature = lambda *a, **k: None
appmod._save_json = lambda *a, **k: None

print("\n--- the bank has both languages ---")
ok("every English pool has a Korean one", not bank.missing("ko"), str(bank.missing("ko")))
ok("no pool is empty",
   all(bank.pool(n, l) for n in bank.EN for l in ("en", "ko")))

hangul = lambda s: any("가" <= c <= "힣" for c in str(s))     # noqa: E731
not_ko = [n for n in bank.EN
          if n != "QUIZ_OFFLINE" and not all(hangul(x) for x in bank.pool(n, "ko"))]
ok("every Korean line is actually in Korean", not not_ko, str(not_ko))
ok("the Korean quiz bank is translated too",
   all(hangul(q) for q, _ in bank.pool("QUIZ_OFFLINE", "ko")))

en_ph = {n: {p.count("{") for p in bank.pool(n, "en")} for n in bank.EN if n != "QUIZ_OFFLINE"}
ko_ph = {n: {p.count("{") for p in bank.pool(n, "ko")} for n in bank.EN if n != "QUIZ_OFFLINE"}
bad_ph = [n for n in en_ph if not (ko_ph[n] & en_ph[n] or ko_ph[n] == {0} == en_ph[n])]
ok("placeholders survive translation", not bad_ph, str(bad_ph))

print("\n--- switching ---")
lang.set("en")
a = appmod.App()
en_line = a.brain.line("GREETING")
ok("starts in English", not hangul(en_line), repr(en_line))

a.toggle_language()
ok("toggle flips to Korean", lang.code() == "ko")
ok("and his next line is Korean", hangul(a.brain.line("GREETING")))
ok("the menu label flips too", "English" in lang.t("menu.language"),
   lang.t("menu.language"))
ok("a UI string is Korean", hangul(lang.t("menu.quiz")), lang.t("menu.quiz"))
ok("the offline quiz is Korean", hangul(a.brain.offline_quiz()[0]))
ok("he says so, in Korean", hangul(a.ui._msg), repr(a.ui._msg))

a.toggle_language()
ok("toggle flips back", lang.code() == "en")
ok("and back to English lines", not hangul(a.brain.line("GREETING")))

lang.set("ko")
ok("an unknown key falls back rather than crashing",
   lang.t("no.such.key") == "no.such.key")
lang.set("en")

print("\n--- one size, and no way to change it ---")
ok("no size cycling is left on the overlay",
   not any(hasattr(a.ui, n) for n in ("set_size", "next_size", "size")),
   str([n for n in ("set_size", "next_size", "size") if hasattr(a.ui, n)]))
ok("nor on the app", not hasattr(a, "cycle_size"))
ok("and config carries no size any more", "size" not in a.cfg.get("appearance", {}),
   str(a.cfg.get("appearance", {}).get("size")))

ok("he is laid out at the plain configured scale",
   a.ui.cell >= 3 and a.ui.font_size >= 7, f"cell={a.ui.cell} font={a.ui.font_size}")
ok("the sprite matches the overlay", a.ui.clawd.cell == a.ui.cell)
ok("and his origin does too",
   (a.ui.clawd.ox, a.ui.clawd.oy) == (a.ui.CLAWD_OX, a.ui.CLAWD_OY))
ok("motion has the right window shape",
   (a.motion.ww, a.motion.wh) == (a.ui.W, a.ui.H))

print("\n--- he holds up an item for what you're doing ---")
from core import items as I                                    # noqa: E402
from core.classify import NEUTRAL, STRAY, STUDY                # noqa: E402

ok("show_items ships on", a.items_on())
routes = [("skibidi toilet compilation - YouTube", "tv"),
          ("KLAS - 광운대학교", "laptop"),
          ("ch4 전자기학.pdf - Adobe Acrobat", "magnet"),
          ("Claude", "chat"),
          ("무신사 장바구니", "cart")]
for title, want in routes:
    a.ui.clawd.hold(None)
    a.show_item(title)
    ok(f"{title[:26]:28} -> {want}",
       a.ui.clawd.held == I.ITEMS[want],
       f"got {I.builtin_for(title)}")

a.state = IDLE
a.ui.clawd.hold(I.ITEMS["book"])
a.handle_idle(1000.0, 600.0)
ok("but nothing while you're away", a.ui.clawd.held is None)

a.cfg.setdefault("appearance", {})["show_items"] = False
a.show_item("skibidi toilet - YouTube")
ok("and the switch still turns them off", a.ui.clawd.held is None)
a.cfg["appearance"]["show_items"] = True

print("\n--- study is an allowlist now ---")
from core import classify as C                                 # noqa: E402
from core.watcher import Activity as _Act                       # noqa: E402

fcfg = {"focus": {"allowlist_mode": True}}
allowed = [("KLAS - 광운대학교", "chrome.exe"),
           ("광운대학교 로그인 페이지", "chrome.exe"),
           ("klas.kw.ac.kr/std/cmn/frame/Frame.do", "chrome.exe"),
           ("ch4 전자기학.pdf - Adobe Acrobat Reader", "acrord32.exe"),
           ("보고서.docx - Word", "winword.exe"),
           ("발표.pptx - PowerPoint", "powerpnt.exe"),
           ("Claude", "claude.exe")]
for title, proc in allowed:
    v = C.classify(_Act(title=title, process=proc), fcfg)
    ok(f"study: {title[:30]}", v.is_study, v.state)

# The blacklist: named things, and the only route to STRAY.
angry = [("skibidi toilet - YouTube", "chrome.exe"),
         ("무신사 - 장바구니", "chrome.exe"),
         ("Steam", "steam.exe")]
for title, proc in angry:
    v = C.classify(_Act(title=title, process=proc), fcfg)
    ok(f"stray: {title[:30]}", v.is_stray, v.state)

# Off the list is no longer an accusation. Excel and a terminal used to get
# the YouTube treatment here, which for an engineering student is wrong about
# half the time — and two false accusations is one uninstall.
for title, proc in (("Book1 - Excel", "excel.exe"),
                    ("명령 프롬프트", "cmd.exe"),
                    ("네이버", "chrome.exe")):
    v = C.classify(_Act(title=title, process=proc), fcfg)
    ok(f"unknown, not accused: {title[:22]}", v.state == C.NEUTRAL, v.state)
    ok("   ...and flagged for a second opinion", v.reason == "unknown", v.reason)

for title, proc in [("바탕 화면", "explorer.exe"), ("Clawd", "pythonw.exe")]:
    v = C.classify(_Act(title=title, process=proc), fcfg)
    ok(f"ignored: {title[:30]}", v.state == NEUTRAL, v.state)

v = C.classify(_Act(title="anything", process="notepad.exe", idle_seconds=9999), fcfg)
ok("idle still wins over the allowlist", v.state == IDLE, v.state)

ok("allowlist can be switched off", not C.allowlist_on({"focus": {"allowlist_mode": False}}))
old = C.classify(_Act(title="fourier transform lecture", process="chrome.exe"), {})
ok("and the old keyword mode still works", old.is_study, old.state)

fcfg2 = {"focus": {"allowlist_mode": True, "allow_title_words": ["notion"],
                   "allow_processes": ["obsidian.exe"]}}
ok("you can add your own allowed title word",
   C.classify(_Act(title="my notes - Notion", process="chrome.exe"), fcfg2).is_study)
ok("and your own allowed app",
   C.classify(_Act(title="vault", process="obsidian.exe"), fcfg2).is_study)

print("\n--- some things he hates on sight ---")
from core.classify import hated_name                            # noqa: E402

for title, proc, want in [("skibidi toilet - YouTube", "chrome.exe", "YouTube"),
                          ("Steam", "steam.exe", "Steam"),
                          ("아이유 라이브 - YouTube", "chrome.exe", "YouTube"),
                          ("무신사 장바구니", "chrome.exe", "Musinsa"),
                          ("TikTok", "chrome.exe", "TikTok"),
                          ("League of Legends", "leagueclient.exe", "League")]:
    v = C.classify(_Act(title=title, process=proc), fcfg)
    ok(f"hates {title[:24]:26} as {want}", v.hated == want, f"got {v.hated!r}")
    ok(f"  ...and still calls it straying ({want})", v.is_stray, v.state)

print("\n--- but straying and hating are different things ---")
for title in ("전자기학 3강 - YouTube", "회로이론 12주차 - YouTube",
              "Fourier transform lecture - YouTube"):
    v = C.classify(_Act(title=title, process="chrome.exe"), fcfg)
    ok(f"a lecture is not hated: {title[:24]}", not v.hated, repr(v.hated))
for title, proc in (("명령 프롬프트", "cmd.exe"), ("Book1 - Excel", "excel.exe")):
    v = C.classify(_Act(title=title, process=proc), fcfg)
    ok(f"nor is a plain off-list window: {title[:16]}",
       v.state == C.NEUTRAL and not v.hated, f"{v.state} {v.hated!r}")
for title, proc in (("KLAS - 광운대학교", "chrome.exe"), ("보고서.docx - Word", "winword.exe")):
    v = C.classify(_Act(title=title, process=proc), fcfg)
    ok(f"and studying is never hated: {title[:16]}", v.is_study and not v.hated)

print("\n--- you can add your own ---")
mine = {"focus": {"allowlist_mode": True, "hated": ["더쿠"],
                  "hated_processes": ["kakaotalk.exe"]}}
ok("your own hated word", C.classify(_Act(title="더쿠 게시판", process="chrome.exe"),
                                     mine).hated == "더쿠")
ok("your own hated app",
   bool(C.classify(_Act(title="채팅", process="kakaotalk.exe"), mine).hated))
ok("hated_name is a plain function too",
   hated_name("something - youtube", "chrome.exe", {}) == "YouTube")
ok("and finds nothing in an innocent window",
   not hated_name("klas - 광운대학교", "chrome.exe", {}))

print("\n--- he reacts to them at once, not after the grace period ---")
import time as _t2                                              # noqa: E402
SEEN = {"act": _Act(title="KLAS - 광운대학교", process="chrome.exe")}
watcher.foreground = lambda: SEEN["act"]
watcher.cursor_pos = lambda: (10, 10)


def run_until_he_speaks(title, proc, polls=40):
    a.reset_neutral("")
    a.stray_tier = 0
    a._verdict = a._settling = None
    a.state, a.state_since, a.last_line_at = STUDY, 500000.0, 0.0
    for step_i in range(2):
        SEEN["act"] = _Act(title="KLAS - 광운대학교", process="chrome.exe")
        a._mouse_moved = a._woke_at = 500000.0 + step_i * 5
        a.last_poll = 0.0
        appmod.time.time = lambda v=500000.0 + step_i * 5: v
        try:
            a.poll()
        finally:
            appmod.time.time = _t2.time
    a.ui.clear_msg()
    a.last_line_at = 0.0
    for i in range(1, polls):
        now = 500010.0 + i * 5
        SEEN["act"] = _Act(title=title, process=proc)
        a._mouse_moved = a._woke_at = now
        a.last_poll = 0.0
        appmod.time.time = lambda v=now: v
        try:
            a.poll()
        finally:
            appmod.time.time = _t2.time
        if a.ui._msg:
            return i * 5, a.ui._msg, a.stray_tier
    return None, "", a.stray_tier


secs, line, tier = run_until_he_speaks("skibidi toilet - YouTube", "chrome.exe")
ok("YouTube gets a word within seconds", secs is not None and secs <= 20, str(secs))
ok("and it names YouTube", "YouTube" in line, repr(line[:50]))
ok("opening at the annoyed tier, not the polite one", tier >= 2, str(tier))

secs2, line2, tier2 = run_until_he_speaks("Steam", "steam.exe")
ok("Steam too", secs2 is not None and secs2 <= 20 and "Steam" in line2,
   f"{secs2}s {line2[:40]!r}")

slow, line3, tier3 = run_until_he_speaks("명령 프롬프트", "cmd.exe")
ok("but an ordinary off-list window still gets its grace period",
   slow is None or slow > 60, str(slow))
ok("and starts gently when it does", tier3 <= 1, str(tier3))
a.reset_neutral("")

print("\n--- a short bubble stays next to him ---")
import time as _time                                            # noqa: E402
head = a.ui.tail_tip_x
for msg in ("....", "ok", "a much longer sentence that will wrap across "
                          "several lines inside the bubble " * 4):
    a.ui.say(msg, 30, _time.time())
    a.ui.render(0.07, _time.time(), "curious")
    boxes = [a.ui.cv.bbox(i) for i in a.ui._bubble_items if a.ui.cv.bbox(i)]
    left = min(b[0] for b in boxes)
    right = max(b[2] for b in boxes)
    bottom = max(b[3] for b in boxes)
    label = msg[:12]
    ok(f"{label!r}: tail reaches his head", left <= head <= right,
       f"bubble x {left}..{right}, head at {head}")
    ok(f"{label!r}: bubble sits just above him",
       0 < a.ui.CLAWD_OY - bottom < 3 * a.ui.cell,
       f"gap {a.ui.CLAWD_OY - bottom:.0f}px")
    ok(f"{label!r}: stays on the canvas", left >= 0 and right <= a.ui.W,
       f"{left}..{right} vs W={a.ui.W}")

print("\n--- the removed menu items are gone for good ---")
for name in ("pause", "unpause", "teach", "BAD_SIGNATURES"):
    ok(f"App.{name} no longer exists", not hasattr(a, name))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, "core", "app.py"), encoding="utf-8").read()
labels = open(os.path.join(ROOT, "core", "lang.py"), encoding="utf-8").read()
for gone in ("shush for", "come back", "this window is study",
             "this window is straying", "look at my screen", "auto-watch",
             "size: {cur}", "talk to me"):
    ok(f"no menu label {gone!r}", gone not in labels)
ok("the paused_until gate is gone too", "paused_until" not in src)
ok("and no background-look code path is left",
   "auto_look" not in src and "ScreenWatch" not in src)
ok("talking to him is gone from the app too",
   "chat_open" not in src and "request_chat" not in src)
ok("PAUSED/UNPAUSED pools dropped", "PAUSED" not in bank.EN and "UNPAUSED" not in bank.EN)

a.ui.root.destroy()
lang.set("en")
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
