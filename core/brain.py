"""
Where Clawd's lines come from.

Two sources:
  * offline  -- bank.py, always available, zero cost, zero network
  * api      -- Anthropic Messages API (stdlib urllib, no SDK dependency).
                Used for genuine commentary on what's on screen, quiz
                questions from your actual material, answer grading, and
                fresh tidbits.

API work always happens on a worker thread; results come back through a queue
that the Tk main loop drains, so the animation never stutters.
"""

from __future__ import annotations

import json
import os
import queue
import random
import threading
import urllib.error
import urllib.request
from collections import deque

from . import bank, lang, secrets

ENV_KEY = secrets.ENV_VAR

API_URL = "https://api.anthropic.com/v1/messages"

PERSONA = """You are Clawd, a small gremlin-ish study buddy that lives in the corner of \
a Korean electrical-engineering undergrad's screen and watches which window they have open.

Voice: lowercase, terse, very online, dry. Gen-Z-adjacent but not cringe — never explain \
a joke, never use hashtags, at most one emoticon like :( or :). One or two short sentences, \
under 25 words, no preamble, no quotation marks around your line.

You are dramatic and smug when they're slacking and quietly proud when they're not. The joke \
is always about the tab or the task, NEVER about them being lazy, stupid, or a failure. \
Never moralize, never write a paragraph, never give a pep-talk speech. If they've been \
off-task a long time, get gentler rather than harsher — assume stuck or tired, not lazy.

Output ONLY the line itself."""

# Appended to every prompt while the app is in Korean. Kept out of the system
# prompt so the JSON-shaped requests (topic, quiz, icon) keep their own systems.
KOREAN_RULE = (
    "\n\n한국어로 답해. 반말로, 짧고 건조하게. 존댓말이나 격식체는 쓰지 마. "
    "JSON을 요청받았다면 키 이름은 영어 그대로 두고 값만 한국어로 써."
)


class Brain:
    def __init__(self, cfg: dict, log=lambda *a: None, budget=None):
        self.cfg = cfg
        self.log = log
        self.budget = budget            # optional spending guard; see budget.py
        self._recent: deque[str] = deque(maxlen=14)
        self.results: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._inflight = 0
        self._epoch = 0             # bumped to disown in-flight requests
        self._lock = threading.Lock()
        self.last_error = ""        # newest API failure, in plain words

    # ---------------- offline ----------------

    def key(self) -> str:
        """
        The API key, from the first of these that has one:

          1. api.api_key in config.json     — explicit, but syncs to the cloud
          2. the ANTHROPIC_API_KEY env var  — best; nothing on disk here
          3. the key you typed into Clawd   — secrets.py, outside this folder

        Checked live on every call, so pasting a key into his dialog takes
        effect immediately without a restart.
        """
        k = (self.cfg.get("api", {}).get("api_key") or "").strip()
        if k:
            return k
        k = os.environ.get(ENV_KEY, "").strip()
        if k:
            return k
        return secrets.load()

    def key_source(self) -> str:
        """Which of the three the current key came from — for the menu."""
        if (self.cfg.get("api", {}).get("api_key") or "").strip():
            return "config.json"
        if os.environ.get(ENV_KEY, "").strip():
            return ENV_KEY
        if secrets.stored():
            return secrets.display_path()
        return ""

    @property
    def api_configured(self) -> bool:
        return bool(self.cfg.get("api", {}).get("enabled")) and bool(self.key())

    @property
    def api_on(self) -> bool:
        """Configured AND still inside the spending cap. Everything checks this."""
        if not self.api_configured:
            return False
        if self.budget is not None and self.budget.over():
            return False
        return True

    def line(self, pool, **fmt) -> str:
        """
        Pick a line from a bank pool, avoiding recent repeats, and format it.

        `pool` is normally a pool NAME, resolved in the current language at the
        moment of speaking — so switching 한/영 changes what he says next
        without restarting anything. A raw list still works, for pools that get
        combined on the fly (see App.flavour_pool).
        """
        if isinstance(pool, str):
            pool = bank.pool(pool, lang.code())
        if not pool:
            return ""
        options = [p for p in pool if p not in self._recent] or list(pool)
        pick = random.choice(options)
        self._recent.append(pick)
        try:
            return pick.format(**fmt)
        except (KeyError, IndexError):
            return pick

    def tidbit(self) -> str:
        return self.line("TIDBITS")

    def offline_quiz(self) -> tuple[str, str]:
        q, a = random.choice(bank.pool("QUIZ_OFFLINE", lang.code())
                             or bank.QUIZ_OFFLINE)
        return q, a

    # ---------------- api plumbing ----------------

    def _post(self, payload: dict, timeout: float = 40.0) -> dict | None:
        key = self.key()
        if not key:
            return None
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")[:400]
            except Exception:
                pass
            self.log(f"api http {e.code}: {body}")
            self.last_error = self._explain(e.code, body)
        except Exception as e:
            self.log(f"api error: {e}")
            self.last_error = "api call failed — check your internet, then the log"
        return None

    @staticmethod
    def _explain(code: int, body: str) -> str:
        """Turn an API failure into something worth putting in a speech bubble."""
        low = (body or "").lower()
        if "credit balance is too low" in low:
            return ("api key works, but the account has no credits.\n"
                    "console.anthropic.com → Plans & Billing → Buy credits")
        if code == 401 or "authentication" in low:
            return "api key rejected. check api_key in config.json"
        if code == 429 or "rate_limit" in low:
            return "rate limited. i'll back off for a bit"
        if code >= 500:
            return "anthropic's end is having a moment. staying offline for now"
        return f"api error {code} — see the log"

    def _text_of(self, resp: dict | None, trim: bool = True) -> str:
        if not resp:
            return ""
        parts = [b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text"]
        text = "".join(parts).strip().strip('"')
        return self.shorten(text) if trim else text

    def shorten(self, text: str) -> str:
        """
        A hard ceiling on any line he says.

        The prompts ask for one short sentence, but a model that runs long
        shouldn't be the reason a bubble loses its ending. Cut at the last
        sentence break under the cap — dropping a whole sentence reads far
        better than a word ending in "li…".
        """
        cap = int(self.cfg.get("api", {}).get("max_line_chars", 200))
        text = (text or "").strip()
        if cap <= 0 or len(text) <= cap:
            return text
        head = text[:cap]
        cut = max(head.rfind(". "), head.rfind("? "), head.rfind("! "),
                  head.rfind(".\n"), head.rfind("다. "), head.rfind("야. "))
        if cut > cap * 0.45:
            return head[:cut + 1].strip()
        return head.rsplit(" ", 1)[0].rstrip(" ,;:") + "…"

    def _ask(self, prompt: str, image_b64: str | None, model: str,
             max_tokens: int = 160, system: str = PERSONA,
             trim: bool = True) -> str:
        content: list[dict] = []
        if image_b64:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64},
            })
        if lang.code() == "ko":
            prompt += KOREAN_RULE
        content.append({"type": "text", "text": prompt})
        shot_note = f"screenshot {len(image_b64) * 3 // 4096}kB" if image_b64 else "text only"
        self.log(f"api -> {model} ({shot_note})")
        resp = self._post({
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": content}],
        })
        self._meter(model, resp)
        return self._text_of(resp, trim)

    def _meter(self, model: str, resp: dict | None):
        """Charge this call against the budget using the usage the API reports."""
        if self.budget is None or not resp:
            return
        u = resp.get("usage") or {}
        try:
            cost = self.budget.add(model,
                                   int(u.get("input_tokens", 0)),
                                   int(u.get("output_tokens", 0)))
            if self.budget.over() and not self.budget.tripped:
                self.budget.tripped = True
                self.results.put(("budget", self.budget.summary()))
            self.log(f"api {model} +${cost:.5f} ({self.budget.summary()})")
        except Exception as e:
            self.log(f"budget error: {e}")

    def cancel_pending(self) -> int:
        """
        Abandon everything currently in flight, plus anything already waiting in
        the queue. Returns how many results were dropped.

        The HTTP request itself is not aborted — urllib has no cancel, and the
        worker thread is already blocked on it — so the call still costs what it
        was going to cost. What this guarantees is that a stale answer can never
        arrive and overwrite whatever you asked for *after* it: click 'quiz me'
        and then 'fun tidbit', and the quiz that lands two seconds later is
        thrown away instead of hijacking the bubble.
        """
        with self._lock:
            self._epoch += 1
        dropped = 0
        while True:
            try:
                self.results.get_nowait()
                dropped += 1
            except Exception:
                break
        return dropped

    def _spawn(self, tag: str, fn, *args):
        """Run fn in a thread; push ('tag', result) onto self.results."""
        with self._lock:
            if self._inflight >= int(self.cfg.get("api", {}).get("max_concurrent", 2)):
                return False
            self._inflight += 1
            epoch = self._epoch

        def run():
            try:
                out = fn(*args)
            except Exception as e:
                self.log(f"brain thread error: {e}")
                out = None
            finally:
                with self._lock:
                    self._inflight -= 1
                    stale = epoch != self._epoch
            if out and not stale:
                self.results.put((tag, out))
            elif out:
                self.log(f"dropped a stale {tag} result")

        threading.Thread(target=run, daemon=True).start()
        return True

    # ---------------- api features ----------------

    def _fast_model(self) -> str:
        return self.cfg.get("api", {}).get("fast_model", "claude-haiku-4-5-20251001")

    def _smart_model(self) -> str:
        return self.cfg.get("api", {}).get("smart_model", "claude-sonnet-5")

    def request_study_comment(self, window_title: str, shot: str | None, context: str):
        """A remark about the material actually on screen."""
        prompt = (
            f"The student's active window is: {window_title!r}\n"
            f"{context}\n\n"
            + ("A screenshot of that window is attached — read it. " if shot else "")
            + "Say ONE line reacting to the specific material they're working on right "
            "now — name the actual concept you can see on the page. Be encouraging or "
            "wryly interested, not instructional."
        )
        return self._spawn("comment", self._ask, prompt, shot, self._fast_model(), 120)

    def request_stray_comment(self, window_title: str, minutes: int, tier: str,
                              context: str, shot: str | None = None):
        """A nag about the specific thing they wandered off to."""
        softness = {
            "nudge": "Mildly note it. Keep it light, almost amused.",
            "annoyed": "You're getting impatient now. Still funny.",
            "disappointed": "Theatrically disappointed. Comedic, not mean.",
            "concerned": "Drop the bit. Be warm and low-pressure — assume they're stuck or "
                         "tired. Offer the smallest possible next step.",
            "recheck": "You just looked at their screen AGAIN and they are still off-task. "
                       "React to what is on screen RIGHT NOW — if it's a different video or "
                       "page than before, say so. Find a new angle every time: amused, "
                       "exasperated, resigned, bargaining. Never repeat a line you'd have "
                       "used earlier.",
        }[tier]
        seeing = ("A screenshot of their window is attached — read it. Name the SPECIFIC "
                  "thing they are looking at: the actual video, the actual page, the "
                  "actual product. Saying 'a browser' or 'youtube' alone is a failure. "
                  "Do not describe the screen neutrally; react to it."
                  if shot else
                  "You only have the window title, not the screen.")
        prompt = (
            f"They have been off-task for {minutes} minutes. Window title: "
            f"{window_title!r}.\n{seeing}\n{context}\n\n{softness}\nOne line."
        )
        return self._spawn("comment", self._ask, prompt, shot, self._fast_model(), 140)

    def request_topic(self, window_title: str, shot: str | None):
        """Work out what they're actually looking at, for context and pixel items."""
        system = (
            "You identify what is on a student's screen. Reply with ONLY JSON: "
            '{"topic": "...", "detail": "...", "item": "..."} — `topic` is 2-5 words '
            "naming the subject (e.g. 'RC transient response', 'skibidi toilet compilation'), "
            "`detail` adds the chapter/section/range or channel if visible (else \"\"), "
            "`item` is one concrete noun that could be drawn as a tiny icon for this topic."
        )
        prompt = (f"Window title: {window_title!r}. What is this, specifically?"
                  if shot else
                  f"Window title: {window_title!r}. Infer the subject from the title alone.")
        return self._spawn("topic", self._json_call, prompt, shot,
                           self._fast_model(), 300, system, ("topic",))

    # -- the screen read -------------------------------------------------

    LOOK_RULES = (
        "A screenshot of the active window is attached. Name the CONTENT, not the "
        "app: 'a browser', 'Chrome', 'a PDF', 'YouTube' alone are wrong. Read the "
        "headline, tab, slide title, filename or equation. If it is genuinely "
        "unreadable set topic to \"unreadable\"; never guess."
    )

    LOOK_MODES = {
        "quiet":  "",
        "study":  "One line reacting to the specific material on screen — name the "
                  "concept you can see. Encouraging or wryly interested, never "
                  "instructional.",
        "stray":  "They just landed on this and it is not studying. One line about "
                  "THIS specific thing — the actual video, the actual page. Light and "
                  "amused, not a lecture.",
        "check":  "They double-clicked you to be checked on, and they are waiting "
                  "for this, so make it land.\n"
                  "NAME THE THING. Not 'a video', not 'that tab', not 'your "
                  "screen' — the actual title, channel, chapter, filename, "
                  "equation or product you can read in the picture. If the line "
                  "would still make sense in front of a different screen, it is "
                  "the wrong line.\n"
                  "Then react: studying, one dry compliment; straying, snark at "
                  "THE THING (never at them); unsure, ask them outright whether "
                  "this counts.\n"
                  "Under 18 words. No preamble, no 'i see', no 'looks like', no "
                  "restating the question.\n"
                  "Shape of it: 'lecture 7, slide 3. fine. carry on' — 'ok but "
                  "this is a 4 hour minecraft video' — 'a spreadsheet named "
                  "final_final2. studying or not, be honest'.",
    }

    # Only the check needs a verdict — it is what decides his face.
    VERDICT_RULE = (
        'verdict — exactly one of "study", "stray" or "unsure". "study" only for '
        "real coursework: lecture material, a textbook or paper, notes, problem "
        "sets, an assignment, a course site, writing or code for a class. "
        '"stray" for entertainment, social media, shopping, games, idle browsing. '
        '"unsure" when the screen is unreadable, blank, ambiguous, or could '
        "honestly be either — do not guess to avoid saying unsure."
    )

    def request_look(self, window_title: str, shot: str | None, context: str,
                     mode: str = "quiet"):
        """
        One call that does what request_topic + request_comment used to do in two:
        identify the screen AND (optionally) produce the line to say about it.

        Returns via the queue as ('look', {topic, detail, item, line}).
        """
        want_line = self.LOOK_MODES.get(mode, "")
        judging = mode == "check"
        system = (
            PERSONA + "\n\n" + self.LOOK_RULES + "\n\n"
            "Reply with ONLY a JSON object:\n"
            + ('{"topic": "...", "detail": "...", "item": "...", '
               '"verdict": "...", "line": "..."}\n' if judging else
               '{"topic": "...", "detail": "...", "item": "...", "line": "..."}\n')
            + "topic  — 2-5 words naming what is on screen\n"
              "detail — the chapter/section/channel/site if you can see it, else \"\"\n"
              "item   — one concrete noun that could be drawn as a tiny 8x8 icon\n"
            + (self.VERDICT_RULE + "\n" if judging else "")
            + ("line   — " + want_line
               + ("\nKeep every field short; the whole object under 60 words."
                  if judging else " Under 25 words, lowercase, in voice.")
               if want_line else 'line   — always exactly "" for this request')
        )
        prompt = (
            f"Window title: {window_title!r}\n{context}\n\n"
            + ("What is on this screen, specifically?" if shot else
               "No screenshot available — infer from the title alone, and set "
               "detail to \"\".")
        )
        # Always the fast model, even for the check. The judgement is easy —
        # is this coursework or not — and the double-click is a thing you stand
        # there waiting for, so latency matters more than cleverness. The smart
        # model was both slower and, at the old 200-token cap, prone to running
        # out mid-JSON, which parses as nothing and answers you with silence.
        return self._spawn("look", self._json_call, prompt, shot,
                           self._fast_model(),
                           int(self.cfg.get("api", {}).get("look_max_tokens", 400)),
                           system, ("topic",))

    def request_item(self, topic: str):
        """Ask for a 16x16 pixel icon for a topic the built-in set doesn't cover."""
        from .items import PALETTE_HELP
        system = (
            "You draw 16x16 pixel icons in the style of a 90s game item sprite. "
            'Reply with ONLY JSON: {"grid": [ ...exactly 16 strings of exactly 16 '
            "characters... ]}. Every row MUST be 16 characters long.\n"
            + PALETTE_HELP + "\n"
            "Rules that decide whether it is recognisable:\n"
            "- ONE object, centred, filling most of the 16x16 box. Not a scene.\n"
            "- Draw the most iconic silhouette of the thing — the shape someone "
            "would recognise as a black cutout.\n"
            "- Outline it in a colour that contrasts with the fill, and never build "
            "the whole icon out of black (1): it disappears against a dark desktop. "
            "Prefer D (light grey) or 2 (white) for structural lines.\n"
            "- Use 3-5 colours. Flat fills, no gradients, no dithering, no text, "
            "no letters or numbers.\n"
            "- Leave a 1-pixel transparent margin around the edge."
        )
        return self._spawn("item", self._item_call, f"Draw an icon for: {topic}", system,
                           topic)

    def request_tidbit(self, topic_hint: str = ""):
        """
        One piece of general trivia. Deliberately NOT about what they are
        studying: the point is a thirty-second break, and a fact about the
        thing they are already staring at is not a break from it.
        """
        prompt = (
            "Tell them one surprising, TRUE fact. Anything at all — history, "
            "animals, language, food, space, geography, the sea, a strange law, "
            "an odd invention. The kind of thing you would stop on while "
            "wandering Wikipedia.\n"
            "NOT about electronics, engineering, physics or their coursework. "
            "They are already looking at that; this is the break from it.\n"
            "Start with 'tidbit:'. Two short sentences at most, 30 words total, "
            "and it must fit in three lines of a small speech bubble.\n"
            "It must be accurate. If you are not certain of a detail, pick a "
            "different fact rather than hedging."
        )
        return self._spawn("tidbit", self._ask, prompt, None, self._fast_model(), 90)

    def request_quiz(self, window_title: str, shot: str | None):
        """Ask for a question about what's on screen. Returns JSON via the queue."""
        system = (
            "You write short study-check questions for an electrical engineering undergrad. "
            "Reply with ONLY a JSON object: "
            '{"question": "...", "answer": "...", "topic": "..."} '
            "The question must be answerable in one or two sentences from memory, and must come "
            "from the material visible on their screen. The answer is the ideal short answer.\n"
            "A screenshot of their window is attached — read it. Base the question on the "
            "actual content you can see (the equation, the slide, the paragraph), not on the "
            "name of the application."
        )
        prompt = (
            f"Active window: {window_title!r}. Write one question about the material on screen. "
            "If the screen has no usable study material, use the window title's topic instead."
        )
        return self._spawn("quiz", self._quiz_call, prompt, shot, system)

    def _json_call(self, prompt, shot, model, max_tokens, system, required=()):
        """
        Ask for JSON and hand back the parsed object, or None.

        trim=False is the whole point of this line. _ask normally runs its
        answer through shorten(), which is right for a line he *says* — it caps
        at api.max_line_chars and adds an ellipsis — and fatal for JSON: a
        200-character cap lands in the middle of a string, json.loads throws,
        this returns None, and _spawn queues nothing at all. That is what made
        the quiz never arrive (a question plus its answer has never once fitted
        in 200 characters) while the shorter look/grade replies squeaked under
        the cap and looked fine.
        """
        raw = self._ask(prompt, shot, model, max_tokens, system, trim=False)
        if not raw:
            return None
        try:
            start, end = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[start:end + 1])
        except Exception:
            return None
        if all(data.get(k) for k in required):
            return data
        return None

    def _quiz_call(self, prompt, shot, system):
        data = self._json_call(prompt, shot, self._smart_model(), 400, system,
                               ("question", "answer"))
        if data:
            return data
        # Never leave the intro line hanging. _spawn queues nothing when the
        # worker returns None, so an unusable answer used to mean "here comes a
        # question" and then nothing at all, forever, with no way to tell
        # whether it was still thinking. An offline question is a worse quiz
        # than a real one and an infinitely better outcome than silence.
        q, a = self.offline_quiz()
        self.log("quiz: no usable question from the api — using the offline bank")
        return {"question": q, "answer": a}

    def _item_call(self, prompt, system, topic):
        data = self._json_call(prompt, None, self._fast_model(), 1400, system, ("grid",))
        if not data:
            return None
        return {"topic": topic, "grid": data["grid"]}

    def request_grade(self, question: str, expected: str, given: str):
        system = (
            "You grade a student's one-line answer generously but honestly. Reply with ONLY JSON: "
            '{"correct": true|false, "line": "..."} '
            "where `line` is Clawd's reaction in his voice: lowercase, under 25 words, dry and "
            "warm. If wrong, the line must contain the actual correct answer, briefly. "
            "If partially right, say which part."
        )
        prompt = (
            f"Question: {question}\nIdeal answer: {expected}\nStudent answered: {given!r}"
        )
        return self._spawn("grade", self._grade_call, prompt, system)

    def _grade_call(self, prompt, system):
        return self._json_call(prompt, None, self._smart_model(), 300, system, ("line",))

    def store_key(self, key: str) -> tuple[bool, str]:
        """Save a key typed into Clawd. Takes effect on the next call."""
        ok, msg = secrets.save(key)
        if ok:
            self.last_error = ""
        return ok, msg

    def forget_key(self) -> bool:
        return secrets.clear()

    def test_key(self) -> tuple[bool, str]:
        """Synchronous one-shot check used by the 'test API key' menu item."""
        if not self.key():
            return False, "no api key yet — right-click me and pick 'set api key'"
        out = self._ask("say: ok", None, self._fast_model(), 20, "Reply with exactly: ok")
        return (True, "api key works") if out else (False, "api call failed — see clawd.log")
