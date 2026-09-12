"""
The notification-area icon.

Clawd has no title bar and no taskbar button, so right-clicking the sprite is
normally the only way to reach him — and when he is behind a maximised window
or on a monitor you unplugged, there is nothing to right-click.

The icon talks to Shell_NotifyIcon through ctypes, with no third-party package
to forget to install and no thread to marshal across: it owns a message-only
window and the animation loop pumps it. The Win32 calls themselves cannot run
here, so `sys.platform` stands in for Windows and user32/shell32 are replaced
with recording stand-ins. What that covers: the icon really is the sprite, a
click really opens the menu, the pump takes only its own window's messages,
the icon is removed on quit, and every failure is survivable.

    xvfb-run -a python tests/test_tray.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import app as appmod, capture, lang, tray, watcher    # noqa: E402
from core.sprite import BLACK, CLAWD_ORANGE, GRID_H, GRID_W     # noqa: E402
from core.watcher import Activity                               # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


watcher.foreground = lambda: Activity(title="KLAS - 광운대학교", process="chrome.exe",
                                      rect=(0, 0, 1200, 800))
watcher.cursor_pos = lambda: (640, 480)
capture.available = lambda: False
capture.signature = lambda *a, **k: None
appmod._save_json = lambda *a, **k: None

RGB_ORANGE = tuple(int(CLAWD_ORANGE[i:i + 2], 16) for i in (1, 3, 5))
RGB_BLACK = tuple(int(BLACK[i:i + 2], 16) for i in (1, 3, 5))

print("\n--- the icon is the sprite, not a redrawing of it ---")
img = tray.icon_image(64)
ok("it is drawn at the size asked for", img.size == (64, 64), str(img.size))
ok("with transparency around him", img.mode == "RGBA", img.mode)
px = img.load()
cell = 64 / GRID_W
oy = (64 - GRID_H * cell) / 2


def at(cx, cy):
    return px[int((cx + 0.5) * cell), int(oy + (cy + 0.5) * cell)][:3]


def alpha(cx, cy):
    return px[int((cx + 0.5) * cell), int(oy + (cy + 0.5) * cell)][3]


ok("his body is Clawd orange", at(8, 4) == RGB_ORANGE, str(at(8, 4)))
ok("his eyes are in the sprite's eye cells",
   at(5, 1) == RGB_BLACK and at(12, 1) == RGB_BLACK, f"{at(5, 1)} {at(12, 1)}")
ok("the eyes are mirrored, like the sprite's", at(5, 1) == at(12, 1))
ok("he has arms out to the sides",
   at(0, 4) == RGB_ORANGE and at(17, 4) == RGB_ORANGE)
ok("and four legs under him",
   all(at(lx, 9) == RGB_ORANGE for lx in (3, 6, 10, 13)),
   str([at(lx, 9) for lx in (3, 6, 10, 13)]))
ok("with a gap between each pair of legs", at(5, 9) != RGB_ORANGE, str(at(5, 9)))
ok("above and below him is see-through", alpha(8, -1) == 0 if oy > cell else True)
ok("it survives every size Windows asks for",
   all(tray.icon_image(n).size == (n, n) for n in (16, 20, 24, 32, 48, 256)))


# ---- stand-ins for user32 / shell32 ----------------------------------------

class FakeUser32:
    def __init__(self):
        self.registered, self.icons, self.destroyed = [], [], []
        self.queue = []                  # (hwnd, message, wparam, lparam)
        self.proc = None

    def RegisterClassW(self, ref):
        self.registered.append(ref)
        return 1

    def CreateWindowExW(self, *a):
        return 4242

    def LoadImageW(self, *a):
        self.icons.append(a)
        return 77

    def LoadIconW(self, *a):
        return 1

    def DestroyWindow(self, hwnd):
        self.destroyed.append(hwnd)
        return 1

    def DefWindowProcW(self, *a):
        return 0

    def RegisterWindowMessageW(self, name):
        return 0xC001                    # what Windows gives TaskbarCreated

    def GetSystemMetrics(self, which):
        return 16

    def PeekMessageW(self, ref, hwnd, lo, hi, flags):
        # only ever asked for OUR window's messages — Tk's queue is untouched
        mine = [m for m in self.queue if m[0] == hwnd]
        if not mine:
            return 0
        m = mine[0]
        self.queue.remove(m)
        ref._obj.hWnd, ref._obj.message = m[0], m[1]
        ref._obj.wParam, ref._obj.lParam = m[2], m[3]
        return 1

    def TranslateMessage(self, ref):
        return 1

    def DispatchMessageW(self, ref):
        m = ref._obj
        if self.proc:
            self.proc(m.hWnd, m.message, m.wParam, m.lParam)
        return 0


class FakeShell32:
    def __init__(self):
        self.calls = []
        self.refuse = False

    def Shell_NotifyIconW(self, action, ref):
        self.calls.append((action, ref._obj.szTip, ref._obj.hIcon))
        return 0 if self.refuse else 1


def install(user32=None, shell32=None):
    """Point one Tray at fake Win32, without touching the real platform."""
    import ctypes
    u = user32 or FakeUser32()
    sh = shell32 or FakeShell32()
    real_windll = ctypes.windll if hasattr(ctypes, "windll") else None

    class FakeWindll:
        pass

    fw = FakeWindll()
    fw.user32, fw.shell32 = u, sh
    fw.kernel32 = type("K", (), {"GetModuleHandleW": staticmethod(lambda _n: 1)})()
    ctypes.windll = fw
    if not hasattr(ctypes, "WINFUNCTYPE"):
        ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE
    if not hasattr(ctypes.wintypes if False else object, "x"):
        pass
    return u, sh, real_windll


print("\n--- off Windows it is simply absent ---")
tray._why = ""
t = tray.Tray(lambda: None)
ok("start() says no", not t.start())
ok("and explains itself", "Windows" in tray.why(), tray.why())
ok("pumping is a no-op", t.pump() == 0)
t.stop()                                 # must be safe having never started

print("\n--- on Windows it registers, creates and adds ---")
import ctypes                                                  # noqa: E402
import ctypes.wintypes as _wt                                  # noqa: E402
for name, size in (("HICON", ctypes.c_void_p), ("HBRUSH", ctypes.c_void_p),
                   ("WCHAR", ctypes.c_wchar), ("HINSTANCE", ctypes.c_void_p),
                   ("HANDLE", ctypes.c_void_p), ("LPCWSTR", ctypes.c_wchar_p)):
    if not hasattr(_wt, name):
        setattr(_wt, name, size)
if not hasattr(ctypes, "WINFUNCTYPE"):
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

real_platform = sys.platform
sys.platform = "win32"
u, sh, real_windll = install()

clicks = []
t = tray.Tray(lambda: clicks.append(1), log=lambda *a: None)
started = t.start()
ok("it starts", started, tray.why())
ok("a window class was registered", len(u.registered) == 1)
ok("a message-only window exists", t.hwnd == 4242)
ok("an icon was loaded from a real .ico", len(u.icons) == 1)
ok("and Shell_NotifyIcon was told to ADD it",
   sh.calls and sh.calls[0][0] == tray.NIM_ADD, str([c[0] for c in sh.calls]))
ok("with a tooltip", sh.calls and sh.calls[0][1] == "Clawd", str(sh.calls[0][1]))
ok("the window procedure is held, not left to the collector", t._proc is not None)

print("\n--- a click opens the menu ---")
u.proc = t._proc
u.queue.append((t.hwnd, tray.WM_TRAY, 0, tray.WM_RBUTTONUP))
ok("the pump delivers it", t.pump() == 1)
ok("and the menu was asked for", clicks == [1], str(clicks))

clicks.clear()
u.queue.append((t.hwnd, tray.WM_TRAY, 0, tray.WM_LBUTTONUP))
t.pump()
ok("left click works too", clicks == [1], str(clicks))

clicks.clear()
for _ in range(5):                       # a burst of the same intent
    u.queue.append((t.hwnd, tray.WM_TRAY, 0, tray.WM_RBUTTONUP))
t.pump()
ok("a burst of clicks opens one menu, not five", clicks == [1], str(clicks))

clicks.clear()
u.queue.append((t.hwnd, 0x0200, 0, 0))   # mouse move: not ours to care about
t.pump()
ok("messages that are not tray clicks do nothing", not clicks)

u.queue.append((9999, tray.WM_TRAY, 0, tray.WM_RBUTTONUP))   # another window
ok("and another window's messages are left alone", t.pump() == 0)
ok("still sitting in the queue for its owner", len(u.queue) == 1)
u.queue.clear()

print("\n--- it puts itself back when the tray is wiped ---")
# Explorer restarting wipes every tray icon and each app is expected to add its
# own back. An app that does not simply vanishes from the tray for the rest of
# the session — which is what kept happening.
sh.calls.clear()
u.queue.append((t.hwnd, 0xC001, 0, 0))   # TaskbarCreated
t.pump()
ok("TaskbarCreated triggers a re-add",
   any(c[0] == tray.NIM_ADD for c in sh.calls), str([c[0] for c in sh.calls]))
ok("and it deletes the stale entry first",
   [c[0] for c in sh.calls][:2] == [tray.NIM_DELETE, tray.NIM_ADD],
   str([c[0] for c in sh.calls]))

print("\n--- and it notices on its own when it goes ---")
sh.calls.clear()
t._checked = 0.0                         # force the heartbeat due
sh.refuse = True                         # the shell no longer knows the icon
t.pump()
sh.refuse = False
ok("the heartbeat checks with NIM_MODIFY",
   sh.calls and sh.calls[0][0] == tray.NIM_MODIFY, str([c[0] for c in sh.calls]))
ok("and re-adds when the check fails",
   any(c[0] == tray.NIM_ADD for c in sh.calls), str([c[0] for c in sh.calls]))

sh.calls.clear()
t._checked = 0.0
t.pump()
ok("a healthy icon is checked and left alone",
   [c[0] for c in sh.calls] == [tray.NIM_MODIFY], str([c[0] for c in sh.calls]))
sh.calls.clear()
t.pump()
ok("and not checked again on the very next frame", not sh.calls, str(sh.calls))

print("\n--- one bad pump does not cost the session its icon ---")


class Flaky(FakeUser32):
    def PeekMessageW(self, *a):
        raise OSError("transient")


t._user32 = Flaky()
for _ in range(5):
    t.pump()
ok("five failures and it is still live", t.live, str(t._faults))
for _ in range(6):
    t.pump()
ok("but it does give up eventually rather than spinning", not t.live)
t.live = True
t._faults = 0
t._user32 = u

print("\n--- the tooltip follows the language ---")
t.set_tip("클로드 — 클릭하면 메뉴")
ok("it was modified, not re-added",
   sh.calls[-1][0] == tray.NIM_MODIFY, str(sh.calls[-1][0]))
ok("with the new text", sh.calls[-1][1] == "클로드 — 클릭하면 메뉴", sh.calls[-1][1])

print("\n--- quitting takes it out of the tray ---")
hwnd = t.hwnd
t.stop()
ok("Shell_NotifyIcon was told to DELETE it",
   any(c[0] == tray.NIM_DELETE for c in sh.calls))
ok("and the window was destroyed", hwnd in u.destroyed, str(u.destroyed))
ok("it knows it is gone", not t.live)
ok("stopping twice is harmless", t.stop() is None)
ok("pumping a dead icon is harmless", t.pump() == 0)

print("\n--- every failure is survivable ---")
bad_sh = FakeShell32()
bad_sh.refuse = True
u2, _, _ = install(shell32=bad_sh)
t2 = tray.Tray(lambda: None, log=lambda *a: None)
ok("a refused icon is not a crash", not t2.start())
ok("it says why", "refused" in tray.why() or "unavailable" in tray.why(), tray.why())


class Exploding(FakeUser32):
    def CreateWindowExW(self, *a):
        return 0


u3, _, _ = install(user32=Exploding())
t3 = tray.Tray(lambda: None, log=lambda *a: None)
ok("nor is a window that will not be created", not t3.start())

print("\n--- only one Clawd at a time ---")
from core import single                                        # noqa: E402
import subprocess                                              # noqa: E402

# the fake platform above must not follow us in here: the lock picks its
# mechanism from sys.platform, and a Windows mutex cannot be taken on Linux
sys.platform = real_platform
single.release()
ok("the first copy gets the lock", single.acquire())
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
probe = ("import sys; sys.path.insert(0, %r)\n"
         "from core import single\n"
         "print(single.acquire())\n" % here)
r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
ok("a second copy is refused", r.stdout.strip() == "False",
   repr(r.stdout.strip() or r.stderr[-200:]))
single.release()
r = subprocess.run([sys.executable, "-c", probe + "single.release()"],
                   capture_output=True, text=True)
ok("and the lock is given back on quit", r.stdout.strip() == "True",
   repr(r.stdout.strip() or r.stderr[-200:]))
ok("asking twice in one process is fine", single.acquire())
single.release()

print("\n--- the tray owns the only menu there is ---")
sys.platform = real_platform
ctypes.windll = real_windll
tray._why = ""

a = appmod.App()
a.cfg["api"]["api_key"] = ""
ok("the app starts with no tray at all", not a.tray_on)
ok("and the frame loop pumping it is harmless", a.tray.pump() == 0)

ok("the icon is handed the menu builder, not a click handler",
   a.tray.build_menu is not None and a.tray.on_click is None)
ok("and it is the app's own menu_spec", a.tray.build_menu == a.menu_spec)
spec = a.tray.build_menu()
ok("which returns entries a native menu can be built from",
   spec and all(e is None or (len(e) >= 2 and isinstance(e[0], str)
                              and callable(e[1])) for e in spec))
ok("with the tray able to post it itself", callable(getattr(a.tray, "popup", None)))
ok("nothing goes through Tk for it",
   not any(hasattr(a, n) for n in ("on_menu", "close_menu", "tray_clicked", "_menu")))

print("\n--- and the menu no longer carries the three you dropped ---")
labels = [x[0] for x in a.menu_spec() if x]
for gone in ("menu.edit_cfg", "menu.open_log", "menu.reload"):
    ok(f"{gone} is gone from the strings", lang.t(gone) == gone, lang.t(gone))
ok("nothing edits config from the menu",
   not any("config" in x.lower() for x in labels), str(labels))
ok("nor opens the log", not any("log" in x.lower() or "로그" in x for x in labels))
ok("nor reloads settings",
   not any("reload" in x.lower() or "다시 읽기" in x for x in labels))
ok("but the useful ones are still there",
   lang.t("menu.quiz") in labels and lang.t("menu.quit") in labels, str(labels))

a.ui.root.destroy()
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
