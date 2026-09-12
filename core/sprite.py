"""
Clawd, drawn on a pixel grid.

Everything is cells, not curves: flat orange blocks, no anti-aliasing, no smooth
motion. Animation is frame swapping at a chunky few-fps the way a sprite sheet
would do it. Every offset in this file is a whole number of cells — nothing here
ever moves by a fraction of a pixel. He is always the same orange; mood shows in
the eyes, the motion, and what floats over his head.

Grid, in cells (18 wide, 11 tall):
    body   x 2..15, y 0..7      -- wide and flat
    arms   y 4..5, x 0..1 (left) and x 16..17 (right)
    legs   y 8..10 at x 3-4, 6-7, 10-11, 13-14
    eyes   2x2 blocks at x 5 / x 11, y 1
Anything with a negative y (anger marks, z's, question marks) floats above him.

Animation, v2. The old version was a 2-frame bob and a 2-frame leg swap, which
read as a stutter rather than a walk. Now:

  * a real 4-beat walk cycle -- contact, passing, contact, passing -- with the
    legs striding one cell forward and back, the body rising on the passing
    beats, and the arms swinging opposite the legs
  * squash on landing and stretch on push-off, one cell each, so starting and
    stopping have weight
  * he faces the way he is walking: the body leans one cell and the eyes shift
    one cell that way
  * per-mood idle loops of 4-8 frames instead of 2, so standing still is not
    a metronome
"""

from __future__ import annotations

# --- palette ----------------------------------------------------------------

CLAWD_ORANGE = "#D9775B"
PUZZLE = "#7A6C86"             # the confused question marks — its own colour
BLACK = "#141414"
WHITE = "#FFFFFF"

MOODS = ["neutral", "focus", "happy", "proud", "curious",
         "annoyed", "disappointed", "concerned", "sleepy", "quiz", "confused"]

# --- geometry ---------------------------------------------------------------

GRID_W, GRID_H = 18, 11

BODY = (2, 0, 14, 8)           # x, y, w, h
ARM_L = (0, 4, 2, 2)
ARM_R = (16, 4, 2, 2)
LEG_X = (3, 6, 10, 13)         # each leg is 2 cells wide
LEG_Y, LEG_H = 8, 3
ITEM_ORIGIN = (-10, 1)         # where the held item sits, in Clawd cells
ITEM_CELLS = 8                 # the item occupies 8 Clawd cells across

# frame period per mood, in seconds
TEMPO = {
    "neutral": 0.40, "focus": 0.40, "happy": 0.16, "proud": 0.20,
    "curious": 0.26, "annoyed": 0.11, "disappointed": 0.55,
    "concerned": 0.32, "sleepy": 0.70, "quiz": 0.24, "confused": 0.30,
}
WALK_TEMPO = 0.10              # the walk cycle runs at its own faster beat


def _mirror(block):
    x, y, w, h = block
    return (GRID_W - x - w, y, w, h)


# Left-eye pixel patterns; the right eye is the mirror image.
EYES = {
    "open":    [(5, 1, 2, 2)],
    "wide":    [(5, 1, 2, 3)],
    "smile":   [(5, 2, 1, 1), (6, 1, 1, 1), (7, 2, 1, 1)],       # ^
    "half":    [(5, 1, 2, 1)],                                    # mid-blink
    "shut":    [(5, 2, 2, 1)],
    "angry":   [(5, 1, 2, 1), (7, 2, 1, 1), (5, 3, 2, 1)],       # inner corner down
    "sad":     [(7, 1, 1, 1), (5, 2, 2, 1), (5, 3, 2, 1)],       # inner corner up
    "worried": [(7, 1, 1, 1), (5, 2, 2, 1)],
    "swirl":   [(5, 1, 3, 1), (7, 2, 1, 1), (5, 3, 3, 1)],       # dizzy S
    # Narrowed, not shut. A cell WIDER than the open eye and only one tall, so
    # it reads as squeezed rather than closed, with the lid dropping at the
    # inner corner — which is the difference between "asleep" and "hang on".
    "squint":  [(5, 2, 3, 1), (7, 1, 1, 1)],
}

EYE_FOR_MOOD = {
    "neutral": "open", "focus": "open", "happy": "smile", "proud": "smile",
    "curious": "wide", "annoyed": "angry", "disappointed": "sad",
    "concerned": "worried", "sleepy": "shut", "quiz": "swirl",
    "confused": "squint",
}

# --- idle loops -------------------------------------------------------------
# Each entry is a list of (dx, dy, arm, squash) — all whole cells.
#   dx/dy   move the whole body
#   arm     raises (-) or drops (+) both arms
#   squash  1 = one cell shorter and one cell wider, -1 = taller and narrower

IDLE = {
    "neutral":      [(0, 0, 0, 0), (0, 0, 0, 0), (0, -1, 0, 0), (0, -1, 0, 0),
                     (0, 0, 0, 0), (0, 0, 0, 0)],
    "focus":        [(0, 0, 0, 0), (0, 0, 0, 0), (0, -1, 0, 0), (0, 0, 0, 0)],
    "happy":        [(0, 0, 0, 1), (0, -1, -1, 0), (0, -2, -1, -1), (0, -1, -1, 0),
                     (0, 0, 0, 1), (0, 0, 0, 0)],
    "proud":        [(0, 0, -1, 0), (0, -1, -1, 0), (0, -1, -1, 0), (0, 0, -1, 0),
                     (0, 0, 0, 0), (0, 0, 0, 0)],
    "curious":      [(0, 0, 0, 0), (1, 0, 0, 0), (1, -1, 0, 0), (0, 0, 0, 0),
                     (-1, 0, 0, 0), (-1, -1, 0, 0)],
    "annoyed":      [(1, 0, 0, 0), (-1, 0, 0, 0), (1, 0, 0, 0), (-1, 0, 0, 0),
                     (0, 0, 0, 0), (0, 0, 0, 0)],
    "disappointed": [(0, 1, 1, 0), (0, 1, 1, 0), (0, 2, 1, 1), (0, 2, 1, 1),
                     (0, 1, 1, 0), (0, 1, 1, 0)],
    "concerned":    [(0, 0, 1, 0), (0, 0, 1, 0), (1, 0, 1, 0), (0, 0, 1, 0),
                     (0, 0, 1, 0), (-1, 0, 1, 0)],
    "sleepy":       [(0, 1, 1, 0), (0, 1, 1, 0), (0, 1, 1, 0), (0, 2, 1, 1),
                     (0, 2, 1, 1), (0, 2, 1, 1), (0, 1, 1, 0), (0, 1, 1, 0)],
    "quiz":         [(0, 0, 0, 0), (0, -1, 0, 0), (0, 0, 0, 0), (0, 0, -1, 0)],
    # Leaning one way, then the other, and never quite settling. No bob and no
    # arm movement: the whole gesture is him tilting at the thing he cannot
    # work out, which is why it is only ever dx.
    "confused":     [(0, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0),
                     (0, 0, 0, 0), (-1, 0, 0, 0), (-1, 0, 0, 0)],
}

# --- walk cycle -------------------------------------------------------------
# Four beats: contact, passing, contact, passing. `lift` is which pair of legs
# is off the ground (0 = legs 0&2, 1 = legs 1&3, None = both down), `stride` is
# how far the planted legs have slid back, in cells.

# `lift` is which pair of legs is off the ground, `tuck` is how many cells that
# pair pulls up. The legs sit 1 cell apart, so striding them sideways just fused
# them into a blob — the alternation reads far better as height.
WALK = [
    # (body_dy, squash, lift, tuck, arm_l, arm_r)
    (0,  1, 0,  2, -1,  1),      # contact: front pair tucked, weight down
    (-1, 0, None, 0,  0,  0),    # passing: rise, all four down
    (0,  1, 1,  2,  1, -1),      # contact: back pair tucked
    (-1, 0, None, 0,  0,  0),    # passing
]

# Picked up by the mouse: he kicks. Each leg becomes a short diagonal staircase
# reaching out and down, and the direction flips every frame, so the four of
# them scrabble at the air. The body itself never slides sideways — the kicking
# is in the legs, so he hangs off the cursor instead of wobbling with it. His
# mood, eyes and decorations are untouched — an annoyed Clawd being dragged is
# still an annoyed Clawd.
# (body_dx, body_dy, arm_l, arm_r, kick direction per leg)
FLAIL = [
    (0, -1, -1,  1, (-1, -1,  1,  1)),
    (0,  0,  1, -1, (1,  1, -1, -1)),
    (0, -1,  1,  1, (-1,  1, -1,  1)),
    (0,  0, -1, -1, (1, -1,  1, -1)),
]
FLAIL_TEMPO = 0.16             # a slow, deliberate scrabble, not a blur
KICK_STEPS = 2                 # cells each leg reaches diagonally — stubby


class Clawd:
    """Renders the pixel Clawd onto a Tk canvas. `cell` is the pixel size."""

    def __init__(self, canvas, ox: float, oy: float, cell: float = 9.0,
                 outline: bool = False):
        self.cv = canvas
        self.ox, self.oy = ox, oy
        self.cell = max(3.0, cell)
        self.outline = outline
        self.mood = "neutral"
        self.items: list[int] = []
        self.t = 0.0
        self.frame = 0
        self._next_frame = 0.0
        self._blink_at = 3.0
        self._blink_stage = 0          # 2 -> half, 1 -> shut, 0 -> open
        self.walking = False
        self._was_walking = False
        self.dragging = False          # held by the mouse right now
        self._land_until = 0.0         # squash-on-landing window
        self._push_until = 0.0         # stretch-on-push-off window
        self.facing = 1                # 1 = right, -1 = left
        self.held: list[str] | None = None
        self._hold_until = 0.0
        self.watching = 0.0            # >0 while a screen capture just happened
        self.boom_until = 0.0          # >0 while the fireworks are going off
        self.boom_seed = 0

    # ------------------------------------------------------------------

    def set_mood(self, mood: str):
        if mood not in EYE_FOR_MOOD:
            mood = "neutral"
        if mood != self.mood:
            self.mood = mood
            self.frame = 0
            self._next_frame = self.t

    def set_facing(self, dx: float):
        """Point him the way he's travelling. Ignores tiny jitter."""
        if dx > 1.5:
            self.facing = 1
        elif dx < -1.5:
            self.facing = -1

    def clear(self):
        for i in self.items:
            self.cv.delete(i)
        self.items.clear()

    def hold(self, grid: list[str] | None, seconds: float = 0.0):
        """Show an item beside him. seconds=0 keeps it until replaced."""
        self.held = grid
        self._hold_until = (self.t + seconds) if seconds else 0.0

    def flash_watching(self, seconds: float = 1.6):
        self.watching = self.t + seconds

    def fireworks(self, seconds: float = 4.5):
        """Set off pixel fireworks above him for `seconds`."""
        self.boom_until = self.t + max(0.5, seconds)
        self.boom_seed = int(self.t * 1000) % 997

    # ------------------------------------------------------------------

    def tick(self, dt: float):
        self.t += dt

        if self.walking != self._was_walking:
            if self.walking:
                self._push_until = self.t + 0.10      # stretch as he takes off
            else:
                self._land_until = self.t + 0.14      # squash as he plants
            self._was_walking = self.walking
            self.frame = 0
            self._next_frame = self.t

        if self._hold_until and self.t > self._hold_until:
            self.held = None
            self._hold_until = 0.0

        if self.dragging:
            period = FLAIL_TEMPO
        elif self.walking:
            period = WALK_TEMPO
        else:
            period = TEMPO.get(self.mood, 0.4)
        if self.t >= self._next_frame:
            self.frame += 1
            self._next_frame = self.t + period
            self._advance_blink()

        self.draw()

    def _advance_blink(self):
        """Blink is three frames — half, shut, open — so it reads as a blink."""
        if self._blink_stage:
            self._blink_stage -= 1
        elif self.t >= self._blink_at and self.mood != "sleepy":
            self._blink_stage = 2
            self._blink_at = self.t + 3.0 + (self.frame % 5)

    # ------------------------------------------------------------------

    def _rect(self, x, y, w, h, color):
        c = self.cell
        x0 = self.ox + x * c
        y0 = self.oy + y * c
        self.items.append(self.cv.create_rectangle(
            x0, y0, x0 + w * c, y0 + h * c, fill=color, outline=""))

    def _halo(self, blocks):
        """Half-cell white sticker outline behind the whole silhouette."""
        for (x, y, w, h) in blocks:
            self._rect(x - 0.5, y - 0.5, w + 1, h + 1, WHITE)

    # ------------------------------------------------------------------

    def _pose(self):
        """
        Work out this frame's offsets. Returns
        (dx, dy, arm_l, arm_r, squash, leg_offsets) — all whole cells.
        leg_offsets is one (dx, height, kick) per leg; a non-zero `kick` means
        draw that leg as a diagonal staircase in that direction.
        """
        f = self.frame

        if self.dragging:
            dx, dy, arm_l, arm_r, kicks = FLAIL[f % len(FLAIL)]
            return dx, dy, arm_l, arm_r, 0, [(0, LEG_H, k) for k in kicks]

        if self.walking:
            dy, squash, lift, tuck, arm_l, arm_r = WALK[f % len(WALK)]
            dx = self.facing                     # lean into the direction of travel
            legs = []
            for i in range(len(LEG_X)):
                tucked = lift is not None and (i % 2) == lift
                legs.append((0, max(1, LEG_H - tuck) if tucked else LEG_H, 0))
            return dx, dy, arm_l, arm_r, squash, legs

        loop = IDLE.get(self.mood, IDLE["neutral"])
        dx, dy, arm, squash = loop[f % len(loop)]

        # squash on landing / stretch on push-off override the idle loop
        if self.t < self._land_until:
            squash, dy = 1, dy + 1
        elif self.t < self._push_until:
            squash, dy = -1, dy - 1

        legs = [(0, LEG_H, 0)] * len(LEG_X)
        return dx, dy, arm, arm, squash, legs

    def draw(self):
        self.clear()
        m = self.mood
        dx, dy, arm_l, arm_r, squash, legs = self._pose()

        # squash: one cell shorter and one cell wider each side, and back again
        bx, by, bw, bh = BODY
        body = (bx - squash + dx, by + squash + dy, bw + 2 * squash, bh - squash)
        leg_y = LEG_Y + dy                       # legs follow the body, not the squash

        # arms ride the squashed body's edge, or they float off it when he
        # stretches (body narrows by a cell each side) and look detached
        blocks = [
            body,
            (ARM_L[0] + dx - squash, ARM_L[1] + dy + arm_l + squash,
             ARM_L[2], ARM_L[3]),
            (ARM_R[0] + dx + squash, ARM_R[1] + dy + arm_r + squash,
             ARM_R[2], ARM_R[3]),
        ]
        for i, lx in enumerate(LEG_X):
            off, h, kick = legs[i]
            if kick:
                # a staircase of 1-cell-tall blocks stepping outward and down
                for step in range(KICK_STEPS):
                    blocks.append((lx + dx + off + kick * step, leg_y + step, 2, 1))
            else:
                blocks.append((lx + dx + off, leg_y, 2, h))

        if self.outline:
            self._halo(blocks)
        for b in blocks:
            self._rect(*b, CLAWD_ORANGE)

        # eyes ride the squash and look the way he's going
        eye_dx = dx + (self.facing if self.walking else 0)
        eye_dy = dy + squash
        pattern = EYE_FOR_MOOD[m]
        if self._blink_stage == 2:
            pattern = "half"
        elif self._blink_stage == 1:
            pattern = "shut"
        for block in EYES[pattern]:
            for bxx, byy, bww, bhh in (block, _mirror(block)):
                self._rect(bxx + eye_dx, byy + eye_dy, bww, bhh, BLACK)

        self._decorate(m, self.frame, dx, dy)
        self._draw_held(dx, dy)
        if self.watching > self.t:
            self._draw_watching(self.frame, dx, dy)
        if self.boom_until > self.t:
            self._draw_fireworks(dx, dy)

    # ------------------------------------------------------------------

    def _draw_held(self, dx, dy):
        """
        The item, floating to his left at half-cell resolution.

        Item grids are 16x16 and each item-pixel is half a Clawd-cell, so the
        icon still spans ITEM_CELLS Clawd-cells — same footprint as the old
        8x8 set, four times the detail.
        """
        if not self.held:
            return
        from .items import PALETTE
        n = len(self.held)
        px = (ITEM_CELLS * self.cell) / float(n)          # item-pixel, in screen px
        ox = self.ox + (ITEM_ORIGIN[0] + dx) * self.cell
        oy = self.oy + (ITEM_ORIGIN[1] + dy) * self.cell
        bobble = self.cell / 2.0 if (self.frame % 2) else 0.0
        for r, row in enumerate(self.held):
            y0 = oy + r * px + bobble
            for c, ch in enumerate(row):
                color = PALETTE.get(ch)
                if not color:
                    continue
                x0 = ox + c * px
                self.items.append(self.cv.create_rectangle(
                    x0, y0, x0 + px, y0 + px, fill=color, outline=""))

    # Three shells, staggered so they don't all pop at once. Each is
    # (centre x, centre y, colour, when it launches) in cells / seconds.
    # Up and to the LEFT: the speech bubble is anchored above his head and is
    # drawn after him, so shells placed there would just be covered by it.
    SHELLS = (
        (-7, -11, "#F2C14E", 0.00),
        (-2, -16, "#5B8FD9", 0.55),
        (3, -20, "#E88BB0", 1.10),
    )
    # A burst, ring by ring: (radius, cells lit at that radius)
    BURST = ((1, ((0, -1), (1, 0), (0, 1), (-1, 0))),
             (2, ((0, -2), (2, 0), (0, 2), (-2, 0), (1, -1), (1, 1), (-1, 1), (-1, -1))),
             (3, ((0, -3), (3, 0), (0, 3), (-3, 0), (2, -2), (2, 2), (-2, 2), (-2, -2))),
             (4, ((1, -4), (-1, -4), (4, 1), (4, -1), (1, 4), (-1, 4), (-4, 1), (-4, -1))))

    def _draw_fireworks(self, dx, dy):
        """
        Pixel fireworks over his head.

        Rings of single cells expanding outward, one ring per animation frame —
        no curves, no fading, no sub-pixel motion. A shell that has expanded past
        its last ring leaves a few sparks behind, then relights on the next loop
        so it keeps going for the whole window.
        """
        span = 1.7                                  # seconds per shell cycle
        for cx, cy, colour, delay in self.SHELLS:
            phase = (self.t - delay) % span
            if phase < 0:
                continue
            step = int(phase / 0.14)                # ring index, ~7 rings/second
            if step == 0:                           # the launch: a single spark
                self._rect(cx + dx, cy + dy + 2, 1, 2, colour)
                continue
            if step > len(self.BURST) + 2:
                continue
            if step <= len(self.BURST):
                _, cells = self.BURST[step - 1]
                for ox, oy in cells:
                    self._rect(cx + ox + dx, cy + oy + dy, 1, 1, colour)
                if step > 1:                        # a dimmer trailing ring
                    _, prev = self.BURST[step - 2]
                    for ox, oy in prev[::2]:
                        self._rect(cx + ox + dx, cy + oy + dy, 1, 1, WHITE)
            else:                                   # embers drifting down
                drop = step - len(self.BURST)
                for ox in (-3, 0, 3):
                    self._rect(cx + ox + dx, cy + 4 + drop + dy, 1, 1, colour)

    def _draw_watching(self, f, dx, dy):
        """A blinking eye so a screen capture is never invisible to you."""
        if f % 2:
            return
        for bx, by, bw in ((5, -3, 4), (4, -2, 1), (9, -2, 1), (5, -1, 4)):
            self._rect(bx + dx, by + dy, bw, 1, "#5B8FD9")
        self._rect(6 + dx, -2 + dy, 2, 1, "#141414")

    # ------------------------------------------------------------------

    def _decorate(self, m, f, dx, dy):
        if m == "annoyed" and f % 2 == 0:
            for bx, by in ((13, -3), (15, -3), (14, -2), (13, -1), (15, -1)):
                self._rect(bx + dx, by + dy, 1, 1, "#D6402F")

        elif m == "disappointed":
            self._rect(14 + dx, 1 + (f % 4) + dy, 1, 1, "#6FA0D8")

        elif m == "concerned":
            self._rect(14 + dx, 1 + dy, 1, 2, "#8FBEE8")

        elif m in ("happy", "proud"):
            lift = -1 if f % 2 else 0
            self._rect(18 + dx, 4 + dy + lift, 2, 1, BLACK)          # wand
            gold = ("#F2C14E", "#E8B03A")
            for i, (sx, sy) in enumerate(
                    ((20, 2), (22, 2), (21, 3), (20, 4), (22, 4), (21, 1), (23, 3))):
                if (i + f) % 3:
                    self._rect(sx + dx, sy + dy + lift, 1, 1, gold[i % 2])

        elif m == "sleepy":
            step = f % 3
            zx, zy = 15 + step, -1 - step * 2
            for bx, by, bw in ((zx, zy, 2), (zx + 1, zy + 1, 1), (zx, zy + 2, 2)):
                self._rect(bx + dx, by + dy, bw, 1, "#6E5A52")

        elif m == "confused":
            # A big question mark that rocks a cell side to side, and a smaller
            # one that pops in and out beside it. Two of them, moving at
            # different times, is what separates "I don't follow" from the
            # quiz mark's single steady "answer me".
            tilt = (0, 1, 1, 0)[f % 4]
            for bx, by, bw in ((2 + tilt, -5, 2), (4 + tilt, -5, 1),
                               (4 + tilt, -4, 1), (3 + tilt, -3, 1),
                               (3 + tilt, -2, 1), (3 + tilt, 0, 1)):
                self._rect(bx + dx, by + dy, bw, 1, PUZZLE)
            if f % 2 == 0:
                # A second, smaller one — the same shape, not loose dots, or it
                # reads as debris rather than a question.
                for bx, by, bw in ((6 + tilt, -4, 2), (7 + tilt, -3, 1),
                                   (6 + tilt, -2, 1), (6 + tilt, 0, 1)):
                    self._rect(bx + dx, by + dy, bw, 1, PUZZLE)

        elif m == "quiz" and f % 4 != 3:
            for bx, by, bw in ((14, -4, 3), (16, -3, 1), (15, -2, 2),
                               (15, -1, 1), (15, 1, 1)):
                self._rect(bx + dx, by + dy, bw, 1, BLACK)

    # ------------------------------------------------------------------

    @property
    def width_px(self) -> float:
        return GRID_W * self.cell

    @property
    def height_px(self) -> float:
        return GRID_H * self.cell
