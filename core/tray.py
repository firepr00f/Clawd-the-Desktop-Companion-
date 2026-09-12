"""
Clawd in the Windows notification area.

The point of this is reachability. Clawd is a borderless, click-through,
always-on-top sprite with no title bar and no taskbar button, so the ONLY way
to control him is to right-click the sprite itself — and if he is behind a
maximised window, off on a monitor you unplugged, or you simply can't find
him, there is nothing left to click. The tray icon is the handle that is
always there.

Two decisions worth knowing about:

  * No third-party package. The first version of this used pystray, which
    meant "the tray icon works if you remembered to pip install something",
    and it turns out you don't remember. This talks to Shell_NotifyIcon
    through ctypes, exactly like `watcher.py` and `dpi.py` already talk to
    user32, so it works on any Python that can run the rest of Clawd.

  * No thread. The icon owns a message-only window, and its messages are
    pumped from the animation loop that is already running. Tk is not thread
    safe, so a tray click arriving on some other thread would have to be
    queued and marshalled back; arriving on the Tk thread in the first place,
    it can just open the menu.

Everything here fails soft. If any Win32 call refuses, `start()` returns False,
`why()` says what happened, and Clawd runs exactly as he did before with one
fewer way to reach him.
"""

from __future__ import annotations

import os
import sys
import tempfile

from time import monotonic as _clock

from .sprite import (ARM_L, ARM_R, BLACK, BODY, CLAWD_ORANGE, EYES, GRID_H,
                     GRID_W, LEG_H, LEG_X, LEG_Y, _mirror)

_why = ""

# Win32 constants
WM_APP = 0x8000
WM_TRAY = WM_APP + 1                # our own callback message

# MENUITEMINFOW, not AppendMenuW. AppendMenuW infers what its last argument
# means from the flags, and when that inference goes wrong you get exactly what
# it gave us: items of the right height, in the right order, that respond to a
# click and draw no text at all. This says which fields it is setting, points
# at the string, and gives its length — nothing is left to be worked out.
def _declare(fn, restype, *argtypes):
    """
    Pin a ctypes function's signature, both directions.

    The try is only for the test doubles, which stand in plain Python callables
    that have no such attributes; a real ctypes function always takes them.
    """
    try:
        fn.restype = restype
        fn.argtypes = list(argtypes)
    except (AttributeError, TypeError):
        pass


MIIM_STATE, MIIM_ID, MIIM_STRING, MIIM_FTYPE = 0x0001, 0x0002, 0x0040, 0x0100
MFT_STRING, MFT_SEPARATOR = 0x0000, 0x0800
MFS_CHECKED, MFS_DEFAULT = 0x0008, 0x1000
TPM_RIGHTBUTTON, TPM_NONOTIFY, TPM_RETURNCMD = 0x0002, 0x0080, 0x0100
WM_LBUTTONUP, WM_RBUTTONUP = 0x0202, 0x0205
WM_DESTROY = 0x0002
NIM_ADD, NIM_DELETE, NIM_MODIFY = 0, 2, 1
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x01, 0x02, 0x04
IMAGE_ICON = 1
LR_LOADFROMFILE, LR_DEFAULTSIZE = 0x0010, 0x0040
IDI_APPLICATION = 32512
PM_REMOVE = 0x0001
HWND_MESSAGE = -3

# How often to check the icon is still in the tray. Explorer restarting is the
# usual reason it goes; there are others, and none of them tell you.
HEARTBEAT = 20.0


def why() -> str:
    """Why there is no tray icon, if there isn't one. Empty if all is well."""
    return _why


# --- the icon ---------------------------------------------------------------

def icon_image(size: int = 32):
    """
    Clawd himself, standing still, drawn straight from the sprite geometry.

    Same body, arms, legs and eyes as the thing on your desktop — read from
    `sprite.py` rather than copied, so if he is ever redrawn the tray icon is
    redrawn with him.

    He is 18 cells wide and 11 tall. At the 16 pixels Windows actually gives a
    tray icon that is under a pixel per cell, which is mush, so below 28px he
    is cropped to his face: the body, the arms and the two eyes, filling the
    square. It is the same sprite, just close up — which is the half of him
    that is recognisable at that size anyway.
    """
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    full = size >= 28

    bx, by, bw, bh = BODY
    if full:
        cols, left, top, rows = GRID_W, 0, 0, GRID_H
    else:
        cols, left, top, rows = bw, bx, by, bh          # just the body block
    cell = size / cols
    oy = (size - rows * cell) / 2

    def box(x, y, w, h, colour):
        d.rectangle([round((x - left) * cell), round(oy + (y - top) * cell),
                     round((x - left + w) * cell) - 1,
                     round(oy + (y - top + h) * cell) - 1], fill=colour)

    box(*BODY, CLAWD_ORANGE)
    if full:
        box(*ARM_L, CLAWD_ORANGE)
        box(*ARM_R, CLAWD_ORANGE)
        for lx in LEG_X:
            box(lx, LEG_Y, 2, LEG_H, CLAWD_ORANGE)
    for block in EYES["open"]:
        for ex, ey, ew, eh in (block, _mirror(block)):
            box(ex, ey, ew, eh, BLACK)
    return img


def _icon_handle(user32):
    """
    An HICON of Clawd at exactly the size Windows wants, or 0.

    Rendered at the target size and written as a single-size .ico, rather than
    drawn big and scaled down: pixel art survives neither Pillow's resampling
    nor the shell's. Pillow does the file, LoadImageW does the handle —
    building it by hand with CreateDIBSection and CreateIconIndirect is four
    times the code for the same picture.
    """
    size = 16
    try:
        SM_CXSMICON = 49
        size = int(user32.GetSystemMetrics(SM_CXSMICON)) or 16
    except Exception:
        pass
    size = max(16, min(size, 256))
    try:
        path = os.path.join(tempfile.gettempdir(), f"clawd_tray_{size}.ico")
        icon_image(size).save(path, sizes=[(size, size)])
        h = user32.LoadImageW(None, path, IMAGE_ICON, size, size, LR_LOADFROMFILE)
        if h:
            return h
    except Exception:
        pass
    try:                                        # last resort: a stock icon
        return user32.LoadIconW(None, IDI_APPLICATION)
    except Exception:
        return 0


class Tray:
    """
    The tray icon, or a harmless no-op wherever it cannot exist.

    `on_click` is called — on the caller's thread, from `pump()` — whenever the
    icon is clicked, with no arguments. Clicking it should do exactly what
    right-clicking the sprite does.
    """

    def __init__(self, on_click=None, log=lambda *a: None, title: str = "Clawd",
                 build_menu=None):
        self.on_click = on_click
        # Returns the menu to show, fresh, every time it is clicked: labels
        # depend on the language and on what is open, so a menu built once at
        # startup would lie. Entries are (label, callback) or None for a rule.
        self.build_menu = build_menu
        self.log = log
        self.title = title
        self.hwnd = 0
        self.hicon = 0
        self._proc = None          # MUST stay referenced or ctypes frees it
        self._clicks = 0
        self._readd = False        # Explorer came back; put the icon back
        self._faults = 0
        self._menu_logged = False
        self._checked = 0.0
        self.live = False

    # -- lifecycle ------------------------------------------------------

    def start(self) -> bool:
        global _why
        if sys.platform != "win32":
            _why = "the tray icon is Windows only"
            self.log(_why)
            return False
        try:
            self._create()
            self.live = True
            self.log("tray icon added")
            return True
        except Exception as e:
            _why = f"tray icon unavailable: {e!r}"
            self.log(_why)
            self._safe_delete()
            return False

    def _create(self):
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        user32 = self._user32 = ctypes.windll.user32
        shell32 = self._shell32 = ctypes.windll.shell32

        # A window procedure that only cares about our own callback message.
        # Kept on self: if this object is collected, Windows calls into freed
        # memory the next time you touch the icon.
        LRESULT = (ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8
                   else ctypes.c_long)
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                                     wintypes.WPARAM, wintypes.LPARAM)

        # Declared, all of it, and DefWindowProcW above all.
        #
        # An undeclared ctypes function returns a C int, so on 64-bit every
        # LRESULT this window proc hands back to Windows was truncated to 32
        # bits. Most messages return 0 and survive that. Menus do not: while a
        # popup is tracking, Windows sends its owner a run of messages whose
        # return value decides how the items get measured and painted — and a
        # corrupted answer to those is a menu that draws its frame, its
        # separators and the right number of correctly-sized rows, and no text
        # in any of them. Which is exactly what it did.
        kernel32 = ctypes.windll.kernel32
        _declare(user32.DefWindowProcW, LRESULT, wintypes.HWND, wintypes.UINT,
                 wintypes.WPARAM, wintypes.LPARAM)
        _declare(user32.CreateWindowExW, wintypes.HWND,
                 wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                 ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                 wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID)
        _declare(user32.RegisterWindowMessageW, wintypes.UINT, wintypes.LPCWSTR)
        _declare(kernel32.GetModuleHandleW, wintypes.HMODULE, wintypes.LPCWSTR)

        # Explorer broadcasts this to every top-level window when it restarts.
        # Every tray icon is wiped when that happens and each app is expected to
        # put its own back — an app that does not simply disappears from the
        # tray for the rest of the session, which is exactly what kept
        # happening here.
        self._taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")

        def proc(hwnd, msg, wparam, lparam):
            if msg == WM_TRAY and lparam in (WM_LBUTTONUP, WM_RBUTTONUP):
                self._clicks += 1
                return 0
            if msg and msg == self._taskbar_created:
                self._readd = True
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._proc = WNDPROC(proc)

        class WNDCLASS(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                        ("lpszMenuName", wintypes.LPCWSTR),
                        ("lpszClassName", wintypes.LPCWSTR)]

        hinst = kernel32.GetModuleHandleW(None)
        cls = WNDCLASS()
        cls.lpfnWndProc = self._proc
        cls.hInstance = hinst
        cls.lpszClassName = "ClawdTrayWindow"
        self._cls = cls                        # also must outlive registration
        _declare(user32.RegisterClassW, wintypes.ATOM, ctypes.POINTER(WNDCLASS))
        user32.RegisterClassW(ctypes.byref(cls))   # harmless if already there

        # A real top-level window, created and never shown — NOT a message-only
        # (HWND_MESSAGE) one. It is what Windows sends tray clicks to, and it
        # is also the menu's owner, and TrackPopupMenu needs an owner it can
        # bring to the foreground. A message-only window cannot be, and the
        # menu then refuses to close when you click away from it.
        self.hwnd = user32.CreateWindowExW(
            0, "ClawdTrayWindow", "Clawd", 0, 0, 0, 0, 0,
            None, None, hinst, None)
        if not self.hwnd:
            raise OSError("could not create the tray's message window")

        self.hicon = _icon_handle(user32)

        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                        ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
                        ("uCallbackMessage", wintypes.UINT),
                        ("hIcon", wintypes.HICON),
                        ("szTip", wintypes.WCHAR * 128),
                        ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                        ("szInfo", wintypes.WCHAR * 256),
                        ("uVersion", wintypes.UINT),
                        ("szInfoTitle", wintypes.WCHAR * 64),
                        ("dwInfoFlags", wintypes.DWORD)]

        self._NID = NOTIFYICONDATA
        nid = self._nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self.hicon
        nid.szTip = self.title[:127]
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            raise OSError("Shell_NotifyIcon refused to add the icon")
        self._checked = _clock()

    def set_tip(self, text: str):
        """Change the hover tooltip — used to follow the 한/영 switch."""
        if not self.live:
            return
        try:
            self._nid.uFlags = NIF_TIP
            self._nid.szTip = text[:127]
            self._shell32.Shell_NotifyIconW(NIM_MODIFY,
                                            self._ctypes.byref(self._nid))
            self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        except Exception:
            pass

    def stop(self):
        """Take the icon out of the tray. Without this a dead ghost is left."""
        self._safe_delete()
        self.live = False

    def _safe_delete(self):
        try:
            if getattr(self, "_nid", None) is not None and self.hwnd:
                self._shell32.Shell_NotifyIconW(NIM_DELETE,
                                                self._ctypes.byref(self._nid))
        except Exception:
            pass
        try:
            if self.hwnd:
                self._user32.DestroyWindow(self.hwnd)
        except Exception:
            pass
        self.hwnd = 0

    # -- the pump -------------------------------------------------------

    def readd(self) -> bool:
        """Put the icon back in the tray. Returns whether it is there now."""
        try:
            self._shell32.Shell_NotifyIconW(NIM_DELETE,
                                            self._ctypes.byref(self._nid))
        except Exception:
            pass
        try:
            ok = bool(self._shell32.Shell_NotifyIconW(
                NIM_ADD, self._ctypes.byref(self._nid)))
            if ok:
                self.log("tray icon re-added")
                self._faults = 0
            return ok
        except Exception as e:
            self.log(f"tray icon could not be re-added: {e!r}")
            return False

    def _heartbeat(self):
        """
        Is the icon still there? Ask, and put it back if not.

        NIM_MODIFY on an icon the shell no longer knows about fails, which is
        the only reliable way to notice it has gone — nothing announces it.
        Explorer restarting is the common cause and is handled by
        TaskbarCreated above; this catches everything else.
        """
        now = _clock()
        if now - self._checked < HEARTBEAT:
            return
        self._checked = now
        try:
            alive = bool(self._shell32.Shell_NotifyIconW(
                NIM_MODIFY, self._ctypes.byref(self._nid)))
        except Exception:
            alive = False
        if not alive:
            self.readd()

    def pump(self, limit: int = 32) -> int:
        """
        Deliver any pending tray messages, then act on the clicks they carried.

        Called once per animation frame. The message-only window belongs to
        this thread, so PeekMessage with its hwnd takes ONLY our messages and
        leaves Tk's own event queue completely alone.

        Returns how many clicks were handled.
        """
        if not self.live or not self.hwnd:
            return 0
        ctypes = self._ctypes
        from ctypes import wintypes

        class MSG(ctypes.Structure):
            _fields_ = [("hWnd", wintypes.HWND), ("message", wintypes.UINT),
                        ("wParam", wintypes.WPARAM), ("lParam", wintypes.LPARAM),
                        ("time", wintypes.DWORD), ("pt_x", ctypes.c_long),
                        ("pt_y", ctypes.c_long)]

        msg = MSG()
        seen = 0
        try:
            while seen < limit and self._user32.PeekMessageW(
                    ctypes.byref(msg), self.hwnd, 0, 0, PM_REMOVE):
                seen += 1
                self._user32.TranslateMessage(ctypes.byref(msg))
                self._user32.DispatchMessageW(ctypes.byref(msg))
            self._faults = 0
        except Exception as e:
            # One bad pump is not a reason to lose the icon for the session.
            self._faults += 1
            if self._faults >= 10:
                self.live = False
                self.log(f"tray pump failed ten times, dropping the icon: {e!r}")
            return 0

        if self._readd:                       # Explorer restarted
            self._readd = False
            self.readd()
        self._heartbeat()

        clicks, self._clicks = self._clicks, 0
        if clicks:                            # a burst is still one intent
            try:
                if self.build_menu is not None:
                    self.popup()
                elif self.on_click is not None:
                    self.on_click()
            except Exception as e:
                self.log(f"tray click failed: {e!r}")
        return clicks

    # -- the menu -------------------------------------------------------

    def popup(self):
        """
        Build the menu, show it at the pointer, run whatever was picked.

        A native Win32 menu, not a Tk one. A Tk popup belongs to a Tk window
        and drags that window's problems along with it — always-on-top fighting
        the menu for the top of the z-order, the window moving out from under
        it, the whole latch-and-freeze apparatus that existed only to keep
        those two apart. This owes Tk nothing.

        Two Win32 details that are not superstition:

          * The item text goes in through MENUITEMINFOW. Its buffer has to
            outlive the call, so every one is held in `keep` until the menu is
            built — a buffer freed early is an item that draws nothing.
          * The foreground dance around TrackPopupMenu: without the
            SetForegroundWindow the menu opens behind whatever you were using,
            and without the empty message after it, it stays on screen once you
            click away.
        """
        ctypes = self._ctypes
        from ctypes import wintypes

        u = self._user32

        class MENUITEMINFOW(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("fMask", wintypes.UINT),
                        ("fType", wintypes.UINT), ("fState", wintypes.UINT),
                        ("wID", wintypes.UINT), ("hSubMenu", wintypes.HMENU),
                        ("hbmpChecked", wintypes.HBITMAP),
                        ("hbmpUnchecked", wintypes.HBITMAP),
                        ("dwItemData", ctypes.c_size_t),
                        ("dwTypeData", wintypes.LPWSTR), ("cch", wintypes.UINT),
                        ("hbmpItem", wintypes.HBITMAP)]

        # Declared in both directions. A handle is 64 bits and an undeclared
        # ctypes argument goes out as a C int, which is how the last round of
        # this failed.
        _declare(u.CreatePopupMenu, wintypes.HMENU, *[])
        u.InsertMenuItemW.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.BOOL,
                                      ctypes.POINTER(MENUITEMINFOW)]
        u.InsertMenuItemW.restype = wintypes.BOOL
        u.GetMenuItemCount.argtypes = [wintypes.HMENU]
        u.GetMenuItemCount.restype = ctypes.c_int
        u.SetMenuDefaultItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.BOOL]
        u.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                     ctypes.c_void_p]
        u.TrackPopupMenu.restype = ctypes.c_int
        u.DestroyMenu.argtypes = [wintypes.HMENU]
        u.DestroyMenu.restype = wintypes.BOOL
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                   wintypes.WPARAM, wintypes.LPARAM]
        u.PostMessageW.restype = wintypes.BOOL
        u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]

        hmenu = u.CreatePopupMenu()
        if not hmenu:
            self.log("tray menu: CreatePopupMenu failed")
            return

        actions, ident, keep, failed = {}, 0, [], 0
        spec = list(self.build_menu())
        try:
            for pos, entry in enumerate(spec):
                info = MENUITEMINFOW()
                info.cbSize = ctypes.sizeof(MENUITEMINFOW)
                if entry is None:
                    info.fMask = MIIM_FTYPE
                    info.fType = MFT_SEPARATOR
                else:
                    label = str(entry[0])
                    ident += 1
                    actions[ident] = entry[1]
                    buf = ctypes.create_unicode_buffer(label)
                    keep.append(buf)          # must outlive InsertMenuItemW
                    info.fMask = MIIM_STRING | MIIM_ID | MIIM_FTYPE | MIIM_STATE
                    info.fType = MFT_STRING
                    info.fState = MFS_CHECKED if (len(entry) > 2 and entry[2]) else 0
                    if ident == 1:
                        info.fState |= MFS_DEFAULT
                    info.wID = ident
                    info.dwTypeData = ctypes.cast(buf, wintypes.LPWSTR)
                    info.cch = len(label)
                if not u.InsertMenuItemW(hmenu, pos, True, ctypes.byref(info)):
                    failed += 1
                    if failed == 1:
                        self.log(f"tray menu: item {pos} refused, "
                                 f"error {ctypes.GetLastError()}")

            # Said once per session, and only if the count is wrong: if the
            # menu ever comes up blank again, this is the line that says
            # whether the items were even inserted.
            count = u.GetMenuItemCount(hmenu)
            if (failed or count != len(spec)) and not self._menu_logged:
                self._menu_logged = True
                self.log(f"tray menu: {count} of {len(spec)} items, {failed} refused")

            pt = wintypes.POINT()
            u.GetCursorPos(ctypes.byref(pt))
            u.SetForegroundWindow(self.hwnd)
            picked = u.TrackPopupMenu(
                hmenu, TPM_RIGHTBUTTON | TPM_NONOTIFY | TPM_RETURNCMD,
                pt.x, pt.y, 0, self.hwnd, None)
            u.PostMessageW(self.hwnd, 0, 0, 0)          # WM_NULL
        finally:
            u.DestroyMenu(hmenu)

        fn = actions.get(picked)
        if fn:
            fn()
