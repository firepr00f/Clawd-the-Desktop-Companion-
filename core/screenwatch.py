"""
Making a window title comparable to the last one you saw.

This used to be a whole background watcher that decided, on a timer, when Clawd
should photograph your screen. That is gone: Clawd never captures anything on
his own any more, and the only screenshot in the whole app is the one you ask
for by double-clicking him. What survived is the useful half — `normalise`,
which strips the parts of a window title that change on their own.

That matters because "has the window changed?" drives the settle timer in
App.settled_verdict. Without it a ticking video clock, an unread badge or an
editor's unsaved-changes dot reads as a brand new window every few seconds:

    " (12) KLAS - 광운대학교 - Google Chrome"  ->  "klas - 광운대학교"
    "▶ lecture 3  12:03 / 48:20 - Chrome"     ->  "lecture 3 /"

Windows puts the browser tab title in the window title, so a new URL shows up
here too — no browser extension needed.
"""
from __future__ import annotations

import re

# Trailing browser/app branding: " - Google Chrome", " — Mozilla Firefox", ...
_BRAND = re.compile(
    r"\s*[-—–|]\s*(google chrome|chrome|microsoft.?edge|edge|mozilla firefox|firefox|"
    r"brave|opera|vivaldi|whale|네이버 웨일|arc|safari)\s*$", re.I)

# Edge's "and 3 more pages", unread badges "(12) ", media marks "▶ "
_MORE_PAGES = re.compile(r"\s*and \d+ more pages?\s*$", re.I)
_BADGE = re.compile(r"^\s*[(\[]\d+[)\]]\s*")
_MEDIA_MARK = re.compile(r"^\s*[▶►●○•⏸]\s*")

# Timestamps that tick while a video plays: "(12:03) ", " 12:03 / 1:02:44"
_TIMECODE = re.compile(r"\(?\b\d{1,2}:\d{2}(?::\d{2})?\b\)?")

# Editors marking unsaved changes: "* main.py", "main.py •"
_DIRTY = re.compile(r"^\s*[*•]\s*|\s*[*•]\s*$")

# Separators left stranded once a timecode or badge between them is removed
_ORPHANED = re.compile(r"\s*[/|–—-]\s*(?=[/|–—-]|\s*$)")


# Edge really does put a zero-width space inside "Microsoft​ Edge"
_INVISIBLE = re.compile(r"[​‌‍﻿]")


def normalise(title: str) -> str:
    """
    Strip the noise that changes without you doing anything, so a genuine page
    change reads as a change and a ticking video clock does not.
    """
    t = _INVISIBLE.sub("", title or "")
    # branding sits at the very end, and Edge hides "and N more pages" behind it,
    # so peel from the right twice
    for _ in range(2):
        t = _BRAND.sub("", t)
        t = _MORE_PAGES.sub("", t)
    t = _BADGE.sub("", t)
    t = _MEDIA_MARK.sub("", t)
    t = _DIRTY.sub("", t)
    t = _TIMECODE.sub("", t)
    # Pulling "12:03 / 48:20" out leaves the slash behind, so a video with a
    # running clock normalised to something slightly different every time and
    # read as a brand new window. Sweep up the separators the removals orphaned.
    t = _ORPHANED.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip(" -|/\u2013\u2014").lower()
