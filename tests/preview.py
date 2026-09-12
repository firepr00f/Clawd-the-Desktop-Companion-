"""
Renders a contact sheet of every Clawd mood (2 animation frames each) to
clawd_moods.png. Handy for tweaking sprite.py without waiting for a real mood.

    python tests/preview.py
"""
import os, sys, tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.sprite import Clawd, MOODS

CAPTIONS = {
    "neutral": "idle, watching",
    "focus": "you're studying",
    "happy": "20 min streak",
    "proud": "45+ min streak",
    "curious": "what's that tab",
    "annoyed": "5 min of YouTube",
    "disappointed": "12 min of YouTube",
    "concerned": "25 min — softens",
    "sleepy": "you're afk",
    "quiz": "pop quiz",
}

CELL = 7
COLS, CELL_W, CELL_H = 4, 350, 168

root = tk.Tk()
W, H = COLS * CELL_W, 3 * CELL_H
cv = tk.Canvas(root, width=W, height=H, bg="#F4EFE9", highlightthickness=0)
cv.pack()

for i, mood in enumerate(MOODS):
    col, row = i % COLS, i // COLS
    ox = col * CELL_W + 22
    oy = row * CELL_H + 46
    for frame, shift in ((0, 0), (1, 176)):        # two frames, side by side
        c = Clawd(cv, ox + shift, oy, CELL)
        c.set_mood(mood)
        c.frame = frame
        c.draw()
    cv.create_text(col * CELL_W + CELL_W / 2 - 12, row * CELL_H + 132, text=mood,
                   font=("DejaVu Sans Mono", 10, "bold"), fill="#2C2119")
    cv.create_text(col * CELL_W + CELL_W / 2 - 12, row * CELL_H + 148,
                   text=CAPTIONS[mood], font=("DejaVu Sans", 8), fill="#7A6A5C")

root.update()
root.update_idletasks()

out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "clawd_moods.png"))
try:
    from PIL import ImageGrab
    ImageGrab.grab(xdisplay=os.environ.get("DISPLAY")).crop((0, 0, W, H)).save(out)
    print("wrote", out)
except Exception as e:
    print("screen grab unavailable:", e)
    root.mainloop()
