"""
한/영 switch.

Two halves live in different places on purpose:

  * Clawd's *lines* — the personality — are in bank.py, which has an EN list and
    a KO list per pool. Those are rewrites, not translations: same gremlin,
    speaking Korean.
  * The *interface* — menu labels, dialogs, status messages — is the table
    below, where a literal translation is exactly what you want.

Language is module state rather than a parameter threaded through everything:
this is a single-window desktop app with one user, and `set()` is called from
one place. Tests set it and set it back.
"""

from __future__ import annotations

DEFAULT = "en"
NAMES = {"en": "English", "ko": "한국어"}

_code = DEFAULT


def set(code: str) -> str:          # noqa: A001 - reads well at the call site
    global _code
    _code = code if code in NAMES else DEFAULT
    return _code


def code() -> str:
    return _code


def other() -> str:
    """The language the toggle would switch to."""
    return "ko" if _code == "en" else "en"


def t(key: str, **fmt) -> str:
    """A UI string in the current language, falling back to English."""
    row = STRINGS.get(key)
    if not row:
        return key
    s = row.get(_code) or row.get("en") or key
    try:
        return s.format(**fmt)
    except (KeyError, IndexError):
        return s


# ---------------------------------------------------------------------------
# key -> {"en": ..., "ko": ...}

STRINGS: dict[str, dict[str, str]] = {
    # ---- menu ----
    "tray.tip":         {"en": "Clawd — click for the menu",
                         "ko": "클로드 — 클릭하면 메뉴"},
    "menu.bring_back":  {"en": "bring Clawd back here", "ko": "클로드 여기로 불러오기"},
    "menu.quiz":        {"en": "quiz me", "ko": "퀴즈 내줘"},
    "menu.tidbit":      {"en": "fun tidbit", "ko": "잡지식 하나"},
    "menu.briefing":    {"en": "today's briefing", "ko": "오늘 브리핑"},
    "menu.fireworks":   {"en": "fireworks!", "ko": "불꽃놀이!"},
    "menu.edit_sched":  {"en": "edit schedule.json", "ko": "schedule.json 편집"},
    "menu.nevermind":   {"en": "never mind, drop the question",
                         "ko": "됐어, 질문 취소"},
    "menu.language":    {"en": "언어: 한국어로 바꾸기", "ko": "Language: switch to English"},
    "menu.set_key":     {"en": "set api key…", "ko": "api 키 입력…"},
    "menu.change_key":  {"en": "change api key…", "ko": "api 키 바꾸기…"},
    "menu.test_key":    {"en": "test api key", "ko": "api 키 테스트"},
    "menu.forget_key":  {"en": "forget my saved api key", "ko": "저장된 api 키 삭제"},
    "menu.spend":       {"en": "api spend so far", "ko": "지금까지 api 비용"},
    "menu.quit":        {"en": "quit", "ko": "종료"},

    # ---- looking at the screen ----
    "look.thinking":    {"en": "....", "ko": "...."},
    "look.no_capture":  {"en": "i can't screenshot anything — run:\npip install mss pillow",
                         "ko": "스크린샷을 아예 못 찍어 — 이거 실행해:\npip install mss pillow"},
    "look.empty":       {"en": "screenshot came back empty — see the log",
                         "ko": "스크린샷이 비어서 왔어 — 로그 봐"},
    "look.busy":        {"en": "i've got too much in flight — try again in a few seconds",
                         "ko": "지금 처리 중인 게 너무 많아 — 몇 초 뒤에 다시",
                         },
    "key.needed":       {"en": "i can't read your screen or set real quizzes without "
                               "an api key.\none sec — i'll ask for it",
                         "ko": "api 키가 없으면 화면도 못 보고 제대로 된 퀴즈도 못 내.\n"
                               "잠깐만 — 물어볼게"},
    "key.opening":      {"en": "i need an api key first — opening the box now",
                         "ko": "api 키부터 필요해 — 입력창 열게"},
    "key.title":        {"en": "Clawd — API key", "ko": "Clawd — API 키"},
    "key.blurb":        {"en": "Paste your Anthropic API key.\n\n"
                               "Get one at console.anthropic.com → API keys. "
                               "It starts with sk-ant-.\n\n"
                               "Saved to {path} — on this machine only, outside this "
                               "project folder, so it is not synced to the cloud with "
                               "the code. It is stored as plain text, so treat it like "
                               "a password on a shared PC.",
                         "ko": "Anthropic API 키를 붙여넣어.\n\n"
                               "console.anthropic.com → API keys 에서 발급받으면 돼. "
                               "sk-ant- 로 시작해.\n\n"
                               "{path} 에 저장돼 — 이 컴퓨터에만, 프로젝트 폴더 밖에 "
                               "저장되니까 코드랑 같이 클라우드로 동기화되지 않아. "
                               "평문으로 저장되니까 공용 PC에서는 비밀번호처럼 다뤄."},
    "key.also_env":     {"en": "also set ANTHROPIC_API_KEY so my other tools see it",
                         "ko": "다른 프로그램도 쓸 수 있게 ANTHROPIC_API_KEY 도 설정"},
    "key.show":         {"en": "show what I'm typing", "ko": "입력한 내용 보기"},
    "key.save":         {"en": "save", "ko": "저장"},
    "key.cancel":       {"en": "cancel", "ko": "취소"},
    "key.empty":        {"en": "nothing typed yet", "ko": "아직 아무것도 안 썼어"},
    "key.bad_shape":    {"en": "that doesn't look like an anthropic key — they start "
                               "with sk-ant- . try again from the menu",
                         "ko": "anthropic 키처럼 안 생겼는데 — sk-ant- 로 시작해야 해. "
                               "메뉴에서 다시 해봐"},
    "key.save_failed":  {"en": "couldn't save it: {why}", "ko": "저장 실패: {why}"},
    "key.testing":      {"en": "got it, testing…", "ko": "받았어, 테스트 중…"},
    "key.works":        {"en": "key works. i can read your screen now — "
                               "double-click me and i'll take a look{note}",
                         "ko": "키 작동함. 이제 화면 볼 수 있어 — "
                               "더블클릭하면 내가 한번 볼게{note}"},
    "key.saved_bad":    {"en": "saved, but the key didn't work:\n{why}{note}",
                         "ko": "저장은 됐는데 키가 작동 안 해:\n{why}{note}"},
    "key.env_note":     {"en": " (new programs only)", "ko": " (새로 실행하는 프로그램부터)"},
    "key.none_saved":   {"en": "i had nothing saved to forget",
                         "ko": "삭제할 저장된 키가 없었어"},
    "key.forgot_other": {"en": "forgot the key i had.\nstill finding one in {src}",
                         "ko": "저장한 키는 지웠어.\n근데 {src} 에서 하나 더 찾았어"},
    "key.forgot":       {"en": "forgotten. back to offline mode",
                         "ko": "지웠어. 다시 오프라인 모드"},
    "key.source":       {"en": "\n(reading it from {src})", "ko": "\n({src} 에서 읽는 중)"},

    # ---- misc ----
    "misc.no_spend":    {"en": "api mode is off — costing you nothing",
                         "ko": "api 모드 꺼져 있어 — 돈 하나도 안 나가"},
    "misc.checking":    {"en": "hm. checking…", "ko": "흠. 확인 중…"},
    "misc.budget_hit":  {"en": "that's my api budget for now — going offline.\n{spend}",
                         "ko": "api 예산 다 썼어 — 오프라인으로 갈게.\n{spend}"},
    "misc.lang_set":    {"en": "ok, English from now on", "ko": "알겠어, 이제 한국어로 할게"},
}
