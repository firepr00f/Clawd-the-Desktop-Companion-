"""
The tray icon on its own, with no Clawd behind it.

Run this when the icon misbehaves: it is the same core/tray.py the app uses,
but nothing else is running, so whatever goes wrong is the tray's fault and the
traceback says so instead of vanishing into a log line.

    python tests/preview_tray.py

A small window appears with the current state in it. Look in the notification
area (open the overflow arrow — Windows hides new icons there until you drag
them out): left-click the icon to toggle, right-click for the menu. Every event
is printed here as it happens.
"""

import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import dpi, tray                                  # noqa: E402

if not tray.available():
    sys.exit("the notification area is Windows-only — nothing to preview here")

dpi.enable()

root = tk.Tk()
root.title("Clawd tray preview")
root.geometry("380x150")
label = tk.Label(root, text="starting…", font=("Segoe UI", 11), justify="left")
label.pack(expand=True, padx=16, pady=16)

state = {"hidden": False, "n": 0}


def show(what):
    state["n"] += 1
    print(f"{state['n']:3}  {what}", flush=True)
    label.config(text=f"hidden: {state['hidden']}\nlast event: {what}\n\n"
                      f"left-click the icon to toggle,\nright-click it for the menu")


def toggle():
    state["hidden"] = not state["hidden"]
    show("toggle -> " + ("hidden" if state["hidden"] else "visible"))


def pick(name):
    return lambda: show(f"menu: {name}")


def build():
    return [
        tray.Item("bring him back" if state["hidden"] else "hide him",
                  toggle, default=True),
        tray.SEP,
        tray.Item("talk to me", pick("talk")),
        tray.Item("quiz me", pick("quiz")),
        tray.Item("auto-watch: on", pick("auto-watch"), checked=True),
        tray.SEP,
        tray.Item("quit", lambda: (icon.close(), root.destroy())),
    ]


size = tray.icon_bits(16)
print(f"icon: {len(tray.ART[0])}x{len(tray.ART)} cells, {len(size)} bytes at 16px")

icon = tray.Tray(root, "Clawd (preview)", build, toggle, print)
print("icon added — check the notification area", flush=True)
show("ready")

root.protocol("WM_DELETE_WINDOW", lambda: (icon.close(), root.destroy()))
root.mainloop()
