"""
Renders Clawd + a bubble to a PNG so the size can be judged without running him.

    xvfb-run -a python tests/preview_bubble.py out.png [bubble_width] [font_size]
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ui import KEY, Overlay          # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "preview.png"
bw = int(sys.argv[2]) if len(sys.argv) > 2 else 640
fs = int(sys.argv[3]) if len(sys.argv) > 3 else 16
msg = sys.argv[4] if len(sys.argv) > 4 else (
    "tidbit: the first transatlantic telegraph cable died in three weeks because "
    "the operators pushed 2000V through it to speed it up and cooked the "
    "gutta-percha insulation. whitehouse got fired over it :("
)

cfg = {"appearance": {"pixel_size": 9, "font_size": fs, "bubble_width": bw,
                      "bubble_max_height": 460, "auto_dpi_scale": False}}
o = Overlay(cfg, lambda: None, lambda e: None, lambda t: None)
o.place(0, 0)
o.say(msg, 60, time.time())
o.render(0.07, time.time(), "curious")
o.root.update()

import mss                     # noqa: E402
from PIL import Image          # noqa: E402

with mss.mss() as sct:
    raw = sct.grab({"left": 0, "top": 0, "width": o.W, "height": o.H})
    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

# paint the transparency key as a mock desktop so it reads like the real thing
key = tuple(int(KEY[i:i + 2], 16) for i in (1, 3, 5))
px = img.load()
for y in range(img.height):
    for x in range(img.width):
        if px[x, y] == key:
            px[x, y] = (38, 40, 46)

img.save(out)
print(f"{out}  {o.W}x{o.H}  bubble_width={o.bubble_w} font={o.font_size}")
o.root.destroy()
