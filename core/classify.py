"""
Decides whether what you're looking at is studying, straying, or neither.

Everything here is driven off the foreground window title + process name, which
on Windows already contains the browser tab title -- so "skibidi toilet ultimate
compilation - YouTube - Google Chrome" is fully visible without any screenshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

STUDY = "study"
STRAY = "stray"
NEUTRAL = "neutral"
IDLE = "idle"

# --- apps -------------------------------------------------------------------

STUDY_APPS = {
    "acrord32.exe", "acrobat.exe", "sumatrapdf.exe", "pdfxedit.exe", "foxitpdfreader.exe",
    "onenote.exe", "obsidian.exe", "notion.exe", "goodnotes.exe", "anki.exe",
    "winword.exe", "excel.exe", "powerpnt.exe", "hwp.exe", "hword.exe",
    "matlab.exe", "pycharm64.exe", "code.exe", "idea64.exe", "studio64.exe",
    "devenv.exe", "spyder.exe", "jupyter-notebook.exe", "rstudio.exe", "octave.exe",
    "ltspice.exe", "xvii.exe", "comsol.exe", "comsollauncher.exe",
    "altium.exe", "kicad.exe", "eeschema.exe", "pspice.exe", "multisim.exe",
    "arduino ide.exe", "arduino.exe", "texstudio.exe", "texworks.exe", "sumatra.exe",
    "wolfram.exe", "mathematica.exe", "geogebra.exe", "calc.exe", "calculator.exe",
    "cmd.exe", "powershell.exe", "windowsterminal.exe", "wt.exe",
}

STRAY_APPS = {
    "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe", "battle.net.exe",
    "leagueclient.exe", "league of legends.exe", "valorant.exe", "riotclientux.exe",
    "kakaotalk.exe", "line.exe", "telegram.exe", "whatsapp.exe",
    "spotify.exe", "netflix.exe", "vlc.exe", "potplayermini64.exe",
    "roblox.exe", "robloxplayerbeta.exe", "minecraft.exe", "javaw.exe",
}

# Discord/chat is ambiguous -- study group vs. yapping. Treated as neutral
# unless the title looks like a game or a meme channel.
AMBIGUOUS_APPS = {"discord.exe", "slack.exe", "zoom.exe", "teams.exe", "kakaotalk.exe"}

# --- title keywords ---------------------------------------------------------

STUDY_WORDS = [
    # generic academic
    "lecture", "lec ", "chapter", "ch.", "syllabus", "homework", "hw", "assignment",
    "problem set", "pset", "midterm", "final exam", "quiz", "solution", "textbook",
    "exercise", "tutorial", "seminar", "thesis", "paper", "journal", "ieee", "arxiv",
    "doi.org", "sciencedirect", "springer", "scholar", "researchgate",
    # EE / your major
    "circuit", "signal", "fourier", "laplace", "transistor", "mosfet", "bjt", "op-amp",
    "opamp", "electromagnet", "maxwell", "semiconductor", "diode", "impedance",
    "capacitor", "inductor", "kirchhoff", "thevenin", "norton", "bode", "nyquist",
    "convolution", "z-transform", "verilog", "vhdl", "fpga", "embedded", "microcontroller",
    "control system", "state space", "eigen", "matrix", "linear algebra", "calculus",
    "differential equation", "probability", "statistics", "thermodynamics", "photonics",
    "antenna", "transmission line", "power system", "motor", "rectifier", "amplifier",
    # korean
    "강의", "강의노트", "과제", "숙제", "시험", "중간고사", "기말", "문제풀이", "정리",
    "전자기", "회로", "신호", "제어", "반도체", "전력", "통신", "논문", "학회",
    # tools / platforms
    "overleaf", "colab", "jupyter", "wolframalpha", "geogebra", "desmos", "symbolab",
    "khan academy", "coursera", "edx", "mit ocw", "ocw.", "nptel",
    "e-class", "eclass", "lms", "blackboard", "canvas", "moodle", "webassign",
    "학습관리", "학사정보", "포털",
    ".pdf", ".tex", ".ipynb", ".m -", ".sch", ".asc",
]

STRAY_WORDS = [
    "youtube", "youtu.be", "netflix", "tiktok", "instagram", "twitch", "reddit",
    "twitter", " / x", "facebook", "pinterest", "9gag", "9animetv", "crunchyroll",
    "laftel", "wavve", "tving", "coupang play", "watcha", "disney+",
    "dcinside", "fmkorea", "에펨코리아", "인스티즈", "더쿠", "루리웹", "웃긴대학",
    "아프리카tv", "chzzk", "치지직", "steam", "nexon", "메이플", "롤", "옵치",
    "shopping", "musinsa", "무신사", "쿠팡", "aliexpress", "지그재그",
    "webtoon", "웹툰", "네이버 웹툰", "만화", "manga", "mangadex",
]

# The specific flavour of stray that deserves the "how old are you gang" treatment
BRAINROT_WORDS = [
    "skibidi", "gyatt", "rizz", "sigma male", "ohio", "fanum", "brainrot",
    "mewing", "npc stream", "sus imposter", "amogus", "grimace", "level 999",
    "tier list", "🤫🧏", "edit audio", "sped up", "slowed reverb",
    "tiktok compilation", "shorts", "reels", "minecraft parkour", "subway surfers",
    "mukbang", "asmr eating", "prank", "storytime",
]

# YouTube etc. that is actually studying
STUDY_ON_STRAY_SITE = [
    "lecture", "tutorial", "explained", "crash course", "3blue1brown", "organic chem",
    "mit ", "nptel", "professor", "khan", "circuit", "fourier", "electromagnetics",
    "signals and systems", "semiconductor", "toefl", "ielts", "강의", "인강",
    "개념", "문제풀이", "정석", "메가스터디", "ebs",
    "전자기학", "회로이론", "공업수학", "미적분", "선형대수", "일반물리",
    "신호및시스템", "전자회로", "제어공학", "논리회로", "자료구조",
]

# "3강", "12주차", "4차시" — Korean lecture numbering. Unambiguous enough to
# rescue a video title on its own, which a bare subject word is not.
_LECTURE_NO = re.compile(r"\d+\s*(강|주차|차시|교시)")

_word_re_cache: dict[str, re.Pattern] = {}


def _hit(blob: str, words: list[str]) -> str | None:
    for w in words:
        if w in blob:
            return w.strip()
    return None


def _looks_like_a_lecture(blob: str) -> str | None:
    """Study material that happens to be hosted somewhere he'd normally hate."""
    m = _LECTURE_NO.search(blob)
    return _hit(blob, STUDY_ON_STRAY_SITE) or (m.group(0) if m else None)


# Sites and apps he does not merely disapprove of — he reacts the moment one
# appears, by name, with no warm-up. Everything off the allowlist is already
# straying; these skip the polite tier and open at annoyed.
#
# keyword found in the title/process  ->  what he calls it out loud
HATED = {
    "youtube": "YouTube", "youtu.be": "YouTube", "유튜브": "YouTube",
    "steam": "Steam", "스팀": "Steam",
    "tiktok": "TikTok", "틱톡": "TikTok",
    "instagram": "Instagram", "인스타": "Instagram",
    "twitch": "Twitch", "트위치": "Twitch",
    "netflix": "Netflix", "넷플릭스": "Netflix",
    "리그 오브 레전드": "League", "league of legends": "League",
    "롤인벤": "League", "발로란트": "Valorant", "valorant": "Valorant",
    "메이플": "Maple", "battle.net": "Battle.net",
    "쿠팡": "Coupang", "무신사": "Musinsa", "coupang": "Coupang",
}

# process name -> what he calls it. A dict, not a set, because "leagueclient"
# is not what anyone calls League of Legends.
HATED_PROCESSES = {
    "steam.exe": "Steam", "steamwebhelper.exe": "Steam",
    "leagueclient.exe": "League", "leagueclientux.exe": "League",
    "riotclientux.exe": "Riot", "valorant.exe": "Valorant",
    "maplestory.exe": "Maple", "battle.net.exe": "Battle.net",
    "epicgameslauncher.exe": "Epic", "discord.exe": "",
}


def hated_name(blob: str, proc: str, focus: dict | None = None) -> str:
    """
    What he hates about this window, by name — or "" if nothing.

    `blob` is the lowercased title + process; `focus` is the focus config
    block. Your own additions in focus.hated / focus.hated_processes are
    matched too, and are reported under whatever you called them.
    """
    cfg = focus or {}
    for w in [str(x).lower() for x in cfg.get("hated", []) or []]:
        if w and w in blob:
            return w.title()
    for p in [str(x).lower() for x in cfg.get("hated_processes", []) or []]:
        if p and p == proc:
            return p.replace(".exe", "").title()
    if proc in HATED_PROCESSES:
        return HATED_PROCESSES[proc]
    for word, name in HATED.items():
        if word in blob:
            return name
    return ""


@dataclass
class Verdict:
    state: str
    reason: str = ""        # the keyword or app that decided it
    brainrot: bool = False
    label: str = ""         # short human label, e.g. "YouTube"
    hated: str = ""         # named on sight: he opens at annoyed, not at nudge

    @property
    def is_stray(self) -> bool:
        return self.state == STRAY

    @property
    def is_study(self) -> bool:
        return self.state == STUDY


# ---------------------------------------------------------------------------
# Allowlist mode: a short list of things that count as studying, and everything
# else is straying. The inverse of the keyword lists above, and much stricter —
# with this on, Excel, a terminal and your bank site are all "get back to work".

ALLOW_PROCESSES = {
    # the pdf readers
    "acrord32.exe", "acrobat.exe", "acrobatinfo.exe", "sumatrapdf.exe",
    "pdfxedit.exe", "foxitpdfreader.exe",
    # office: word and powerpoint
    "winword.exe", "powerpnt.exe", "hwp.exe", "hword.exe",
    # the claude desktop app
    "claude.exe", "claude desktop.exe",
}

# Words that mark a browser tab (or any window title) as study. KLAS is the
# Kwangwoon LMS at klas.kw.ac.kr; its login page is titled 광운대학교 로그인 페이지
# and the pages behind it carry the course or menu name, so match the school and
# the system rather than one exact title.
ALLOW_TITLE_WORDS = [
    "klas", "klas.kw.ac.kr", "kw.ac.kr", "광운대", "kwangwoon", "학습관리",
    "광운대학교 로그인", "이러닝", "e-learning", "강의자료실", "수업활동",
    "출석/성적", "과제제출", "강의계획서",
    "claude",                       # the Claude app / claude.ai
    ".pdf", ".docx", ".pptx", ".hwp",
]

# Windows that are neither study nor slacking — nagging about the desktop or
# about Clawd's own dialogs would be unbearable.
IGNORE_PROCESSES = {
    "explorer.exe", "searchhost.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "textinputhost.exe", "lockapp.exe",
    "applicationframehost.exe", "systemsettings.exe",
    "pythonw.exe", "python.exe", "py.exe", "pyw.exe",
}
IGNORE_TITLES = {
    "", "clawd", "clawd — api key", "clawd — api 키", "program manager",
    "windows 입력 환경", "search", "검색", "시작", "start",
}


def _allowlist_verdict(act, cfg: dict) -> Verdict:
    """STUDY only for the allowlisted apps and titles; everything else strays."""
    blob = act.blob
    proc = act.process.lower()
    title = (act.title or "").strip().lower()

    extra_apps = {s.lower() for s in cfg.get("allow_processes", []) or []}
    extra_words = [s.lower() for s in cfg.get("allow_title_words", []) or []]
    ignore_apps = {s.lower() for s in cfg.get("ignore_processes", []) or []}

    if proc in IGNORE_PROCESSES or proc in ignore_apps or title in IGNORE_TITLES:
        return Verdict(NEUTRAL, reason="ignored", label=act.short(38))

    # your own overrides still win, in both directions
    for w in [s.lower() for s in cfg.get("extra_stray_keywords", [])]:
        if w and w in blob:
            return Verdict(STRAY, reason=w, brainrot=bool(_hit(blob, BRAINROT_WORDS)),
                           label=act.short(38))

    if proc in ALLOW_PROCESSES or proc in extra_apps:
        return Verdict(STUDY, reason=proc, label=act.short(38))

    hit = _hit(blob, ALLOW_TITLE_WORDS) or _hit(blob, extra_words)
    if hit:
        return Verdict(STUDY, reason=hit, label=act.short(38))
    for w in [s.lower() for s in cfg.get("extra_study_keywords", [])]:
        if w and w in blob:
            return Verdict(STUDY, reason=w, label=act.short(38))

    # --- the blacklist: named on sight, and the only way to STRAY from here --
    #
    # A lecture that happens to live on YouTube is not something to be hated BY
    # NAME. Stray and hated are different things: one is where you are, the
    # other is what it is.
    hate = "" if _looks_like_a_lecture(blob) else hated_name(blob, proc, cfg)
    stray_hit = _hit(blob, STRAY_WORDS)
    if hate or (stray_hit and not _looks_like_a_lecture(blob)):
        return Verdict(
            STRAY,
            reason=stray_hit or proc or "blacklist",
            brainrot=bool(_hit(blob, BRAINROT_WORDS)),
            label=(hate or (stray_hit.title() if stray_hit else act.short(38))),
            hated=hate,
        )

    # --- everything else is UNKNOWN, and unknown is not a crime --------------
    #
    # This used to be the YouTube treatment: off the list, therefore straying.
    # For an electrical engineering student that is wrong about half the time —
    # LTspice, MATLAB, a datasheet PDF, a GitHub page and a plain Google search
    # are all off the list and all of them are work. Two or three false
    # accusations and the app gets closed, which costs more than every missed
    # real distraction put together.
    #
    # So he says nothing. `reason="unknown"` is deliberately distinct from a
    # confident neutral: it is the hook a local vision model can hang off later
    # to turn an unknown into a real verdict, for free and without the screen
    # leaving the machine.
    return Verdict(NEUTRAL, reason="unknown", label=act.short(38))


def allowlist_on(cfg: dict | None) -> bool:
    return bool((cfg or {}).get("focus", {}).get("allowlist_mode", False))


def classify(act, cfg: dict | None = None) -> Verdict:
    """Map an Activity onto STUDY / STRAY / NEUTRAL / IDLE."""
    cfg = cfg or {}
    blob = act.blob
    proc = act.process.lower()

    if not blob.strip(" :"):
        return Verdict(NEUTRAL)

    if act.idle_seconds >= float(cfg.get("idle_seconds", 180)):
        return Verdict(IDLE, reason="afk")

    if allowlist_on(cfg):
        focus = dict(cfg.get("focus", {}))
        focus.setdefault("extra_study_keywords", cfg.get("extra_study_keywords", []))
        focus.setdefault("extra_stray_keywords", cfg.get("extra_stray_keywords", []))
        return _allowlist_verdict(act, focus)

    # user overrides win over everything
    for w in [s.lower() for s in cfg.get("extra_study_keywords", [])]:
        if w and w in blob:
            return Verdict(STUDY, reason=w, label=act.short(38))
    for w in [s.lower() for s in cfg.get("extra_stray_keywords", [])]:
        if w and w in blob:
            return Verdict(STRAY, reason=w, label=act.short(38))

    if proc in STUDY_APPS:
        return Verdict(STUDY, reason=proc, label=act.short(38))

    if proc in STRAY_APPS and proc not in AMBIGUOUS_APPS:
        return Verdict(STRAY, reason=proc, label=proc.replace(".exe", ""))

    stray_hit = _hit(blob, STRAY_WORDS)
    study_hit = _hit(blob, STUDY_WORDS)

    focus_cfg = (cfg.get("focus", {}) or {})
    hate = hated_name(blob, proc, focus_cfg)
    if stray_hit or hate:
        # "Electromagnetics Lecture 3 - YouTube" is studying, not straying —
        # and if it is studying he does not hate it either.
        rescue = _looks_like_a_lecture(blob)
        if rescue or (study_hit and not _hit(blob, BRAINROT_WORDS)):
            return Verdict(STUDY, reason=rescue or study_hit, label=act.short(38))
        return Verdict(
            STRAY,
            reason=stray_hit or hate,
            brainrot=bool(_hit(blob, BRAINROT_WORDS)),
            label=hate or (stray_hit.title() if stray_hit else act.short(38)),
            hated=hate,
        )

    if study_hit:
        return Verdict(STUDY, reason=study_hit, label=act.short(38))

    if _hit(blob, BRAINROT_WORDS):
        return Verdict(STRAY, reason="brainrot", brainrot=True, label=act.short(38))

    return Verdict(NEUTRAL, label=act.short(38))
