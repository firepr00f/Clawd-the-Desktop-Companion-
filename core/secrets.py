"""
Where the API key lives when you type it into Clawd instead of a file.

Deliberately NOT config.json and definitely not a .py file: this project sits in
a OneDrive folder, so anything written next to the code syncs to the cloud and
follows every copy of the project around. The key goes in the per-user app-data
directory instead, which is local to this machine:

    Windows   %LOCALAPPDATA%\\Clawd\\api_key
    macOS     ~/Library/Application Support/Clawd/api_key
    Linux     ~/.config/clawd/api_key

Plain text, readable by anyone who can already read your user profile — this is
obfuscation-free storage, not a vault. It is a level safer than the synced
folder, and no safer than that. If you want it properly protected, use the
ANTHROPIC_API_KEY environment variable and a password manager.
"""

from __future__ import annotations

import os
import subprocess
import sys

APP = "Clawd"
ENV_VAR = "ANTHROPIC_API_KEY"
FILENAME = "api_key"


def _dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP)
    if sys.platform == "darwin":
        return os.path.expanduser(f"~/Library/Application Support/{APP}")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP.lower())


def path() -> str:
    return os.path.join(_dir(), FILENAME)


def display_path() -> str:
    """The stored location, with the home directory shortened for a bubble."""
    p = path()
    home = os.path.expanduser("~")
    return p.replace(home, "~") if p.startswith(home) else p


# ---------------------------------------------------------------------------


def load() -> str:
    try:
        with open(path(), "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def save(key: str) -> tuple[bool, str]:
    """Write the key. Returns (ok, message)."""
    key = (key or "").strip()
    if not key:
        return False, "nothing to save"
    try:
        os.makedirs(_dir(), exist_ok=True)
        p = path()
        with open(p, "w", encoding="utf-8") as f:
            f.write(key)
        try:                       # best effort; a no-op on Windows
            os.chmod(p, 0o600)
        except Exception:
            pass
        return True, display_path()
    except Exception as e:
        return False, f"couldn't write {display_path()}: {e}"


def clear() -> bool:
    try:
        os.remove(path())
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False


def stored() -> bool:
    return bool(load())


# ---------------------------------------------------------------------------


def set_user_env(key: str) -> tuple[bool, str]:
    """
    Also register the key as a persistent user environment variable, so other
    tools on this machine can see it. Windows only; `setx` writes to the
    registry and only affects processes started afterwards.
    """
    if sys.platform != "win32":
        return False, "only on windows"
    try:
        r = subprocess.run(["setx", ENV_VAR, key], capture_output=True, text=True,
                           timeout=15,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0:
            return True, f"{ENV_VAR} set for your account"
        return False, (r.stderr or r.stdout or "setx failed").strip()[:120]
    except Exception as e:
        return False, f"setx failed: {e}"


def looks_like_key(s: str) -> bool:
    """A cheap shape check so an obvious paste error is caught before a call."""
    s = (s or "").strip()
    return s.startswith("sk-ant-") and len(s) >= 40 and " " not in s


def redact(s: str) -> str:
    s = (s or "").strip()
    if len(s) < 12:
        return "(empty)"
    return f"{s[:10]}…{s[-4:]}"
