"""
JSON replies must not go through the spoken-line trimmer.

The bug this pins down: every API answer went through Brain.shorten(), which
caps a *line* at api.max_line_chars (200 by default) and ends it in an
ellipsis. That is right for something he says out loud and fatal for a JSON
object — 200 characters lands in the middle of a string, json.loads throws,
_json_call returns None, and _spawn queues nothing at all.

The visible symptom was a quiz that never arrived: 'here comes a question…'
and then nothing, forever, because a question plus its answer has never once
fitted in 200 characters. The shorter look/grade replies usually squeaked
under the cap, which is why most of the app looked fine.

    python tests/test_json_replies.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.brain import Brain                              # noqa: E402

fails = []


def ok(label, cond, extra=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}" + (f"   {extra}" if extra else ""))
    if not cond:
        fails.append(label)


CFG = {"api": {"enabled": True, "api_key": "test", "max_line_chars": 200}}
QUESTION = ("In a series RLC circuit driven at resonance, what happens to the "
            "magnitude of the impedance, and why does the current reach its "
            "maximum there?")
ANSWER = ("The reactances cancel, so the impedance falls to just R — its "
          "minimum — and by Ohm's law the current is therefore at its maximum.")
QUIZ_JSON = json.dumps({"question": QUESTION, "answer": ANSWER, "topic": "RLC resonance"})


def parses(text: str) -> bool:
    """The exact test _json_call applies: grab the outer braces and load."""
    try:
        json.loads(text[text.find("{"):text.rfind("}") + 1])
        return True
    except Exception:
        return False


def brain_returning(text):
    """A Brain whose one and only API call hands back `text`."""
    b = Brain(CFG, lambda _m: None, None)
    b._post = lambda payload, timeout=40.0: {
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }
    return b


print("\n--- the cap that broke the quiz ---")

cap = CFG["api"]["max_line_chars"]
ok("the test's own quiz JSON is longer than the cap", len(QUIZ_JSON) > cap,
   f"{len(QUIZ_JSON)} chars vs cap {cap}")

b = brain_returning(QUIZ_JSON)
ok("as written it parses fine", parses(QUIZ_JSON))
ok("run through shorten() it does not — that was the bug",
   not parses(b.shorten(QUIZ_JSON)), repr(b.shorten(QUIZ_JSON))[-60:])

data = b._quiz_call("prompt", None, "system")
ok("but the real call comes back parsed", isinstance(data, dict), repr(data)[:80])
ok("with the question intact, not cut short",
   data.get("question") == QUESTION, repr(data.get("question"))[:90])
ok("and the answer intact too", data.get("answer") == ANSWER,
   repr(data.get("answer"))[:90])
ok("nothing picked up an ellipsis", "…" not in json.dumps(data, ensure_ascii=False))

print("\n--- spoken lines are still trimmed ---")

long_line = ("He does go on. " * 40).strip()
b2 = brain_returning(long_line)
said = b2._ask("prompt", None, "model", 160, "system")
ok("a line he says out loud is still capped", len(said) <= cap + 1,
   f"{len(said)} chars")
ok("and only that path trims",
   len(b2._ask("prompt", None, "model", 160, "system", trim=False)) == len(long_line))

print("\n--- an unusable answer still ends the wait ---")

for junk, why in ((" ", "an empty reply"),
                  ("sorry, I can't see the screen", "prose instead of JSON"),
                  ('{"question": "half a que', "JSON cut off mid-string"),
                  ('{"question": "q", "answer": ""}', "a blank answer field")):
    got = brain_returning(junk)._quiz_call("prompt", None, "system")
    ok(f"{why}: he falls back to an offline question",
       isinstance(got, dict) and bool(got.get("question")) and bool(got.get("answer")),
       repr(got)[:70])

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
