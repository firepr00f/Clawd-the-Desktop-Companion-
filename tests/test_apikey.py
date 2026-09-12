"""
The runtime API-key flow: where the key is looked for, what the dialog does
with it, and where it must never end up.

    xvfb-run -a python tests/test_apikey.py

Uses a temporary app-data directory, so it never touches a real saved key.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TMP = tempfile.mkdtemp(prefix="clawd-key-test-")
os.environ["LOCALAPPDATA"] = TMP
os.environ["XDG_CONFIG_HOME"] = TMP
os.environ.pop("ANTHROPIC_API_KEY", None)

from core import app as appmod, capture, secrets, watcher   # noqa: E402
from core.brain import Brain                                # noqa: E402
from core.watcher import Activity                           # noqa: E402

fails = []
FAKE = "sk-ant-api03-" + "x" * 60
OTHER = "sk-ant-api03-" + "y" * 60


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


print("\n--- where the key is stored ---")
ok("app-data dir is outside the project folder",
   os.path.dirname(os.path.abspath(__file__)) not in secrets.path(),
   secrets.path())
ok("nothing stored to begin with", not secrets.stored())

good, where = secrets.save(FAKE)
ok("it saves", good, where)
ok("and reads back", secrets.load() == FAKE)
ok("stored() notices", secrets.stored())

print("\n--- lookup order ---")
cfg = {"api": {"enabled": True, "api_key": ""}}
b = Brain(cfg)
ok("falls back to the saved file", b.key() == FAKE)
ok("and says so", b.key_source() == secrets.display_path(), b.key_source())

os.environ["ANTHROPIC_API_KEY"] = OTHER
ok("the env var beats the saved file", b.key() == OTHER)
ok("and says so", b.key_source() == "ANTHROPIC_API_KEY", b.key_source())

cfg["api"]["api_key"] = "sk-ant-api03-" + "z" * 60
ok("config.json beats both", b.key().endswith("z" * 10))
ok("and says so", b.key_source() == "config.json", b.key_source())

cfg["api"]["api_key"] = ""
os.environ.pop("ANTHROPIC_API_KEY", None)
ok("back to the saved file when the others are empty", b.key() == FAKE)

print("\n--- shape check and redaction ---")
ok("accepts a real-shaped key", secrets.looks_like_key(FAKE))
ok("rejects a random string", not secrets.looks_like_key("hunter2"))
ok("rejects an openai key", not secrets.looks_like_key("sk-proj-" + "a" * 60))
ok("rejects a key with a stray space", not secrets.looks_like_key(FAKE[:20] + " " + FAKE[20:]))
ok("redaction hides the middle",
   FAKE[15:40] not in secrets.redact(FAKE), secrets.redact(FAKE))

print("\n--- through the app ---")
watcher.foreground = lambda: Activity(title="t", process="chrome.exe", rect=(0, 0, 900, 700))
capture.available = lambda: False
appmod._save_json = lambda *a, **k: None

secrets.clear()
app = appmod.App()
app.cfg["api"]["enabled"] = True
app.cfg["api"]["api_key"] = ""
ok("he knows he needs a key", app.needs_key())

app.brain.test_key = lambda: (True, "api key works")
app.save_key(FAKE, also_env=False)
ok("saving from the dialog stores it", secrets.load() == FAKE)
ok("and the brain picks it up with no restart", app.brain.key() == FAKE)
ok("he no longer needs one", not app.needs_key())

app.ui.clear_msg()
app.save_key("not-a-key", also_env=False)
ok("a bad paste is refused", secrets.load() == FAKE, secrets.redact(secrets.load()))
ok("and he says why", "sk-ant-" in app.ui._msg, repr(app.ui._msg))

print("\n--- the key must not leak ---")
log_path = appmod.LOG_PATH
before = os.path.getsize(log_path) if os.path.exists(log_path) else 0
app.brain.test_key = lambda: (True, "api key works")
app.save_key(OTHER, also_env=False)
with open(log_path, "r", encoding="utf-8") as f:
    f.seek(before)
    written = f.read()
ok("the log records the save", "api key saved" in written, written.strip()[-80:])
ok("but never the key itself", OTHER not in written)
ok("only a redacted stub", secrets.redact(OTHER) in written)

app.ui.clear_msg()
app.test_key()
ok("the bubble never shows the key", OTHER not in app.ui._msg, repr(app.ui._msg))

cfgtext = open(os.path.join(os.path.dirname(appmod.CONFIG_PATH), "config.json"),
               encoding="utf-8").read()
ok("nothing was written into config.json", OTHER not in cfgtext and FAKE not in cfgtext)

srcdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
leaked = [f for f in os.listdir(srcdir) if f.endswith(".py")
          and OTHER in open(os.path.join(srcdir, f), encoding="utf-8").read()]
ok("and nothing was written into the source code", not leaked, str(leaked))

print("\n--- forgetting ---")
app.ui.clear_msg()
app.forget_key()
ok("forget removes the file", not secrets.stored())
ok("and he says he's offline", "offline" in app.ui._msg.lower(), repr(app.ui._msg))
ok("brain agrees", not app.brain.key())

print("\n--- the dialog itself ---")
captured = []
box = app.ui.ask_secret("t", "blurb", "extra", on_done=lambda v, e: captured.append((v, e)))
ok("it opens", box is not None)
entry = [w for w in box.winfo_children()
         if w.winfo_class() == "Entry"] or None
ok("input is masked", entry and entry[0].cget("show") not in ("", None),
   entry[0].cget("show") if entry else "no entry")
app.ui.root.update()
box.destroy()

app.ui.root.destroy()
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
