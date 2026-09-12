"""
Renders Clawd's animation frames to a PNG contact sheet, with no display needed.

    python tests/preview_anim.py out.png

Each row is one state, each column one frame, left to right in playback order.
Handy for checking that the walk cycle actually reads as walking before you go
and stare at the real thing.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw        # noqa: E402

from core.sprite import GRID_H, GRID_W, Clawd   # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "clawd_anim.png"
CELL, COLS = 7, 8


class FakeCanvas:
    """Just enough Tk Canvas for Clawd.draw() to render into a PIL image."""

    def __init__(self, draw):
        self.draw = draw

    def create_rectangle(self, x0, y0, x1, y1, fill="", outline=""):
        if fill and x1 > x0 and y1 > y0:
            self.draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=fill)
        return 0

    def delete(self, _i):
        pass


ROWS = [
    ("walk right", "neutral", True, 1),
    ("walk left", "neutral", True, -1),
    ("neutral", "neutral", False, 1),
    ("focus", "focus", False, 1),
    ("happy", "happy", False, 1),
    ("proud", "proud", False, 1),
    ("curious", "curious", False, 1),
    ("annoyed", "annoyed", False, 1),
    ("disappointed", "disappointed", False, 1),
    ("concerned", "concerned", False, 1),
    ("sleepy", "sleepy", False, 1),
    ("quiz", "quiz", False, 1),
]

cw = (GRID_W + 14) * CELL
chh = (GRID_H + 11) * CELL
img = Image.new("RGB", (cw * COLS, chh * len(ROWS)), (32, 34, 42))
d = ImageDraw.Draw(img)
cv = FakeCanvas(d)

for r, (label, mood, walking, facing) in enumerate(ROWS):
    if r % 2:
        d.rectangle([0, r * chh, img.width, (r + 1) * chh - 1], fill=(38, 40, 49))
    c = Clawd(cv, 0, 0, CELL)
    c.set_mood(mood)
    c.walking = walking
    c._was_walking = walking
    c.facing = facing
    for f in range(COLS):
        c.ox = f * cw + 7 * CELL
        c.oy = r * chh + 7 * CELL
        c.frame = f
        c.draw()
    d.text((4, r * chh + 3), label, fill=(200, 205, 215))

img.save(out)
print(f"{out}  {img.size[0]}x{img.size[1]}  {len(ROWS)} states x {COLS} frames")
