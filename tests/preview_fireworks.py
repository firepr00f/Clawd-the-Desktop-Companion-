"""
The full-screen fireworks, on their own.

Nothing else runs — no watcher, no API, no Clawd — so this works even when the
rest of the app does not, and whatever goes wrong here is the fireworks' fault.

    python tests/preview_fireworks.py            :: one show, with sound
    python tests/preview_fireworks.py --silent   :: no sound
    python tests/preview_fireworks.py --loop     :: over and over, to watch it

A small window appears with a button. The show itself covers the whole desktop
and is click-through, so you can keep using the machine underneath it.
"""

import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import dpi, fireworks                            # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUND = os.path.join(HERE, "assets", "firework_sound.mp3")

silent = "--silent" in sys.argv
loop = "--loop" in sys.argv

dpi.enable()
root = tk.Tk()
root.title("Clawd fireworks preview")
root.geometry("300x170")

bounds = dpi.virtual_screen() or (0, 0, root.winfo_screenwidth(),
                                  root.winfo_screenheight())
show = fireworks.Fireworks(root, bounds, 14.0, print)

print(f"desktop {bounds}   cell {show.cell}")
print(f"sound   {SOUND}\n        exists: {os.path.exists(SOUND)}"
      + ("   (--silent)" if silent else ""))

n = {"i": 0}


def go():
    n["i"] += 1
    print(f"show {n['i']}", flush=True)
    show.show(seconds=6.0, count=9, sound="" if silent else SOUND)
    if loop:
        root.after(9000, go)


tk.Label(root, text="Clawd fireworks", font=("Segoe UI", 12)).pack(pady=(18, 4))
tk.Label(root, text="the show covers the whole screen\nand clicks pass through it",
         font=("Segoe UI", 9), fg="#666").pack()
tk.Button(root, text="set them off", command=go, padx=18, pady=6).pack(pady=12)

root.after(600, go)
root.protocol("WM_DELETE_WINDOW", lambda: (show.stop(), root.destroy()))
root.mainloop()
