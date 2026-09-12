"""
He must never be able to walk off the monitor.

If he does there is no way back: the window is borderless, transparent and
click-through, so you cannot right-click him, and there is no tray icon. The
only fix would be editing config.json by hand or killing the process.

    xvfb-run -a python tests/test_onscreen.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import app as appmod, capture, dpi, watcher     # noqa: E402
from core.motion import BLOCK, FOLLOW, HOME, PATROL, Motion   # noqa: E402
from core.sprite import GRID_H, GRID_W                    # noqa: E402
from core.ui import Overlay                               # noqa: E402
from core.watcher import Activity                         # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


watcher.foreground = lambda: Activity(title="t", process="chrome.exe", rect=(0, 0, 900, 700))
capture.available = lambda: False
capture.signature = lambda *a, **k: None
appmod._save_json = lambda *a, **k: None

SCREEN = (0, 0, 1920, 1080)
dpi.virtual_screen = lambda: SCREEN


def overlay(size="normal", cell=18, font=32):
    """A Clawd sized like a 200%-scaled display, where the bug showed up."""
    cfg = {"appearance": {"pixel_size": cell, "font_size": font, "bubble_width": 1280,
                          "bubble_max_height": 920, "auto_dpi_scale": False,
                          "size": size}}
    return Overlay(cfg, lambda: None, lambda e: None, lambda t: None)


o = overlay()
L, T, R, B = SCREEN
print(f"\n--- the window is {o.W}x{o.H} but he is only "
      f"{GRID_W * o.cell:.0f}x{GRID_H * o.cell:.0f} of it ---")
ok("most of the window is empty space above him",
   o.CLAWD_OY > GRID_H * o.cell * 2, f"CLAWD_OY={o.CLAWD_OY}")

print("\n--- the window clamp ---")
extremes = [(-99999, -99999), (99999, 99999), (0, 99999), (99999, 0),
            (860, -430), (0, 0), (-99999, 99999)]
for x, y in extremes:
    cx, cy = o._clamp(x, y)
    sl, st, sr, sb = o.sprite_rect(cx, cy)
    ok(f"clamp({x},{y}) keeps him visible",
       sl >= L - 1 and st >= T - 1 and sr <= R + 1 and sb <= B + 1,
       f"sprite {sl:.0f},{st:.0f} .. {sr:.0f},{sb:.0f}")

ok("on_screen agrees with the clamp", o.on_screen(*o._clamp(0, 99999)))
ok("and spots a genuinely lost Clawd", not o.on_screen(0, 99999))

print("\n--- a saved position from the broken build heals itself ---")
for bad in ([0, 3000], [5000, 0], [-4000, -4000]):
    o.cfg["appearance"]["position"] = bad
    x, y = o._saved_pos()
    ok(f"startup rescues {bad}", o.on_screen(x, y), f"-> {x},{y}")

print("\n--- he stays on screen ---")
x, y = o._clamp(99999, 99999)
sl, st, sr, sb = o.sprite_rect(x, y)
ok("bottom-right corner is reachable and visible",
   sr <= R + 1 and sb <= B + 1 and sl >= L - 1 and st >= T - 1,
   f"{sl:.0f},{st:.0f} .. {sr:.0f},{sb:.0f}")
hx, hy = o.home_corner()
ok("home corner is on screen", o.on_screen(hx, hy), f"{hx},{hy}")

print("\n--- the walking clamp ---")
m = Motion({}, (o.CLAWD_OX, o.CLAWD_OY), (o.W, o.H), (R - L, B - T),
           sprite_size=(GRID_W * o.cell, GRID_H * o.cell), screen_rect=SCREEN)
for x, y in extremes:
    cx, cy = m._clamp(x, y)
    sl, st = cx + m.ox, cy + m.oy
    ok(f"motion clamp({x},{y}) keeps him visible",
       sl >= L - 1 and st >= T - 1 and sl + m.spw <= R + 1 and st + m.sph <= B + 1,
       f"sprite {sl:.0f},{st:.0f}")

print("\n--- a minimised window must not drag him into the void ---")
MINIMISED = (-32000, -32000, -31840, -31970)     # what Windows actually reports
ok("a minimised rect is rejected", m._sane_rect(MINIMISED) is None)
ok("so is a degenerate one", m._sane_rect((10, 10, 12, 12)) is None)
ok("so is garbage", m._sane_rect(("a", "b", "c", "d")) is None)
ok("so is None", m._sane_rect(None) is None)
ok("a real window is kept", m._sane_rect((100, 100, 900, 700)) == (100, 100, 900, 700))

m.start_at(*o._clamp(400, 400))
for mode in (BLOCK, PATROL, FOLLOW):
    m.set_mode(mode, MINIMISED)
    for _ in range(200):                          # plenty of time to walk away
        x, y = m.update(0.07)
    sl, st = x + m.ox, y + m.oy
    ok(f"{mode} at a minimised window still leaves him on screen",
       L - 1 <= sl and st >= T - 1 and sl + m.spw <= R + 1 and st + m.sph <= B + 1,
       f"sprite {sl:.0f},{st:.0f}")

print("\n--- and through a real chase, from every corner ---")
for start in ((0, 0), (R, B), (0, B), (R, 0)):
    m.start_at(*o._clamp(*start))
    for rect, mode in (((1500, 800, 1900, 1050), BLOCK),
                       ((20, 20, 1900, 300), PATROL),
                       ((0, 0, 1920, 1080), BLOCK)):
        m.set_mode(mode, rect)
        worst = None
        for _ in range(160):
            x, y = m.update(0.07)
            sl, st = x + m.ox, y + m.oy
            if not (L - 1 <= sl and st >= T - 1
                    and sl + m.spw <= R + 1 and st + m.sph <= B + 1):
                worst = (sl, st)
        ok(f"from {start} chasing {mode} he stays visible", worst is None, str(worst))

o.root.destroy()

print("\n--- the app rescues him if anything ever slips through ---")
a = appmod.App()
a.ui.place(0, 20000)                              # simulate him being lost
ok("he is off screen", not a.ui.on_screen())
for _ in range(10):
    a.last_tick = a.last_tick - 0.07
    a.frame()
ok("the frame loop brings him back on its own", a.ui.on_screen(),
   str(a.ui.sprite_rect()))
a.rescue("test")
ok("an explicit rescue puts him somewhere visible", a.ui.on_screen(),
   str(a.ui.sprite_rect()))
ok("and writes that position back to config",
   a.ui.on_screen(*a.cfg["appearance"]["position"]),
   str(a.cfg["appearance"].get("position")))

ok("motion knows his sprite size",
   (a.motion.spw, a.motion.sph) == (a.ui.clawd.width_px, a.ui.clawd.height_px))

print("\n--- and he never parks behind the taskbar ---")
# The bug: screen_bounds() is every pixel that exists, taskbar strip included,
# so the bottom-right corner computed from it put him UNDER the tray — painted
# over, invisible, and with nothing left to right-click.
TASKBAR_H = 72
WORK = (SCREEN[0], SCREEN[1], SCREEN[2], SCREEN[3] - TASKBAR_H)
dpi.work_area = lambda *a, **k: WORK

o2 = overlay()
hx, hy = o2.home_corner()
sl, st, sr, sb = o2.sprite_rect(hx, hy)
ok("his home corner clears the taskbar", sb <= WORK[3],
   f"sprite bottom {sb:.0f} vs work area bottom {WORK[3]}")
ok("and is still hard against the bottom-right", sb > WORK[3] - 4 * o2.cell,
   f"{sb:.0f} vs {WORK[3] - 4 * o2.cell:.0f}")
ok("and inside the right edge", sr <= WORK[2], f"{sr:.0f} vs {WORK[2]}")

x, y = o2._clamp(99999, 99999)
sl, st, sr, sb = o2.sprite_rect(x, y)
ok("dragging him off the bottom lands him above the taskbar too", sb <= WORK[3],
   f"{sb:.0f} vs {WORK[3]}")

# a sprite sitting entirely inside the taskbar strip is a LOST Clawd, even
# though every pixel of him is technically on the desktop
buried_y = int(WORK[3] + 8 - o2.CLAWD_OY)
ok("a Clawd buried in the taskbar counts as off screen",
   not o2.on_screen(x, buried_y),
   str(o2.sprite_rect(x, buried_y)))
ok("but one merely near the bottom does not", o2.on_screen(*o2.home_corner()))
ok("usable bounds never exceed the real desktop",
   o2.usable_bounds()[3] <= SCREEN[3] and o2.usable_bounds()[2] <= SCREEN[2],
   str(o2.usable_bounds()))

dpi.work_area = lambda *a, **k: None
ok("with no work area available it falls back to the whole desktop",
   o2.usable_bounds() == SCREEN, str(o2.usable_bounds()))
o2.root.destroy()

a.ui.root.destroy()
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
