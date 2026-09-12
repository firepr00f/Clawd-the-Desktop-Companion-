"""Renders the real overlay window (Clawd + bubble) to clawd_window.png."""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui import Overlay, W, H, KEY

msg = sys.argv[1] if len(sys.argv) > 1 else \
    "12 minutes of skibidi. how old are you gang :("
mood = sys.argv[2] if len(sys.argv) > 2 else "disappointed"

ov = Overlay({"appearance": {"scale": 1.0, "font_size": 10, "position": [0, 0]}},
             lambda: None, lambda e: None, lambda t: None)
ov.root.attributes("-topmost", True)
try:
    ov.root.attributes("-transparentcolor", "")
except Exception:
    pass
ov.cv.configure(bg="#EDE6DE")          # stand-in for "whatever is behind him"
ov.root.configure(bg="#EDE6DE")
if len(sys.argv) > 4:
    from core.items import ITEMS
    ov.clawd.hold(ITEMS.get(sys.argv[4]))
ov.say(msg, 999, time.time())
ov.render(0.0, time.time(), mood)
ov.root.update()
ov.root.update_idletasks()

from PIL import ImageGrab
out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                   sys.argv[3] if len(sys.argv) > 3 else "clawd_window.png"))
ImageGrab.grab(xdisplay=os.environ.get("DISPLAY")).crop((0, 0, W, H)).save(out)
print("wrote", out)
