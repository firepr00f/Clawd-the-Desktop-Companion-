"""
Screenshot capture for API mode. Optional -- absent libs just disable it.

Two jobs:

  grab_jpeg_b64()   a real screenshot, base64 JPEG, for the model to read.
  signature()       a tiny 8x8 grayscale fingerprint used locally, for free,
                    to notice that the screen *changed* without calling the API.

Both go through _resolve_rect(), which is where the old "Clawd only sees the
tab bar" bug lived: a window rect that doesn't line up with the physical
screen (DPI scaling, a minimised window, a bogus rect) now falls back to
capturing the whole monitor instead of cropping garbage.
"""

from __future__ import annotations

import base64
import io

from . import dpi

_backend = None

try:  # preferred: fast, no extra image deps beyond Pillow for encoding
    import mss  # type: ignore
    _backend = "mss"
except Exception:
    mss = None  # type: ignore

try:
    from PIL import Image  # type: ignore
    if _backend is None:
        from PIL import ImageGrab  # type: ignore
        _backend = "pil"
except Exception:
    Image = None  # type: ignore
    ImageGrab = None  # type: ignore

# 1568px is where Anthropic stops gaining anything from a larger image, and it
# is roughly the point where 12px on-screen text is still legible after JPEG.
DEFAULT_MAX_WIDTH = 1568
DEFAULT_QUALITY = 72

MIN_USEFUL_SIDE = 200          # anything thinner than this isn't worth reading


def available() -> bool:
    return _backend is not None and Image is not None


def last_error() -> str:
    return _last_error


_last_error = ""


# ---------------------------------------------------------------------------


def _resolve_rect(rect):
    """
    Turn a window rect into a box we can actually grab, or None for full screen.

    Rejects rects that are off-screen, degenerate, or larger than the desktop
    -- all signs that the coordinates don't mean what we think they mean.
    """
    if not rect:
        return None
    try:
        l, t, r, b = (int(v) for v in rect)
    except Exception:
        return None
    if r < l:
        l, r = r, l
    if b < t:
        t, b = b, t
    w, h = r - l, b - t
    if w < MIN_USEFUL_SIDE or h < MIN_USEFUL_SIDE:
        return None

    screen = dpi.virtual_screen()
    if screen:
        sl, st, sr, sb = screen
        # clip to the desktop; if almost nothing survives, take the full screen
        cl, ct = max(l, sl), max(t, st)
        cr, cb = min(r, sr), min(b, sb)
        if cr - cl < MIN_USEFUL_SIDE or cb - ct < MIN_USEFUL_SIDE:
            return None
        visible = (cr - cl) * (cb - ct)
        if visible < 0.5 * w * h:      # more than half the window is off-screen
            return None
        l, t, r, b = cl, ct, cr, cb

    return (l, t, r, b)


def _grab_image(rect):
    """PIL RGB image of `rect`, or of the whole desktop when rect is None."""
    global _last_error
    box = _resolve_rect(rect)

    if _backend == "mss":
        with mss.mss() as sct:
            if box:
                l, t, r, b = box
                area = {"left": l, "top": t,
                        "width": max(1, r - l), "height": max(1, b - t)}
            else:
                # monitors[0] is the whole virtual desktop across all screens
                area = sct.monitors[0] if len(sct.monitors) > 1 else sct.monitors[-1]
            raw = sct.grab(area)
            return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    img = ImageGrab.grab(bbox=box, all_screens=True)
    return img.convert("RGB")


# ---------------------------------------------------------------------------


def grab_jpeg_b64(rect=None, max_width: int = DEFAULT_MAX_WIDTH,
                  quality: int = DEFAULT_QUALITY) -> str | None:
    """
    Capture `rect` (left, top, right, bottom) or the whole desktop, downscale
    and return base64 JPEG. Returns None if capture isn't possible.
    """
    global _last_error
    if not available():
        _last_error = "no screenshot backend (pip install mss Pillow)"
        return None
    try:
        img = _grab_image(rect)
        if img.width > max_width:
            h = int(img.height * max_width / img.width)
            img = img.resize((max_width, max(1, h)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        _last_error = ""
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as e:
        _last_error = f"capture failed: {e}"
        return None


def signature(rect=None, side: int = 12) -> tuple[int, ...] | None:
    """
    A tiny grayscale fingerprint of the screen -- 12x12 = 144 numbers.

    Costs a few milliseconds and zero tokens, so it can run on every poll.
    Compare two of these with `delta()` to notice that the page changed even
    though the window title didn't (a video playing, scrolling a PDF, a SPA
    that never updates its <title>).
    """
    if not available():
        return None
    try:
        img = _grab_image(rect)
        img = img.convert("L").resize((side, side), Image.BILINEAR)
        return tuple(img.getdata())
    except Exception:
        return None


def delta(a, b) -> float:
    """Mean absolute difference between two signatures, 0..255. None-safe."""
    if not a or not b or len(a) != len(b):
        return 255.0
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))
