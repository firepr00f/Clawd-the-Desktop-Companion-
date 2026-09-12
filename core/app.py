"""
The brain stem: polls the watcher, runs the mood/nag state machine, moves him
around the screen, and drives the UI.
"""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime

from . import (bank, capture, dpi, fireworks, items, lang, secrets, single,
               tray, watcher)
from .lang import t
from .brain import Brain
from .budget import Budget
from .classify import IDLE, NEUTRAL, STRAY, STUDY, Verdict, classify
from .motion import BLOCK, FOLLOW, HOME, PATROL, Motion
from .chatter import Chatter, key_for
from .scheduler import Schedule, humanize
from . import screenwatch
from .ui import Overlay

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(HERE, "config.json")
SCHEDULE_PATH = os.path.join(HERE, "schedule.json")
SOUND_PATH = os.path.join(HERE, "assets", "firework_sound.mp3")
STATE_PATH = os.path.join(HERE, "state.json")
ITEMS_PATH = os.path.join(HERE, "items_cache.json")
SPEND_PATH = os.path.join(HERE, "spend.json")
LOG_PATH = os.path.join(HERE, "clawd.log")

FRAME_MS = 70          # ~14 fps


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class App:
    def __init__(self):
        self.cfg = _load_json(CONFIG_PATH, {})
        lang.set(self.cfg.get("language", lang.DEFAULT))
        self.budget = Budget(SPEND_PATH, self.cfg, self.log)
        self.brain = Brain(self.cfg, self.log, self.budget)
        self.item_cache = items.ItemCache(ITEMS_PATH, self.log)
        self.sched = Schedule(SCHEDULE_PATH, self.log)
        self.chatter = Chatter(self.cfg, self.log)
        self.fw = None                  # the full-screen show, once the UI exists
        # last time each schedule nag fired, so a deadline that is still a
        # deadline five minutes later does not get mentioned five times
        self.sched_marks: dict[str, float] = {}

        self.state = NEUTRAL
        self.state_since = time.time()
        self.prev_state = NEUTRAL
        self.mood = "neutral"
        self.mood_until = 0.0

        self.stray_tier = 0
        self.study_run = 0.0            # seconds of the current study streak
        self.praise_mark = 0
        self.last_line_at = 0.0
        self.last_api_comment = 0.0
        self.study_since_quiz = 0.0
        self.last_break = time.time()
        self.quiz: dict | None = None
        self.pending: tuple[float, list, dict, str] | None = None
        self.last_tick = time.time()
        self.last_poll = 0.0
        self.night_done = False

        # what he thinks you're looking at
        self.topic = ""
        self.topic_detail = ""
        self._topic_by_title: dict[str, str] = {}
        self._look_pending = False
        self._last_stray_look = 0.0
        self._last_auto_line = 0.0      # last time an auto-look spoke
        self.last_act = None            # last foreground window that wasn't Clawd
        self._shown_error = ""          # so one API problem is reported once, not forever
        self._key_box = None            # the api-key dialog, while it's open
        self._last_keep = 0.0           # last 5-minute check-in line
        self._mouse_at = None           # last cursor position we saw
        self._mouse_moved = time.time()
        self._woke_at = 0.0             # last fireworks
        self._settling = None           # a verdict waiting to prove itself
        self._verdict = None            # the last one that stuck
        self._pardoned: dict[str, float] = {}   # windows a look proved innocent

        st = _load_json(STATE_PATH, {})
        today = datetime.now().strftime("%Y-%m-%d")
        self.day = today
        self.study_today = float(st.get("study_seconds", 0)) if st.get("date") == today else 0.0

        self.motion = None          # Overlay may call back before it exists
        self.ui = Overlay(self.cfg, self.on_answer,
                          on_moved=self.on_moved, on_cancel=self.cancel_input,
                          on_double=self.command(self.check_screen),
                          on_resized=self.sync_motion_bounds)

        # The handle that is always there. Clawd has no title bar and no
        # taskbar button, so if he is behind a maximised window or on a
        # monitor you unplugged, the sprite is not clickable and the tray is
        # the only way left to reach him.
        self.tray = tray.Tray(log=self.log, build_menu=self.menu_spec)
        self.tray_on = self.tray.start()
        self.log(f"display: dpi_aware={dpi.active()} scale={dpi.scale():.2f} "
                 f"window={self.ui.W}x{self.ui.H} cell={self.ui.cell:.1f} "
                 f"font={self.ui.font_size} capture={capture.available()}")
        bounds = self.ui.screen_bounds()
        self.motion = Motion(self.cfg, (self.ui.CLAWD_OX, self.ui.CLAWD_OY),
                             (self.ui.W, self.ui.H),
                             (bounds[2] - bounds[0], bounds[3] - bounds[1]), self.log,
                             sprite_size=(self.ui.clawd.width_px,
                                          self.ui.clawd.height_px),
                             screen_rect=bounds)
        self.motion.start_at(self.ui.x, self.ui.y)
        self.log(f"desktop {bounds} | clawd at {self.ui.sprite_rect()}")

        self.fw = fireworks.Fireworks(self.ui.root, self.ui.screen_bounds(),
                                      self.ui.cell, self.log)

        self.ui.root.after(400, self.greet)
        self.ui.root.after(FRAME_MS, self.frame)

    # ------------------------------------------------------------------
    # utilities

    def log(self, msg: str):
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")
        except Exception:
            pass

    def tune(self, *path, default=None):
        node = self.cfg
        for p in path:
            if not isinstance(node, dict) or p not in node:
                return default
            node = node[p]
        return node

    def set_mood(self, mood: str, seconds: float = 10.0):
        self.mood = mood
        self.mood_until = time.time() + seconds

    def can_speak(self, gap: float | None = None) -> bool:
        now = time.time()
        if self.quiz:
            return False
        if self.ui.talking:
            return False
        gap = gap if gap is not None else float(self.tune("min_seconds_between_lines", default=50))
        return now - self.last_line_at >= gap

    def may_comment(self, gap: float) -> bool:
        """
        Like can_speak, but without the 'is he mid-sentence' test.

        An auto-look decides whether to ask for a line ~2s before the line
        arrives, so blocking on a bubble that is about to expire anyway would
        silently downgrade most page changes to a quiet look. The gap is longer
        than the longest bubble, so it already implies he has finished talking.
        """
        now = time.time()
        if self.quiz:
            return False
        return now - self.last_line_at >= gap

    def say(self, text: str, mood: str | None = None, seconds: float | None = None):
        now = time.time()
        self.ui.say(text, seconds, now)
        self.last_line_at = now
        if mood:
            self.set_mood(mood, (seconds or self.ui._read_time(text)) + 3)

    def speak_bank(self, pool, mood: str, **fmt):
        self.say(self.brain.line(pool, **fmt), mood)

    def speak_api_or_bank(self, requested: bool, pool, mood: str, **fmt):
        if requested:
            self.pending = (time.time() + float(self.tune("api", "wait_seconds", default=7)),
                            pool, fmt, mood)
            self.set_mood(mood, 12)
        else:
            self.speak_bank(pool, mood, **fmt)

    # ------------------------------------------------------------------
    # pixel items

    def items_on(self) -> bool:
        """Held icons are off by default now — appearance.show_items turns them
        back on. The 37-icon set and the generator are still there, just idle."""
        return bool(self.tune("appearance", "show_items", default=False))

    def show_item(self, text: str, seconds: float = 0.0):
        """Hold up an icon for `text`; generate one via the API if it's new."""
        if not self.items_on():
            self.ui.clawd.hold(None)
            return
        if not text:
            return
        grid = items.resolve(text, self.item_cache)
        if grid:
            self.ui.clawd.hold(grid, seconds)
            return
        if self.brain.api_on and self.tune("api", "generate_items", default=True):
            self.brain.request_item(text)
        fallback = items.resolve("", None, self.state)      # something in the meantime
        if fallback:
            self.ui.clawd.hold(fallback, seconds)

    # ------------------------------------------------------------------
    # lifecycle

    def greet(self):
        self.say(self.brain.line("GREETING"), "happy", 6)
        # ...then what today actually holds, once the hello has been read
        self.ui.root.after(6500, self.show_briefing)
        if self.needs_key():
            self.ui.root.after(3000, self.offer_key)

    # ---- api key -----------------------------------------------------

    def needs_key(self) -> bool:
        """API mode is switched on but there is no key anywhere to use."""
        return bool(self.tune("api", "enabled", default=False)) and not self.brain.key()

    def offer_key(self):
        """First run with no key: say so, then open the box."""
        self.say(t("key.needed"), "concerned", 7)
        self.ui.root.after(2200, self.ask_key)

    def ask_key(self):
        if self._key_box is not None:
            try:
                self._key_box.lift()
                return
            except Exception:
                self._key_box = None
        self._key_box = self.ui.ask_secret(
            t("key.title"), t("key.blurb", path=secrets.display_path()),
            extra_label=t("key.also_env"), on_done=self.save_key)
        if self._key_box is not None:
            self._key_box.bind("<Destroy>", lambda e: setattr(self, "_key_box", None))

    def save_key(self, key: str, also_env: bool):
        """Store what was typed, then actually try it."""
        if not secrets.looks_like_key(key):
            self.say(t("key.bad_shape"), "concerned", 12)
            return
        ok, where = self.brain.store_key(key)
        if not ok:
            self.say(t("key.save_failed", why=where), "concerned", 14)
            return

        note = ""
        if also_env:
            env_ok, env_msg = secrets.set_user_env(key)
            note = "\n" + env_msg + (t("key.env_note") if env_ok else "")

        self.log(f"api key saved to {where} ({secrets.redact(key)})")
        self.say(t("key.testing"), "curious", 8)
        self.ui.root.after(120, lambda: self._after_key_test(note))

    def _after_key_test(self, note: str):
        good, msg = self.brain.test_key()
        self._shown_error = self.brain.last_error      # don't re-announce it
        if good:
            self.say(t("key.works", note=note), "happy", 14)
        else:
            self.say(t("key.saved_bad", why=msg, note=note), "concerned", 18)

    def forget_key(self):
        had = secrets.stored()
        self.brain.forget_key()
        src = self.brain.key_source()
        if not had:
            self.say(t("key.none_saved"), "neutral", 8)
        elif src:
            self.say(t("key.forgot_other", src=src), "curious", 12)
        else:
            self.say(t("key.forgot"), "sleepy", 8)

    def frame(self):
        """
        One animation frame, then reschedule itself.

        A posted menu runs its own nested event loop, so these timers keep
        firing underneath it — and a frame that re-entered from in there used to
        queue a *second* frame chain, doubling the loop every time the menu was
        opened. The guard makes a re-entrant call do nothing and, above all,
        schedule nothing.
        """
        if getattr(self, "_in_frame", False):
            return
        self._in_frame = True
        try:
            self._frame()
        finally:
            self._in_frame = False
            # the reschedule lives in the finally: one bad frame must never be
            # able to stop the clock and leave him standing there dead
            self.ui.root.after(FRAME_MS, self.frame)

    def _frame(self):
        now = time.time()
        dt = min(0.4, now - self.last_tick)
        self.last_tick = now

        self.drain_brain()
        # the tray's message-only window belongs to this thread, so its clicks
        # arrive here, on the Tk thread, with nothing to marshal
        self.tray.pump()
        self.surface_api_error()

        if self.pending and now >= self.pending[0]:
            _, pool, fmt, mood = self.pending
            self.pending = None
            self.speak_bank(pool, mood, **fmt)

        if now > self.mood_until and not self.ui.talking:
            self.mood = {STUDY: "focus", STRAY: "annoyed",
                         IDLE: "sleepy"}.get(self.state, "neutral")
            if self.state == STUDY and self.study_run > 2400:
                self.mood = "proud"

        if now - self.last_poll >= float(self.tune("poll_seconds", default=5)):
            self.last_poll = now
            try:
                self.poll()
            except Exception as e:
                self.log(f"poll error: {e!r}")

        # "off in every situation" means every situation: rather than trusting
        # each caller to check, the held icon is cleared once per frame while
        # items are off, so nothing anywhere can leave one on screen.
        if not self.items_on() and self.ui.clawd.held is not None:
            self.ui.clawd.hold(None)

        # walk him wherever he's supposed to be — but hold still while a popup
        # is up, because moving the window closes the popup (Overlay._open_menu)
        if not self.ui._drag:
            x, y = self.motion.update(dt)
            if (x, y) != (self.ui.x, self.ui.y):
                self.ui.clawd.set_facing(x - self.ui.x)
                self.ui.place(x, y)
            # last line of defence: if he is somehow not visible, bring him back
            if not self.ui.on_screen():
                self._lost = getattr(self, "_lost", 0) + 1
                if self._lost > 6:
                    self._lost = 0
                    self.rescue("walked off screen")
            else:
                self._lost = 0
        self.ui.clawd.walking = self.motion.walking

        # While a popup is up he gives up always-on-top, which is what stops
        # him covering the menu. He does NOT stop repainting: a window that is
        # no longer topmost cannot composite over a menu that is, so the
        # repaint was never the problem — and skipping it meant the speech
        # bubble stopped being drawn, which made a double-click look like it
        # did nothing at all for as long as the freeze lasted.
        # menu_is_up() is latched and puts topmost back itself when the menu
        # ends, so nothing here toggles anything per frame. He keeps drawing
        # throughout: a window that is not topmost cannot cover a menu that is.
        self.ui.render(dt, now, self.mood)

    def surface_api_error(self):
        """Say an API problem out loud once instead of silently going offline."""
        err = self.brain.last_error
        if err and err != self._shown_error and self.can_speak(0):
            self._shown_error = err
            self.say(err, "concerned", 18)

    def drain_brain(self):
        while True:
            try:
                tag, payload = self.brain.results.get_nowait()
            except Exception:
                return
            if tag in ("comment", "tidbit") and isinstance(payload, str):
                mood = self.pending[3] if self.pending else "neutral"
                self.pending = None
                self.say(payload.strip(), mood)
            elif tag == "budget" and isinstance(payload, str):
                self.say(t("misc.budget_hit", spend=payload), "sleepy", 14)
            elif tag == "look" and isinstance(payload, dict):
                self.apply_look(payload)
            elif tag == "item" and isinstance(payload, dict):
                stored = self.item_cache.put(payload["topic"], payload["grid"])
                if stored and self.items_on():
                    self.ui.clawd.hold(payload["grid"])
            elif tag == "quiz" and isinstance(payload, dict):
                self.start_quiz(payload["question"], payload["answer"])
            elif tag == "grade" and isinstance(payload, dict):
                self.say(payload["line"], "happy" if payload.get("correct") else "curious")

    UNREADABLE = {"unreadable", "unknown", "", "n/a", "a browser", "browser"}

    def apply_look(self, data: dict):
        """A screen read came back: update what he thinks you're doing, and talk."""
        self._look_pending = False
        self._check_id = getattr(self, "_check_id", 0) + 1     # stand the watchdog down
        mode = getattr(self, "_look_mode", "quiet")

        topic = str(data.get("topic", "")).strip()[:80]
        readable = topic.lower() not in self.UNREADABLE
        if readable:
            self.topic = topic
            self.topic_detail = str(data.get("detail", "")).strip()[:80]
            if self.last_act:
                self._topic_by_title[self.last_act.short(90)] = topic
            if self.tune("privacy", "log_screen_details", default=False):
                self.log(f"screen: {topic}"
                         + (f" ({self.topic_detail})" if self.topic_detail else ""))
            else:
                self.log("screen: read ok")
        else:
            self.log("screen: unreadable")

        self.show_item(str(data.get("item") or self.topic))

        line = str(data.get("line", "")).strip()
        if mode == "check":
            # He judged it himself from the picture, which sees far more than a
            # window title does — an unreadable or genuinely ambiguous screen is
            # allowed to answer "unsure" rather than being forced into one.
            verdict = str(data.get("verdict", "")).strip().lower()
            if not readable or verdict not in self.CHECK_REACTION:
                verdict = "unsure"
            self.pending = None
            self.react_to_check(verdict, line)
            return
        if mode == "quiet":
            return
        if line:
            self.pending = None
            self.say(line, {"stray": "annoyed"}.get(mode, "curious"))
            self._last_auto_line = time.time()

    # ------------------------------------------------------------------
    # the actual watching

    def poll(self):
        now = time.time()
        self.roll_day()

        act = watcher.foreground()
        if watcher.is_own_window(act, {"Clawd"}):
            return
        self.last_act = act              # the last real window, for teach()
        v = self.settled_verdict(now, act)

        if v.state != self.state:
            self.prev_state, self.state = self.state, v.state
            self.state_since = now
            self.topic = self.topic_detail = ""
            if v.state == STUDY:
                self.on_enter_study(v, act)
            elif v.state == STRAY:
                self.stray_tier = 0
                self._last_stray_look = now
        elapsed = now - self.state_since

        # the only thing that ever reads the title is the item he holds up —
        # no capture, no API call, nothing leaves the machine
        self.show_item_for(act)

        step = float(self.tune("poll_seconds", default=5))
        if self.state == STUDY:
            self.study_run += step
            self.study_today += step
            self.study_since_quiz += step
            self.handle_study(now, elapsed, act)
        elif self.state == STRAY:
            self.handle_stray(now, elapsed, v, act)
        elif self.state == IDLE:
            self.handle_idle(now, elapsed)
        else:
            self.study_run = max(0.0, self.study_run - 2)

        self.drive_motion(now, elapsed, act)
        self.handle_mouse(now)
        self.handle_keep(now, act, v)
        self.handle_night(now)
        self.handle_schedule(now)

    def settled_verdict(self, now, act):
        """
        Classify the foreground window, but only *act* on a change once it has
        held still for `window_settle_seconds`.

        A page mid-load is a different window than the page it becomes. The KLAS
        lecture viewer spends its first moment as a blank or placeholder title,
        and reacting to that instantly is why an online lecture got interrupted
        before it had even finished opening. The same guard covers alt-tabbing
        through windows and a browser between tabs.
        """
        raw = classify(act, self.cfg)
        # `unknown` joins `stray` here now. Tier 1 stopped calling every
        # off-list window straying, so a window you pardoned by looking at it
        # comes back as unknown rather than stray — and without this the pardon
        # would quietly stop applying to exactly the windows it was made for.
        if (raw.is_stray or raw.reason == "unknown") and self.is_pardoned(act):
            # You double-clicked him on this exact window and he looked at it
            # properly and admitted it was coursework. The title still says
            # YouTube, so the keyword rules will keep saying stray forever —
            # but he has seen it. The pardon overrules them until it expires.
            raw = Verdict(STUDY, reason="pardoned", label=raw.label)
        if self._verdict is None:
            self._verdict = raw
            return raw
        if raw.state == self.state:
            self._settling = None
            self._verdict = raw
            return raw

        settle = float(self.tune("window_settle_seconds", default=2.0))
        key = (raw.state, screenwatch.normalise(act.short(120)))
        if self._settling and self._settling[0] == key:
            if now - self._settling[1] >= settle:
                self._settling = None
                self._verdict = raw
                return raw
        else:
            self._settling = (key, now)
        return self._verdict          # hold the previous verdict for now

    def drive_motion(self, now, elapsed, act):
        """How much he physically gets in your way."""
        if not self.tune("motion", "enabled", default=True):
            return
        if self.quiz:
            self.motion.set_mode(HOME)
            return
        if self.state != STRAY:
            self.motion.set_mode(HOME)
            return

        rect = act.rect
        follow_after = float(self.tune("motion", "follow_after_seconds", default=8))
        block_tier = int(self.tune("motion", "block_at_tier", default=1))
        patrol_tier = int(self.tune("motion", "patrol_at_tier", default=2))

        if self.stray_tier >= patrol_tier:
            self.motion.set_mode(PATROL, rect)
        elif self.stray_tier >= block_tier:
            self.motion.set_mode(BLOCK, rect)
        elif elapsed >= follow_after:
            self.motion.set_mode(FOLLOW, rect)
        else:
            self.motion.set_mode(HOME)

    def roll_day(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.day:
            _save_json(STATE_PATH, {"date": self.day,
                                    "study_seconds": round(self.study_today)})
            self.day, self.study_today = today, 0.0
            self.night_done = False
        _save_json(STATE_PATH, {"date": self.day, "study_seconds": round(self.study_today)})

    # ---- study ----

    def on_enter_study(self, v, act):
        came_back = self.prev_state == STRAY and self.stray_tier >= 2
        self.study_run = 0.0
        self.praise_mark = 0
        self.ui.clawd.hold(None)
        if came_back and self.can_speak(20):
            mins = int((time.time() - self.state_since) // 60)
            self.speak_bank("RETURN_TO_STUDY", "happy", mins=max(1, mins))
        elif self.can_speak(120):
            self.speak_bank("STUDY_START", "focus", what=act.short(40))
        self.stray_tier = 0

    def handle_study(self, now, elapsed, act):
        mins = int(self.study_run // 60)
        step = int(self.tune("praise_every_minutes", default=20))
        if step and mins >= step and mins // step > self.praise_mark and self.can_speak(90):
            self.praise_mark = mins // step
            pool = "STUDY_DEEP" if mins >= 45 else "STUDY_PRAISE"
            self.speak_bank(pool, "proud" if mins >= 45 else "happy", mins=mins)
            self.show_item("praise", 12)
            if random.random() < float(self.tune("tidbit_chance", default=0.45)):
                self.ui.root.after(9000, self.fire_tidbit,
                                   self.topic or act.short(50), False)
            return

        brk = int(self.tune("break_after_minutes", default=50)) * 60
        if brk and now - self.last_break > brk and self.can_speak(90):
            self.last_break = now
            self.speak_bank("BREAK_SUGGEST", "curious", mins=int(brk // 60))
            self.show_item("break", 12)
            return

        gap = float(self.tune("api", "study_comment_minutes", default=12)) * 60
        if (self.brain.api_on and self.study_run > 180
                and now - self.last_api_comment > gap and self.can_speak(120)):
            self.last_api_comment = now
            shot = self.shot_of(act, studying=True)
            ok = self.brain.request_study_comment(act.short(90), shot, self.context_line())
            self.speak_api_or_bank(ok, "STUDY_PRAISE", "curious", mins=max(1, mins))
            return

        qmin = float(self.tune("quiz_every_minutes", default=25)) * 60
        if qmin and self.study_since_quiz >= qmin and self.can_speak(120):
            self.study_since_quiz = 0.0
            self.begin_quiz(act)

    def fire_tidbit(self, hint: str, force: bool = True):
        """`force` is the default because the only caller that isn't you asking
        directly is the study-streak follow-up, which passes force=False."""
        if not force and not self.can_speak(5):
            return
        if self.brain.api_on and self.brain.request_tidbit(hint):
            self.pending = (time.time() + 7, "TIDBITS", {}, "curious")
            self.set_mood("curious", 10)
        else:
            self.say(self.brain.tidbit(), "curious")
        self.show_item("idea", 12)

    # ---- stray ----

    def handle_stray(self, now, elapsed, v, act):
        mins = int(elapsed // 60)
        t = self.tune("stray", default={}) or {}
        tiers = [
            (float(t.get("grace_minutes", 2)), 1, "STRAY_NUDGE", "curious", "nudge"),
            (float(t.get("annoyed_minutes", 5)), 2, "STRAY_ANNOYED", "annoyed", "annoyed"),
            (float(t.get("disappointed_minutes", 12)), 3, "STRAY_DISAPPOINTED",
             "disappointed", "disappointed"),
            (float(t.get("concerned_minutes", 25)), 4, "STRAY_CONCERNED",
             "concerned", "concerned"),
        ]

        # Some things he does not warm up to. YouTube, Steam and the rest of
        # focus.hated get named the moment the window settles and skip straight
        # to the annoyed tier — which also puts him in your way, because
        # motion.block_at_tier is 1. Everything else keeps its grace period.
        if v.hated and self.stray_tier < 2:
            wait = float(t.get("hated_seconds", 0))
            if elapsed >= wait and self.can_speak(20):
                self.stray_tier = 2
                self.speak_bank("HATED_OPEN", "annoyed", what=v.hated)
                self.show_item(self.topic or v.hated)
                self.log(f"hated: {v.hated}")
                return

        if v.brainrot and self.stray_tier < 1 and elapsed > 20 and self.can_speak(30):
            self.stray_tier = 1
            self.say(self.brain.line("BRAINROT"), "annoyed")
            self.show_item(self.topic or v.label or "youtube")
            return

        for threshold, tier, pool, mood, label in tiers:
            if mins >= threshold and self.stray_tier < tier and self.can_speak(30):
                self.stray_tier = tier
                flavour = self.flavour_pool(v, pool)
                self.show_item(self.topic or v.label or act.short(40))
                if self.brain.api_on:
                    shot = self.shot_of(act, studying=False)
                    ok = self.brain.request_stray_comment(
                        act.short(90), max(1, mins), label, self.context_line(), shot)
                    self.speak_api_or_bank(ok, flavour, mood,
                                           mins=max(1, mins), what=v.label or act.short(34))
                else:
                    self.speak_bank(flavour, mood, mins=max(1, mins),
                                    what=v.label or act.short(34))
                return

        # keep looking, keep commenting — not once and done
        recheck = float(self.tune("stray_recheck_minutes", default=3)) * 60
        if (recheck and self.stray_tier >= 1
                and now - self._last_stray_look >= recheck and self.can_speak(60)):
            self._last_stray_look = now
            self.show_item(self.topic or v.label or act.short(40))
            if self.brain.api_on:
                shot = self.shot_of(act, studying=False)
                ok = self.brain.request_stray_comment(
                    act.short(90), max(1, mins), "recheck", self.context_line(), shot)
                self.speak_api_or_bank(ok, "STRAY_RECHECK", "annoyed",
                                       mins=max(1, mins), what=v.label or act.short(34))
            else:
                self.speak_bank("STRAY_RECHECK", "annoyed",
                                mins=max(1, mins), what=v.label or act.short(34))
            return

    @staticmethod
    def flavour_pool(v, default_pool):
        """
        Widen the nag pool with lines specific to what they wandered off to.

        Returns a combined LIST rather than a pool name, because it is two pools
        at once — resolved here, in the current language.
        """
        r = (v.reason or "").lower()
        code = lang.code()
        base = bank.pool(default_pool, code)
        for keys, extra in (
            (("steam", "롤", "league", "valorant", "게임", "nexon", "메이플"), "GAMING"),
            (("shopping", "쿠팡", "무신사", "musinsa", "aliexpress"), "SHOPPING"),
            (("instagram", "twitter", " / x", "facebook", "reddit", "더쿠"), "SOCIAL"),
        ):
            if any(k in r for k in keys):
                return base + bank.pool(extra, code)
        return base

    # ---- idle ----

    def handle_idle(self, now, elapsed):
        self.ui.clawd.hold(None)      # nothing to hold up when you aren't there
        if self.can_speak(600):
            self.speak_bank("IDLE", "sleepy", mins=max(3, int(elapsed // 60)))

    # ------------------------------------------------------------------
    # looking at the screen

    def screenshots_allowed(self, studying: bool, force: bool = False) -> bool:
        if not self.brain.api_on:
            return False
        if not self.tune("api", "send_screenshots", default=True):
            return False
        if not force and not studying and not self.tune("api", "screenshot_stray",
                                                        default=True):
            return False
        return capture.available()

    def shot_of(self, act, studying: bool, force: bool = False):
        """
        Capture the foreground window, in memory only, right now.

        Clawd is always-on-top, so he ends up in his own screenshots unless he
        ducks out of frame first — hence the withdraw/deiconify.
        """
        if not self.screenshots_allowed(studying, force):
            return None

        hidden = False
        if self.tune("api", "hide_self_while_capturing", default=True):
            hidden = self.ui.duck()
            if hidden:
                time.sleep(float(self.tune("api", "duck_seconds", default=0.06)))
        try:
            shot = capture.grab_jpeg_b64(
                act.rect,
                int(self.tune("api", "screenshot_max_width", default=1100)),
                int(self.tune("api", "screenshot_quality", default=72)))
        finally:
            if hidden:
                self.ui.unduck()

        if shot:
            self.ui.clawd.flash_watching()
        else:
            self.log(f"screenshot failed: {capture.last_error()}")
        return shot

    # ---- screen reading: only ever when you double-click him ----------

    def show_item_for(self, act):
        """
        Match the window title against the built-in keyword list and hold up an
        icon for it. Purely local: no screenshot, no API call, no cost.

        This is all that is left of the old background watcher. Clawd never
        captures your screen on his own any more — the only thing that takes a
        screenshot is you double-clicking him.
        """
        title = act.short(90)
        if not title:
            return
        known = self._topic_by_title.get(title)
        self.show_item(known or title)

    def fire_look(self, act, mode: str = "check"):
        """Take the screenshot and ask what it is, and what to say about it."""
        shot = self.shot_of(act, studying=self.state == STUDY, force=True)
        if shot is None:
            if not capture.available():
                self.say(t("look.no_capture"), "concerned", 14)
                return
            self.say(t("look.empty"), "concerned", 10)

        self._look_mode = mode
        self._look_started = time.time()
        if self.brain.request_look(act.short(90), shot, self.context_line(), mode):
            self._look_pending = True
            detail = (act.short(60)
                      if self.tune("privacy", "log_screen_details", default=False)
                      else act.process or "?")
            self.log(f"look ({mode}): {detail}")
        else:
            self.say(t("look.busy"), "concerned", 8)

    # ---- the five-minute check-in ----

    def handle_keep(self, now, act, v):
        """
        Company on a timer — but a timer you cannot learn.

        No screenshot and no API call: this runs off the offline bank and costs
        nothing. What changed is WHEN. The old version fired every five minutes
        for as long as you sat there; `Chatter` jitters the gap, stretches it
        each time he speaks on the same window, and remembers a window you
        alt-tabbed away from so coming back does not start the nagging over.

        The two mutes are absolute and sit above the timer: he does not talk
        into a full-screen window, and he does not talk while you are still
        typing.
        """
        if self.state == IDLE:
            return
        key = key_for(act)
        self.chatter.arrive(now, key)

        hushed = self.chatter.muted(act, self.ui.screen_bounds())
        if hushed or not self.chatter.due(now):
            return
        if not self.can_speak(30):
            return

        what = self.topic or (v.label if v else "") or act.short(34)
        # The pool follows the STATE and is not rotated for variety. Swapping a
        # repeat KEEP_STRAY for a neutral line was tried and is wrong: "waiting
        # patiently" while you are on YouTube is not a different way of saying
        # the same thing, it is him losing the plot. Variety comes from the
        # line buffer instead, which refuses the last twenty lines outright —
        # a stronger guarantee than not repeating a category.
        pool = {STUDY: "KEEP_STUDY", STRAY: "KEEP_STRAY"}.get(self.state, "KEEP_NEUTRAL")
        mood = {STUDY: "focus", STRAY: "annoyed"}.get(self.state, "neutral")

        mins = int((now - self.state_since) // 60)
        line = self.chatter.fresh(bank.pool(pool, lang.code()))
        if not line:
            return
        try:
            line = line.format(what=what, mins=mins)
        except (KeyError, IndexError):
            pass
        self._last_keep = now
        self.say(line, mood)
        self.chatter.spoke(now, pool)
        self.show_item(what)

    # ---- ten minutes without the mouse ----

    def handle_mouse(self, now):
        """
        Fireworks when the cursor hasn't twitched for ten minutes.

        Deliberately the mouse and not `idle_seconds`: reading a PDF without
        touching anything is exactly when a nudge helps, and Windows' idle timer
        counts the keyboard too.
        """
        pos = watcher.cursor_pos()
        if pos is not None:
            if self._mouse_at is None or pos != self._mouse_at:
                self._mouse_at = pos
                self._mouse_moved = now
        still = now - self._mouse_moved
        gap = float(self.tune("wake_after_minutes", default=10)) * 60
        if not gap or still < gap:
            return
        if now - self._woke_at < gap:            # one show per quiet stretch
            return
        self._woke_at = now
        # Off by default: coming back to a desk that is setting off the whole
        # screen is a different proposition from a few sparkles over his head,
        # and that should be something you asked for.
        if self.tune("fireworks", "on_wake", default=False):
            self.fireworks_show(f"idle {int(still // 60)}m")
        else:
            self.ui.clawd.fireworks(float(self.tune("wake_seconds", default=4.5)))
        self.log(f"sparkles — no mouse for {int(still // 60)} min")
        if self.can_speak(20):
            self.speak_bank("WAKE_UP", "curious", mins=int(still // 60))

    def handle_night(self, now):
        h = datetime.now().hour
        late = int(self.tune("late_night_hour", default=1))
        if not self.night_done and late <= h < 5 and self.can_speak(120):
            self.night_done = True
            self.speak_bank("LATE_NIGHT", "sleepy", hour=f"{h}")
            self.show_item("sleep", 12)

    # ------------------------------------------------------------------
    # context and quizzing

    def context_line(self) -> str:
        now = datetime.now()
        bits = [f"Right now it is {now:%A %Y-%m-%d %H:%M} (Asia/Seoul)."]
        if self.topic:
            bits.append(f"They appear to be looking at: {self.topic}"
                        + (f" ({self.topic_detail})" if self.topic_detail else "") + ".")
        bits.append(f"Focused minutes logged today: {int(self.study_today // 60)}.")
        # The nearest deadline is the single most useful thing he can know
        # about them: it is what turns "get back to work" into "get back to
        # work, the thing is due tomorrow".
        d = self.sched.due_today(now) or self.sched.due_within(3, now)
        if d:
            bits.append(f"Nearest deadline: {d[0].get('title')} "
                        f"in {humanize(d[0]['_delta'])}.")
        extra = self.tune("about_me", default="")
        if extra:
            bits.append(str(extra))
        return " ".join(bits)

    def begin_quiz(self, act):
        if self.brain.api_on:
            shot = self.shot_of(act, studying=True)
            if self.brain.request_quiz(act.short(90), shot):
                self.say(self.brain.line("QUIZ_INTRO"), "quiz", 6)
                return
        q, a = self.brain.offline_quiz()
        self.start_quiz(q, a)

    def start_quiz(self, question: str, answer: str):
        self.quiz = {"q": question, "a": answer}
        self.ui.say(question, 90, time.time())
        self.last_line_at = time.time()
        self.set_mood("quiz", 90)
        self.motion.set_mode(HOME)
        self.ui.show_entry()

    def on_answer(self, text: str):
        """The answer box only ever belongs to a quiz now."""
        if self.quiz:
            return self.grade_answer(text)

    def reset_neutral(self, why: str = "") -> None:
        """
        Drop everything and go back to neutral.

        Every menu item runs this first, and a double right-click runs it on its
        own. It clears the bubble as well as the mode flags — leaving the old
        one up was why 'fun tidbit' silently did nothing while a quiz was open:
        the question was still on screen, so `ui.talking` was true, so
        `can_speak()` refused, so it returned without a word.
        """
        self.quiz = None
        self.pending = None
        self._look_pending = False
        # A new command supersedes the old one outright. Bumping the id disowns
        # any screen read still in the air, and cancelling the timers stops a
        # capture that was scheduled a moment ago from happening AFTER you have
        # already asked for something else.
        self._check_id = getattr(self, "_check_id", 0) + 1
        self.cancel_check_timers()
        self.ui.hide_entry()
        self.ui.clear_msg()
        dropped = self.brain.cancel_pending()
        self.mood = "neutral"
        self.mood_until = 0.0
        self.last_line_at = 0.0          # whatever you just asked for may speak now
        if self.motion is not None:
            self.motion.set_mode(HOME)
        if why:
            self.log(f"reset ({why})" + (f", dropped {dropped}" if dropped else ""))

    def supersede(self):
        """
        A new input arrived: drop whatever was running, without clearing the
        screen. Opening the menu counts — you have moved on from the last thing
        you asked for, even if you have not yet said what you want instead.
        """
        self._check_id = getattr(self, "_check_id", 0) + 1
        self.cancel_check_timers()
        if self._look_pending:
            self._look_pending = False
            self.brain.cancel_pending()

    def cancel_check_timers(self):
        """Drop a scheduled capture and its watchdog, if either is pending."""
        for name in ("_check_after", "_timeout_after"):
            after = getattr(self, name, None)
            if after is not None:
                try:
                    self.ui.root.after_cancel(after)
                except Exception:
                    pass
                setattr(self, name, None)

    def cancel_input(self, silent: bool = False) -> bool:
        """
        Leave quiz mode without answering.

        `quiz` gates can_speak(), so anything that closed the answer box without
        clearing it left Clawd permanently mute and unable to change mode.
        Escape, an empty Enter, a second click on him, the bubble timing out,
        and every right-click menu item all land here.
        """
        was_open = self.quiz is not None or self.ui.entry_open
        quiz, self.quiz = self.quiz, None
        self.ui.hide_entry()
        self.mood_until = 0.0
        if silent:
            return was_open
        if quiz:
            self.say(self.brain.line("QUIZ_SKIP", answer=quiz["a"]), "curious")
        elif was_open:
            self.ui.clear_msg()
        return was_open

    def grade_answer(self, text: str):
        q, self.quiz = self.quiz, None
        if text.lower() in {"skip", "pass", "dunno", "idk", "몰라", "패스"}:
            self.say(self.brain.line("QUIZ_SKIP", answer=q["a"]), "curious")
            return
        if self.brain.api_on and self.brain.request_grade(q["q"], q["a"], text):
            self.say(t("misc.checking"), "quiz", 8)
            return
        correct = self._offline_grade(q["a"], text)
        pool = "QUIZ_CORRECT" if correct else "QUIZ_WRONG"
        self.say(self.brain.line(pool, answer=q["a"]), "happy" if correct else "curious")

    COMMON = {
        "the", "a", "an", "of", "is", "are", "was", "were", "to", "in", "and", "it",
        "its", "that", "this", "at", "on", "for", "with", "by", "as", "be", "been",
        "has", "have", "had", "will", "would", "can", "could", "do", "does", "you",
        "your", "we", "they", "but", "or", "not", "no", "yes", "so", "if", "when",
        "then", "than", "there", "here", "about", "into", "from", "up", "down", "out",
        "over", "under", "more", "most", "some", "any", "all", "each", "other", "same",
        "very", "just", "only", "also", "because", "which", "what", "how", "why",
        "get", "gets", "got", "make", "makes", "made", "use", "used", "using", "like",
        "one", "two", "first", "second", "thing", "things", "way", "ok", "okay", "im",
        "final", "change", "changes", "value", "values", "kind", "sort", "much",
    }

    @classmethod
    def _tokens(cls, s: str) -> set[str]:
        return {w for w in re.findall(r"[a-z0-9µωτπ]+", s.lower()) if len(w) >= 2}

    @classmethod
    def _offline_grade(cls, expected: str, given: str) -> bool:
        exp, got = cls._tokens(expected), cls._tokens(given)

        def weight(w: str) -> float:
            if w in cls.COMMON:
                return 0.0
            return 2.0 if (any(c.isdigit() for c in w) or len(w) <= 3) else 1.0

        total = sum(weight(w) for w in exp if weight(w) > 0)
        if total <= 0:
            return False
        return sum(weight(w) for w in exp & got) / total >= 0.34

    # ------------------------------------------------------------------
    # interaction

    def on_moved(self, x, y):
        """You dragged him — that's his new home."""
        self.motion.start_at(x, y)
        self.motion.set_mode(HOME)

    def menu_spec(self):
        """
        The tray menu, as data: (label, callback) pairs, None for a separator.

        This is the ONLY menu now. The sprite has no popup: you pick him up or
        you double-click him, and everything else lives here. Built fresh on
        every click, because half these labels describe state.

        Every callback is wrapped so that asking for something *always* wins
        over whatever is already running — see `command()`.
        """
        cmd = self.command

        items = [
            # From the tray you may well have lost sight of him entirely, so
            # the first thing offered is putting him back somewhere visible.
            (t("menu.bring_back"), cmd(lambda: self.rescue("tray"))),
            None,
            (t("menu.quiz"), cmd(lambda: self.begin_quiz(self.last_act
                                                         or watcher.foreground()))),
            (t("menu.tidbit"), cmd(lambda: self.fire_tidbit(self.topic))),
            (t("menu.briefing"), cmd(self.show_briefing)),
        ]
        if self.tune("fireworks", "enabled", default=True):
            items.append((t("menu.fireworks"),
                          cmd(lambda: self.fireworks_show("menu"))))
        if self.ui.entry_open or self.quiz:
            items.append((t("menu.nevermind"), cmd(self.ui.clear_msg)))
        items += [
            None,
            (t("menu.language"), cmd(self.toggle_language)),
            (t("menu.edit_sched"), cmd(lambda: self.open_file(SCHEDULE_PATH))),
            None,
            (t("menu.change_key" if self.brain.key() else "menu.set_key"),
             cmd(self.ask_key)),
            (t("menu.test_key"), cmd(self.test_key)),
        ]
        if secrets.stored():
            items.append((t("menu.forget_key"), cmd(self.forget_key)))
        items += [
            (t("menu.spend"), cmd(self.show_spend)),
            None,
            (t("menu.quit"), cmd(self.quit)),
        ]
        return items

    def check_screen(self):
        """
        Double-click him: he takes one look at your screen and reacts to it.

        This is the ONLY thing in Clawd that captures your screen. He works out
        for himself whether what he sees is studying, straying, or something he
        cannot call either way, and answers in kind — a compliment, a telling
        off, or a suspicious "...are you actually studying".
        """
        self.reset_neutral("check")
        if not self.brain.api_on:
            # no key, or the budget is spent: fall back on what he can tell from
            # the window title alone, which is the same allowlist the nagging uses
            if not self.brain.api_configured:
                self.say(t("key.opening"), "concerned", 6)
                self.ui.root.after(700, self.ask_key)
                return
            self.offline_check()
            return
        self._look_pending = False
        self.topic = self.topic_detail = ""
        delay = max(0.3, float(self.tune("api", "manual_delay_seconds", default=0.35)))
        # no commentary while he looks — just dots until the answer lands
        self.say(t("look.thinking"), "curious", delay + 25.0)
        self.ui.clawd.flash_watching(delay + 2.0)
        self._check_id = getattr(self, "_check_id", 0) + 1
        self._check_after = self.ui.root.after(int(delay * 1000), self._do_check)
        # He must never just go quiet. If the answer has not landed by the time
        # this fires, he reacts anyway from the window title — a wrong-ish
        # verdict beats a double-click that visibly does nothing.
        wait = int((delay + float(self.tune("api", "check_timeout_seconds",
                                            default=18))) * 1000)
        self._timeout_after = self.ui.root.after(
            wait, lambda n=self._check_id: self._check_timeout(n))

    def _check_timeout(self, check_id: int):
        """The look never came back. Say something regardless."""
        self._timeout_after = None
        if check_id != getattr(self, "_check_id", 0) or not self._look_pending:
            return
        self._look_pending = False
        self.brain.cancel_pending()
        self.log("check: timed out, answering from the title instead")
        self.offline_check()

    def _do_check(self):
        self._check_after = None
        """
        Fires `manual_delay_seconds` after the double-click.

        The delay re-reads the foreground window at capture time, so clicking
        Clawd does not make Clawd the subject: you land back in whatever you
        were doing and he photographs THAT.
        """
        act = watcher.foreground()
        if watcher.is_own_window(act, {"Clawd"}) or not (act.title or act.process):
            act = self.last_act or act
        self.last_act = act
        self.fire_look(act, "check")
        if not self._look_pending:       # nothing was sent — don't leave dots up
            self._check_id = getattr(self, "_check_id", 0) + 1

    # verdict -> (mood, offline pool). The three ways a look can land.
    CHECK_REACTION = {
        "study":  ("proud", "CHECK_STUDY"),
        "stray":  ("annoyed", "CHECK_STRAY"),
        "unsure": ("confused", "CHECK_UNSURE"),
    }

    def offline_check(self):
        """The double-click reaction without an API: classify the title, react."""
        act = self.last_act or watcher.foreground()
        v = classify(act, self.cfg)
        verdict = {STUDY: "study", STRAY: "stray"}.get(v.state, "unsure")
        self.react_to_check(verdict, "")

    # ---- pardons: a look can overrule the keyword rules ----------------

    def pardon_key(self, act) -> str:
        """
        What a pardon is filed under: the window title with the noise stripped.

        The same normalising the settle timer uses, so a ticking video clock or
        an unread badge does not turn a pardoned lecture back into a stranger.
        """
        return screenwatch.normalise(act.short(120)) if act else ""

    def is_pardoned(self, act) -> bool:
        key = self.pardon_key(act)
        if not key:
            return False
        until = self._pardoned.get(key, 0.0)
        if until and until > time.time():
            return True
        self._pardoned.pop(key, None)
        return False

    def pardon(self, act):
        """He looked, it was coursework: stop being angry at this window."""
        key = self.pardon_key(act)
        if not key:
            return False
        hours = float(self.tune("focus", "pardon_hours", default=6))
        self._pardoned[key] = time.time() + hours * 3600
        if len(self._pardoned) > 40:                # keep it from growing forever
            for dead in sorted(self._pardoned, key=self._pardoned.get)[:-30]:
                self._pardoned.pop(dead, None)
        # take the anger back down with it, and re-decide from scratch
        self.stray_tier = 0
        self.state, self.state_since = STUDY, time.time()
        self._verdict = self._settling = None
        self.motion.set_mode(HOME)
        self.log("pardoned this window")
        return True

    def revoke_pardon(self, act):
        """He looked again and it was not coursework after all."""
        self._pardoned.pop(self.pardon_key(act), None)

    def react_to_check(self, verdict: str, line: str):
        """Mood, animation and comment for one of the three verdicts."""
        mood, pool = self.CHECK_REACTION.get(verdict,
                                             self.CHECK_REACTION["unsure"])
        self.log(f"check: {verdict}")

        # The whole point of being able to check: a lecture that lives on
        # YouTube is judged by what is ON the screen, not by the word in the
        # title. If he was cross about this window and the look says otherwise,
        # the look wins and he lets it go.
        act = self.last_act
        forgiven = False
        if verdict == "study" and act is not None:
            was_cross = self.state == STRAY or classify(act, self.cfg).is_stray
            if was_cross and not self.is_pardoned(act):
                forgiven = self.pardon(act)
        elif verdict == "stray" and act is not None:
            self.revoke_pardon(act)

        if forgiven and not line:
            self.speak_bank("PARDON", mood, what=self.topic or "")
        elif line:
            self.say(line, mood, 14)
        else:
            self.speak_bank(pool, mood, what=self.topic or "")
        self.set_mood(mood, 14)

    # ---- language and size -------------------------------------------

    def toggle_language(self):
        """
        한/영. Everything is resolved at speak time, so this takes effect on his
        very next line — the menu, the dialogs, the offline bank and the
        instruction appended to every API prompt all follow immediately.
        """
        code = lang.set(lang.other())
        self.cfg["language"] = code
        _save_json(CONFIG_PATH, self.cfg)
        self.log(f"language: {code}")
        self.tray.set_tip(t("tray.tip"))
        self.say(t("misc.lang_set"), "happy", 7)

    def sync_motion_bounds(self):
        """Re-hand Motion the geometry after a resize, and re-home him safely."""
        if self.motion is None:
            return
        bounds = self.ui.screen_bounds()
        self.motion.ox, self.motion.oy = self.ui.CLAWD_OX, self.ui.CLAWD_OY
        self.motion.ww, self.motion.wh = self.ui.W, self.ui.H
        self.motion.spw = self.ui.clawd.width_px
        self.motion.sph = self.ui.clawd.height_px
        self.motion.screen_rect = bounds
        self.motion.sw = bounds[2] - bounds[0]
        self.motion.sh = bounds[3] - bounds[1]
        x, y = self.ui._clamp(self.ui.x, self.ui.y)
        self.ui.place(x, y)
        self.motion.start_at(x, y)

    def rescue(self, why: str = ""):
        """
        Put him back where he can be seen.

        Nothing should be able to get him off screen any more, but if anything
        ever does he is unreachable — the window is transparent and
        click-through, so there is no way to right-click him and no tray icon to
        fall back on. This runs from the frame loop, so recovery needs no input.
        """
        x, y = self.ui.home_corner()
        self.ui.place(x, y)
        self.motion.set_mode(HOME)
        self.motion.start_at(x, y)
        self.cfg.setdefault("appearance", {})["position"] = [x, y]
        self.log(f"rescued to {x},{y}" + (f" ({why})" if why else ""))

    def command(self, fn):
        """
        Wrap a command so that asking for it drops whatever came before.

        This is the rule for every entry point — every tray item, and the
        double-click — and it has no conditions on it. It does not matter that
        a screen check is mid-capture, that an API answer is two seconds from
        arriving, or that a quiz is waiting for your answer: you have asked for
        something else, so the old thing is over. Anything less means the
        previous command lands on top of the new one, seconds later, and the
        app looks like it ignored you.

        In order: drop the in-flight work (`supersede`), then the mode flags,
        the bubble and the rate limiter (`reset_neutral` — without that last
        part a command could fire and produce nothing at all), then run.
        """
        def run(*_a, **_k):
            self.supersede()
            # You reached for him, so he has not worn out his welcome on this
            # window: one step of the decay comes back.
            self.chatter.engaged(time.time())
            self.reset_neutral("command")
            fn()
        return run

    # ------------------------------------------------------------------
    # the full-screen show

    def fireworks_show(self, why: str = "menu"):
        """
        Set the whole desktop off.

        Its own window, so Clawd stays exactly where he is and stays the size
        he is; click-through, so it never costs you the click you were about to
        make. `fireworks.enabled: false` in config.json switches it off, and
        the menu item goes with it.
        """
        if self.fw is None or not self.tune("fireworks", "enabled", default=True):
            return
        # The desktop can have gained or lost a monitor since startup.
        self.fw.bounds = self.ui.screen_bounds()
        sound = SOUND_PATH if self.tune("fireworks", "sound", default=True) else ""
        self.fw.show(seconds=float(self.tune("fireworks", "seconds", default=6.0)),
                     count=int(self.tune("fireworks", "bursts", default=9)),
                     sound=sound)
        self.ui.clawd.fireworks(3.0)     # he sparkles along with it
        self.log(f"fireworks ({why})")

    # ------------------------------------------------------------------
    # schedule: briefings and deadline nagging

    def show_briefing(self):
        """Today, in one bubble: classes, what is due, what is still pending."""
        now = datetime.now()
        head = f"{now:%m/%d (%a) %H:%M}"
        lines = [head] + self.sched.briefing(now)[:4]
        self.say("\n".join(lines), "curious", 16)
        self.show_item("deadline", 16)

    def mark_ok(self, key: str, every_seconds: float) -> bool:
        """True at most once per `every_seconds` for this key."""
        now = time.time()
        if now - self.sched_marks.get(key, 0) < every_seconds:
            return False
        self.sched_marks[key] = now
        return True

    def handle_schedule(self, now):
        """
        Say at most one schedule-driven thing per poll, worst first.

        Order matters and the `return`s are the point: overdue beats due-today
        beats due-soon beats a pending todo. Without them a busy week would
        empty the whole calendar into the bubble at once, which is noise, and
        noise is what you learn to ignore.
        """
        if not self.can_speak(120):
            return

        for c in self.sched.starting_soon(25):
            if self.mark_ok("class:" + str(c.get("name") or c.get("title")), 3600):
                self.speak_bank("CLASS_SOON", "curious",
                                course=c.get("name") or c.get("title", "your thing"),
                                due=humanize(c["_delta"]))
                self.show_item("schedule", 12)
                return

        for d in self.sched.overdue():
            if self.mark_ok("over:" + d.get("title", "?"), 5400):
                self.speak_bank("OVERDUE", "disappointed",
                                task=d.get("title"), due=humanize(d["_delta"]))
                self.show_item("deadline", 12)
                return

        for d in self.sched.due_today():
            if self.mark_ok("today:" + d.get("title", "?"), 5400):
                self.speak_bank("DUE_TODAY", "annoyed",
                                task=d.get("title"), due=humanize(d["_delta"]))
                self.show_item("deadline", 12)
                return

        horizon = int(self.tune("deadline_horizon_days", default=3))
        for d in self.sched.due_within(horizon):
            if self.mark_ok("soon:" + d.get("title", "?"), 14400):
                self.speak_bank("DUE_SOON", "curious",
                                task=d.get("title"), due=humanize(d["_delta"]))
                return

        todos = self.sched.todos()
        if todos and self.mark_ok("todo", float(self.tune("todo_poke_hours",
                                                          default=3)) * 3600):
            self.speak_bank("TODO_POKE", "curious",
                            task=random.choice(todos).get("title", "that thing"))

    @staticmethod
    def open_file(path):
        """Open a file in whatever the OS thinks should edit it."""
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def show_spend(self):
        if not self.brain.api_configured:
            self.say(t("misc.no_spend"), "neutral", 8)
            return
        self.say(self.budget.summary(), "curious", 12)

    def test_key(self):
        ok, msg = self.brain.test_key()
        src = self.brain.key_source()
        self.say(msg + (t("key.source", src=src) if ok and src else ""),
                 "happy" if ok else "concerned", 12)

    def quit(self):
        _save_json(STATE_PATH, {"date": self.day, "study_seconds": round(self.study_today)})
        self.cfg.setdefault("appearance", {})["position"] = [
            int(self.motion.home[0]), int(self.motion.home[1])]
        _save_json(CONFIG_PATH, self.cfg)
        self.log(f"session end — {int(self.study_today // 60)} focused minutes")
        if self.fw is not None:
            self.fw.stop()      # a show outliving the app would never come down
        self.tray.stop()        # or the icon is left behind as a dead ghost
        single.release()
        self.ui.root.destroy()

    def run(self):
        self.ui.root.mainloop()


def main():
    # One at a time. Two Clawds fight over always-on-top, both put an icon in
    # the tray so quitting one orphans the other's, both write state.json, and
    # every nag and screen check happens twice at twice the cost.
    if not single.acquire():
        single.already_running_notice()
        return

    # Must happen before Tk exists, and before anything reads a window rect:
    # without it, GetWindowRect returns logical pixels while the screen grab
    # returns physical ones, and every screenshot is cropped to the top-left
    # corner of the display.
    dpi.enable()
    try:
        App().run()
    finally:
        single.release()


if __name__ == "__main__":
    main()
