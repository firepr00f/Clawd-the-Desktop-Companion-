"""
The floating window: pixel Clawd + a pixel speech bubble + the quiz answer box.

One borderless always-on-top Tk window with a colour-keyed transparent
background, so only Clawd and the bubble are visible (and the transparent
area is click-through on Windows).

Layout is computed from `appearance` in config.json rather than hard-coded, so
the bubble can be made as big as you like without touching this file:

    pixel_size          size of one Clawd pixel, in screen px
    font_size           bubble text size
    bubble_width        max text width inside the bubble, in px
    bubble_max_height   how tall the bubble may grow before text is trimmed

The canvas then sizes itself around whatever those add up to. The old build
had W,H = 470,330 with the bubble capped at 292px wide and clamped to the top
of the canvas, which is why longer lines came out cramped or clipped.
"""

from __future__ import annotations

import time as _time
import tkinter as tk
from tkinter import font as tkfont

from . import dpi
from .lang import t
from .sprite import GRID_H, GRID_W, BLACK, WHITE, Clawd

_now = _time.monotonic

KEY = "#010203"          # transparency key colour — must not appear in artwork

BUBBLE_BG = WHITE
BUBBLE_TXT = "#141414"
PIXEL_FONTS = ("Press Start 2P", "Silkscreen", "DungGeunMo", "Galmuri11",
               "Consolas", "Courier New", "TkFixedFont")

# Padding around Clawd, in sprite cells. Clawd's decorations (sparkles, z's,
# anger marks, the held item) live outside his 18x11 grid, so the canvas has to
# leave room for them or they get clipped at the edges.
PAD_L_CELLS = 11         # held item sits at x = -10
PAD_R_CELLS = 8          # happy/proud sparkles reach x = 23
PAD_B_CELLS = 3          # legs + bob
HEAD_CELLS = 5           # anger marks / z's / quiz mark reach y = -5

# He is one size now. The three-stage giant/normal/petite cycle is gone and the
# double-click that drove it does something useful instead — see App.check_screen.
# appearance.pixel_size / font_size / bubble_width still scale him if you want
# him bigger; they are just not a thing you flip through at runtime any more.


class Overlay:
    def __init__(self, cfg: dict, on_answer, on_moved=None,
                 on_cancel=None, on_double=None, on_resized=None):
        self.cfg = cfg
        self.on_answer = on_answer
        self.on_moved = on_moved
        self.on_double = on_double        # double-click: check the screen
        # told after any resize, so Motion's bounds can never go stale
        self.on_resized = on_resized
        # called whenever the answer box closes WITHOUT an answer, so the app
        # can leave quiz mode instead of staying stuck in it
        self.on_cancel = on_cancel or (lambda silent=False: None)

        self.root = tk.Tk()
        self.root.title("Clawd")
        self.root.overrideredirect(True)
        self._topmost = True
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass                      # non-Windows: window just has a solid bg
        self.root.configure(bg=KEY)

        self._measure()

        self.cv = tk.Canvas(self.root, width=self.W, height=self.H, bg=KEY,
                            highlightthickness=0, bd=0)
        self.cv.pack()

        look = cfg.get("appearance", {})
        self.clawd = Clawd(self.cv, self.CLAWD_OX, self.CLAWD_OY, self.cell,
                           outline=bool(look.get("sticker_outline", False)))

        self.font = tkfont.Font(family=self._pick_font(), size=self.font_size)

        self._bubble_items: list[int] = []
        self._msg = ""
        self._msg_until = 0.0

        # quiz answer box (hidden until needed)
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self.root, textvariable=self.entry_var,
                              font=self.font, relief="flat", bd=0,
                              highlightthickness=max(2, self.u // 2),
                              highlightbackground=BLACK, highlightcolor=BLACK,
                              bg=WHITE, fg=BUBBLE_TXT, insertbackground=BUBBLE_TXT)
        self.entry.bind("<Return>", lambda e: self._submit())
        self.entry.bind("<Escape>", lambda e: self.cancel_entry())
        self._entry_win: int | None = None

        # interaction
        self._drag = None
        self._suppress_click = False
        self._ducked = None            # where he was before hiding for a capture
        # Two ways to touch him and no more: pick him up, or double-click him.
        # There is no menu on the sprite any more and no single-click action —
        # the tray owns every command now, and the whole apparatus that kept an
        # always-on-top window from fighting its own popup went with it.
        for seq, fn in (("<ButtonPress-1>", self._press),
                        ("<B1-Motion>", self._motion),
                        ("<ButtonRelease-1>", self._release),
                        ("<Double-Button-1>", self._double)):
            self.cv.bind(seq, fn)
        # Escape anywhere on the overlay drops whatever question is open.
        self.root.bind_all("<Escape>", self._escape, add="+")

        self.place(*self._saved_pos())

    # ------------------------------------------------------------------
    # layout

    def _measure(self):
        """Work out every coordinate from config + the current display scale."""
        look = self.cfg.get("appearance", {}) or {}

        # Once the process is DPI aware, Tk geometry is in physical pixels, so
        # a 9px sprite cell on a 150% display would render two thirds the size
        # it used to. Scaling by the same factor keeps him looking identical.
        s = dpi.scale() if look.get("auto_dpi_scale", True) else 1.0

        self.cell = max(3.0, float(look.get("pixel_size", 9)) * s)
        self.font_size = max(7, int(round(float(look.get("font_size", 16)) * s)))
        self.u = max(3, int(self.cell * 0.6))          # bubble border unit
        self.pad = self.u * 2

        self.bubble_w = max(160, int(float(look.get("bubble_width", 640)) * s))
        self.bubble_max_h = max(120, int(float(look.get("bubble_max_height", 460)) * s))

        c = self.cell
        sprite_w, sprite_h = GRID_W * c, GRID_H * c
        self.head_room = HEAD_CELLS * c
        self.tail_h = self.u * 4

        self.CLAWD_OX = int(PAD_L_CELLS * c)
        self.CLAWD_OY = int(self.bubble_max_h + self.tail_h + self.head_room + self.u * 2)

        self.entry_h = self.font_size * 2 + 12
        entry_band = self.entry_h + 10

        clawd_span = int(PAD_L_CELLS * c + sprite_w + PAD_R_CELLS * c)
        bubble_span = self.bubble_w + 2 * self.pad + 4 * self.u + 8
        self.W = int(max(clawd_span, bubble_span))
        self.H = int(self.CLAWD_OY + sprite_h + PAD_B_CELLS * c + entry_band)

        # bubble anchors: outer bottom-right corner of the white box
        self.anchor_right = self.W - 2 * self.u - 4
        self.anchor_bottom = int(self.CLAWD_OY - self.head_room)
        self.tail_tip_x = int(self.CLAWD_OX + (GRID_W / 2) * c)

    def _pick_font(self) -> str:
        want = (self.cfg.get("appearance", {}) or {}).get("font")
        available = set(tkfont.families())
        for fam in ((want,) if want else ()) + PIXEL_FONTS:
            if fam in available:
                return fam
        return "TkFixedFont"

    # ------------------------------------------------------------------

    def _saved_pos(self):
        """
        Where he starts. A saved position from a bigger screen, a different
        size, or a version with the broken clamp is pulled back on screen here,
        so a lost Clawd fixes himself on the next launch.
        """
        pos = (self.cfg.get("appearance", {}) or {}).get("position")
        if isinstance(pos, list) and len(pos) == 2:
            try:
                return self._clamp(int(pos[0]), int(pos[1]))
            except (TypeError, ValueError):
                pass
        return self.home_corner()

    def screen_bounds(self) -> tuple[int, int, int, int]:
        """
        The whole visible desktop as (left, top, right, bottom).

        The virtual screen spans every monitor, so dragging him to a second
        display doesn't get him yanked back to the primary one.
        """
        vs = dpi.virtual_screen()
        if vs:
            return vs
        return (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())

    def usable_bounds(self, x: int | None = None, y: int | None = None):
        """
        Where he is allowed to stand: the desktop MINUS the taskbar.

        `screen_bounds` is every pixel that exists, taskbar strip included, and
        clamping to it is how he ended up parked behind the system tray —
        painted over by the taskbar, invisible, and with nothing to right-click.
        Anything that decides *where to put him* uses this instead.
        """
        l, t, r, b = self.screen_bounds()
        # Careful: this runs during __init__, from the very first _clamp, before
        # self.x exists. With no position to go on, ask about the primary
        # monitor rather than reaching for one that isn't there yet.
        mid = None
        if x is not None and y is not None:
            mid = (int(x + self.CLAWD_OX + GRID_W * self.cell / 2),
                   int(y + self.CLAWD_OY + GRID_H * self.cell / 2))
        elif hasattr(self, "x"):
            sl, st, sr, sb = self.sprite_rect()
            mid = (int((sl + sr) // 2), int((st + sb) // 2))
        wa = dpi.work_area(*mid) if mid else dpi.work_area()
        if not wa:
            return (l, t, r, b)
        # intersect, so a bogus work area can never shrink him off the desktop
        wl, wt, wr, wb = wa
        out = (max(l, wl), max(t, wt), min(r, wr), min(b, wb))
        if out[2] - out[0] < 40 or out[3] - out[1] < 40:
            return (l, t, r, b)
        return out

    def sprite_rect(self, x: int | None = None, y: int | None = None):
        """Where CLAWD himself is on screen, for a given window position."""
        x = self.x if x is None else x
        y = self.y if y is None else y
        return (x + self.CLAWD_OX, y + self.CLAWD_OY,
                x + self.CLAWD_OX + GRID_W * self.cell,
                y + self.CLAWD_OY + GRID_H * self.cell)

    def on_screen(self, x: int | None = None, y: int | None = None) -> bool:
        """
        Can you actually see and click him?

        Measured against the usable area, not the raw desktop: a sprite sitting
        entirely inside the taskbar strip is painted over and unreachable, which
        is a lost Clawd even though every pixel of him is "on screen". He only
        has to overlap it — dragging him half over the taskbar is your business.
        """
        l, t, r, b = self.usable_bounds(x, y)
        sl, st, sr, sb = self.sprite_rect(x, y)
        return sr > l and sl < r and sb > t and st < b

    def _clamp(self, x: int, y: int) -> tuple[int, int]:
        """
        Keep CLAWD on screen — not the window.

        This is the bug that lost him entirely. The window is mostly empty
        bubble space *above* him: on a 150-200% display CLAWD_OY is over a
        thousand pixels, so a clamp written against the window rectangle let his
        sprite sit 600+ px below the bottom edge — invisible, and unclickable,
        with no way back short of editing config.json.
        """
        l, t, r, b = self.usable_bounds(x, y)
        w, h = GRID_W * self.cell, GRID_H * self.cell
        margin = max(6.0, self.cell)

        lo_x, hi_x = l + margin - self.CLAWD_OX, r - margin - w - self.CLAWD_OX
        lo_y, hi_y = t + margin - self.CLAWD_OY, b - margin - h - self.CLAWD_OY
        if hi_x < lo_x:                       # sprite wider than the desktop
            lo_x = hi_x = (lo_x + hi_x) / 2.0
        if hi_y < lo_y:
            lo_y = hi_y = (lo_y + hi_y) / 2.0
        return (int(round(max(lo_x, min(hi_x, x)))),
                int(round(max(lo_y, min(hi_y, y)))))

    def home_corner(self) -> tuple[int, int]:
        """His default spot: bottom-right, above the taskbar, fully visible."""
        l, t, r, b = self.usable_bounds()
        return self._clamp(int(r - GRID_W * self.cell - self.CLAWD_OX - 4 * self.cell),
                           int(b - GRID_H * self.cell - self.CLAWD_OY - 2 * self.cell))

    def place(self, x: int, y: int):
        """
        Move the window. Unconditionally — everything that moves him comes
        through here, and there is no longer anything it has to wait for.

        This used to be full of exceptions. A Tk menu belongs to the window it
        was posted from and travels with it, so him walking (or `duck()`, which
        throws the window 30000px away to keep him out of his own screenshot)
        dragged the open menu along with it. All of that left with the menu.
        """
        self.x, self.y = int(x), int(y)
        self.root.geometry(f"{self.W}x{self.H}+{self.x}+{self.y}")

    def ask_secret(self, title: str, blurb: str, extra_label: str = "",
                   on_done=None):
        """
        A small window for typing something you don't want on screen.

        Its own Toplevel rather than the speech bubble: the overlay is
        borderless, click-through where it's transparent, and colour-keyed, none
        of which suits a password field. Input is masked, and the value is
        handed straight to `on_done` — it is never put in a bubble or the log.
        """
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg="#1d1f26")
        win.attributes("-topmost", True)
        win.resizable(False, False)

        pad = {"padx": 14, "pady": (10, 0)}
        tk.Label(win, text=blurb, bg="#1d1f26", fg="#d8dbe2", justify="left",
                 wraplength=430).pack(anchor="w", **pad)

        var = tk.StringVar()
        entry = tk.Entry(win, textvariable=var, show="•", width=52,
                         relief="flat", bd=0, highlightthickness=2,
                         highlightbackground="#3a3f4b", highlightcolor="#5B8FD9",
                         bg="#2a2d36", fg="#f0f2f6", insertbackground="#f0f2f6")
        entry.pack(fill="x", padx=14, pady=(10, 0))

        show = tk.IntVar(value=0)
        tk.Checkbutton(win, text=t("key.show"), variable=show,
                       command=lambda: entry.config(show="" if show.get() else "•"),
                       bg="#1d1f26", fg="#9aa0ad", selectcolor="#2a2d36",
                       activebackground="#1d1f26", activeforeground="#d8dbe2",
                       bd=0, highlightthickness=0).pack(anchor="w", padx=10, pady=(6, 0))

        extra = tk.IntVar(value=0)
        if extra_label:
            tk.Checkbutton(win, text=extra_label, variable=extra,
                           bg="#1d1f26", fg="#9aa0ad", selectcolor="#2a2d36",
                           activebackground="#1d1f26", activeforeground="#d8dbe2",
                           bd=0, highlightthickness=0).pack(anchor="w", padx=10)

        note = tk.Label(win, text="", bg="#1d1f26", fg="#e88b8b",
                        wraplength=430, justify="left")
        note.pack(anchor="w", padx=14, pady=(4, 0))

        row = tk.Frame(win, bg="#1d1f26")
        row.pack(fill="x", padx=12, pady=12)

        def close():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        def submit():
            value = var.get().strip()
            if not value:
                note.config(text=t("key.empty"))
                return
            var.set("")
            close()
            if on_done:
                on_done(value, bool(extra.get()))

        tk.Button(row, text=t("key.cancel"), command=close, bd=0, relief="flat",
                  bg="#2a2d36", fg="#c3c8d2", activebackground="#343845",
                  activeforeground="#f0f2f6", padx=14, pady=4).pack(side="right")
        tk.Button(row, text=t("key.save"), command=submit, bd=0, relief="flat",
                  bg="#5B8FD9", fg="#0f1116", activebackground="#7aa6e4",
                  activeforeground="#0f1116", padx=18, pady=4).pack(side="right", padx=(0, 8))

        entry.bind("<Return>", lambda e: submit())
        win.bind("<Escape>", lambda e: close())
        win.protocol("WM_DELETE_WINDOW", close)

        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        w, h = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        entry.focus_force()
        try:
            win.grab_set()
        except Exception:
            pass
        return win

    DUCK_OFFSET = 30000            # far enough to be off any real desktop

    def duck(self) -> bool:
        """
        Get him out of the way of his own screenshot.

        He is MOVED off screen, not withdrawn. withdraw()/deiconify() is what
        made him freeze and sometimes come back wrong: hiding and re-showing a
        borderless, always-on-top, colour-keyed window tears down and rebuilds
        all three of those properties, and Tk skips re-applying a transparent
        colour that hasn't changed — so he could return as a solid rectangle
        sitting on top of everything. Sliding the window 30000px away has none
        of that: same window, same properties, back in one geometry call.
        """
        try:
            self._ducked = (self.x, self.y)
            self.root.geometry(f"{self.W}x{self.H}"
                               f"+{self.x}+{self.y + self.DUCK_OFFSET}")
            self.root.update_idletasks()
            return True
        except Exception:
            self._ducked = None
            return False

    def unduck(self):
        try:
            back, self._ducked = self._ducked, None
            if back:
                self.place(*back)
            self.root.update_idletasks()
        except Exception:
            pass

    def _press(self, e):
        self._drag = (e.x_root - self.x, e.y_root - self.y, e.x_root, e.y_root)

    def _motion(self, e):
        if self._drag:
            dx, dy, *_ = self._drag
            self.clawd.dragging = True        # kick, until you put him down
            self.place(e.x_root - dx, e.y_root - dy)

    def _release(self, e):
        self.clawd.dragging = False
        if not self._drag:
            return
        _, _, sx, sy = self._drag
        moved = abs(e.x_root - sx) + abs(e.y_root - sy)
        self._drag = None
        if moved >= 4:
            self.cfg.setdefault("appearance", {})["position"] = [self.x, self.y]
            if self.on_moved:
                self.on_moved(self.x, self.y)
        # A single click does nothing, so there is no pending action to hold
        # back here and nothing to cancel when the second click arrives.

    def _double(self, _e):
        self._drag = None
        if self.on_double:
            self.on_double()

    def set_topmost(self, on: bool):
        """
        Give up always-on-top, or take it back.

        Nothing in Clawd calls this any more — the one thing that needed it was
        the popup menu, which is now a native Win32 menu owned by the tray's
        own window and does not care what this overlay is doing. Kept because
        anything that has to share the top of the z-order will want it, and it
        only ever acts on a change, so it is never a per-frame Windows call.
        """
        on = bool(on)
        if on == self._topmost:
            return
        self._topmost = on
        try:
            self.root.attributes("-topmost", on)
        except Exception:
            pass

    def _escape(self, _e=None):
        """Escape still drops whatever question is open."""
        self._drag = None
        self.cancel_entry(silent=True)

    # ------------------------------------------------------------------

    def say(self, text: str, seconds: float | None = None, now: float = 0.0):
        self._msg = text or ""
        secs = seconds if seconds is not None else self._read_time(text)
        self._msg_until = now + secs

    @staticmethod
    def _read_time(text: str) -> float:
        return max(4.5, min(30.0, 2.4 + len(text) / 14.0))

    def clear_msg(self):
        self._msg = ""
        self._msg_until = 0.0

    @property
    def talking(self) -> bool:
        return bool(self._msg)

    # ------------------------------------------------------------------

    def show_entry(self, _placeholder: str = ""):
        """
        The answer box, tucked under him.

        It used to span the whole canvas — a 670px white bar pinned to the
        bottom edge of a mostly-transparent window, floating on the desktop
        nowhere near Clawd or the question. Now it starts at his left shoulder
        and is about as wide as a sentence, so it reads as part of him.
        """
        if self._entry_win is not None:
            self.cv.delete(self._entry_win)
        x = self.CLAWD_OX
        width = int(max(20 * self.cell,
                        min(self.bubble_w * 0.62, self.W - x - 2 * self.u)))
        self._entry_win = self.cv.create_window(
            x, self.H - self.entry_h - 6, anchor="nw",
            window=self.entry, width=width, height=self.entry_h)
        self.entry_var.set("")
        self.entry.focus_force()

    @property
    def entry_open(self) -> bool:
        return self._entry_win is not None

    def hide_entry(self):
        """Just take the box away. Does NOT tell the app anything."""
        if self._entry_win is not None:
            self.cv.delete(self._entry_win)
            self._entry_win = None
        try:
            self.root.focus_set()
        except Exception:
            pass

    def cancel_entry(self, silent: bool = False):
        """
        Close the box without an answer AND tell the app, so it can drop out of
        quiz mode. Escape used to only do the first half, which left the
        app stuck: can_speak() stayed false forever and clicking Clawd just
        reopened the box.
        """
        if self._entry_win is None:
            return False
        self.hide_entry()
        self.on_cancel(silent)
        return True

    def _submit(self):
        text = self.entry_var.get().strip()
        if not text:
            self.cancel_entry()          # empty Enter means "never mind"
            return
        self.hide_entry()
        self.on_answer(text)

    # ------------------------------------------------------------------

    def render(self, dt: float, now: float, mood: str):
        self.clawd.set_mood(mood)
        self.clawd.tick(dt)
        for i in self._bubble_items:
            self.cv.delete(i)
        self._bubble_items.clear()
        if self._msg and now < self._msg_until:
            self._draw_bubble(self._msg)
        elif self._msg:
            self.clear_msg()
            # the bubble timing out is also how an unanswered question expires
            if not self.cancel_entry(silent=True):
                self.hide_entry()

    # ------------------------------------------------------------------

    def _blk(self, x, y, w, h, color):
        self._bubble_items.append(
            self.cv.create_rectangle(x, y, x + w, y + h, fill=color, outline=""))

    def _fit(self, text: str):
        """
        Lay the text out so it FITS, rather than cutting it off.

        Three moves, in order, before anything is thrown away:
          1. widen the bubble, up to whatever the canvas can hold
          2. step the font down, to 70% of its normal size
          3. only then trim, with an ellipsis

        A long tidbit used to hit the height cap at step zero and lose its last
        sentence, which is the half that usually carried the point.
        """
        widest = max(self.bubble_w, self.W - 6 * self.u - 2 * self.pad)
        base = self.font_size
        attempts = [(self.bubble_w, base), (widest, base)]
        for pct in (0.88, 0.78, 0.70):
            attempts.append((widest, max(8, int(round(base * pct)))))

        for width, size in attempts:
            self.font.configure(size=size)
            t = self.cv.create_text(0, 0, text=text, anchor="nw", width=width,
                                    font=self.font, fill=BUBBLE_TXT, justify="left")
            _, y0, _, y1 = self.cv.bbox(t)
            if (y1 - y0) <= self.bubble_max_h:
                return t
            self.cv.delete(t)

        # still too tall: trim at the widest and smallest we allow
        width, size = attempts[-1]
        self.font.configure(size=size)
        body = text
        for _ in range(8):
            t = self.cv.create_text(0, 0, text=body, anchor="nw", width=width,
                                    font=self.font, fill=BUBBLE_TXT, justify="left")
            _, y0, _, y1 = self.cv.bbox(t)
            if (y1 - y0) <= self.bubble_max_h or len(body) < 60:
                return t
            self.cv.delete(t)
            body = body[:int(len(body) * 0.82)].rstrip() + "…"
        return self.cv.create_text(0, 0, text=body, anchor="nw", width=width,
                                   font=self.font, fill=BUBBLE_TXT, justify="left")

    def _draw_bubble(self, text: str):
        """Chamfered pixel box that grows upward from a fixed anchor by his head."""
        cv = self.cv
        u, pad = self.u, self.pad

        t = self._fit(text)
        bx0, by0, bx1, by1 = cv.bbox(t)

        # Horizontal: anchor the bubble's LEFT edge just left of his head, so the
        # tail always lands on him. The old code right-aligned every bubble to
        # the canvas edge, which is invisible for a wide one but strands a short
        # message — "...." especially — hundreds of pixels away with its tail
        # pointing at nothing. A bubble too wide to fit from there slides back
        # left, and the tail clamp below still finds his head.
        want_x0 = self.tail_tip_x - 3 * u
        outer_w = (bx1 - bx0) + 2 * pad
        x0_target = max(2 * u, min(want_x0, self.W - outer_w - 2 * u))
        dx = (x0_target + pad) - bx0

        dy = (self.anchor_bottom - pad) - by1
        cv.move(t, dx, max(dy, (u * 3) - by0))
        tx0, ty0, tx1, ty1 = cv.bbox(t)

        x0, y0 = tx0 - pad, ty0 - pad
        x1, y1 = tx1 + pad, ty1 + pad

        # a bubble narrower than its own tail looks broken — "...." is exactly
        # that short, so widen the box around the text rather than the text
        min_w = 9 * u
        if x1 - x0 < min_w:
            grow = (min_w - (x1 - x0)) / 2.0
            x0, x1 = x0 - grow, x1 + grow
        w, h = x1 - x0, y1 - y0

        # white fill
        self._blk(x0, y0, w, h, BUBBLE_BG)
        # black border bars, inset one unit at each corner -> chamfer
        self._blk(x0 + u, y0 - u, w - 2 * u, u, BLACK)
        self._blk(x0 + u, y1, w - 2 * u, u, BLACK)
        self._blk(x0 - u, y0 + u, u, h - 2 * u, BLACK)
        self._blk(x1, y0 + u, u, h - 2 * u, BLACK)
        for cxx, cyy in ((x0, y0), (x1 - u, y0), (x0, y1 - u), (x1 - u, y1 - u)):
            self._blk(cxx, cyy, u, u, BLACK)

        # stair-step tail, stepping down-left toward Clawd's head. It has to end
        # up over his head AND stay inside the bubble, so aim at the head and
        # clamp to the box.
        tail_x = max(x0 + u, min(self.tail_tip_x - u, x1 - 4 * u))
        for i in range(3):                       # outline pass
            self._blk(tail_x - (i + 1) * u, y1 + u + i * u,
                      (3 - i) * u + 2 * u, 2 * u, BLACK)
        for i in range(3):                       # white interior
            self._blk(tail_x - i * u, y1 + u + i * u, (3 - i) * u, u, BUBBLE_BG)
        # punch through the bubble's bottom border so the tail joins the body
        self._blk(tail_x, y1, 3 * u, u, BUBBLE_BG)

        cv.tag_raise(t)
        self._bubble_items.append(t)
        # _fit may have shrunk the shared Font; the answer box borrows it too
        if self.font.cget("size") != self.font_size:
            self.entry.config(font=(self.font.cget("family"), self.font_size))
