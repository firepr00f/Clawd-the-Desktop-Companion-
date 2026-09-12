"""
Reads schedule.json and turns it into things Clawd can nag about.

The file is plain JSON you edit in any text editor; it's re-read from disk
whenever it changes, so you can update it while Clawd is running.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt in ("%Y-%m-%d", "%Y/%m/%d"):
                dt = dt.replace(hour=23, minute=59)
            return dt
        except ValueError:
            continue
    return None


def humanize(delta: timedelta) -> str:
    secs = abs(int(delta.total_seconds()))
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    if days >= 2:
        return f"{days} days"
    if days == 1:
        return "1 day" if hours < 6 else f"1 day {hours}h"
    if hours >= 1:
        return f"{hours}h" if mins < 10 else f"{hours}h {mins}m"
    return f"{max(1, mins)} min"


class Schedule:
    def __init__(self, path: str, log=lambda *a: None):
        self.path = path
        self.log = log
        self.data: dict = {}
        self._mtime = 0.0
        self.reload()

    def reload(self) -> bool:
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            return False
        if mtime == self._mtime:
            return False
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            self._mtime = mtime
            self.log("schedule.json loaded")
            return True
        except Exception as e:
            self.log(f"schedule.json unreadable: {e}")
            return False

    # ---------------- queries ----------------

    def deadlines(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        out = []
        for d in self.data.get("deadlines", []):
            if d.get("done"):
                continue
            due = _parse_dt(d.get("due", ""))
            if not due:
                continue
            out.append({**d, "_due": due, "_delta": due - now})
        out.sort(key=lambda d: d["_due"])
        return out

    def due_today(self, now=None) -> list[dict]:
        now = now or datetime.now()
        return [d for d in self.deadlines(now)
                if d["_due"].date() == now.date() and d["_delta"].total_seconds() > 0]

    def overdue(self, now=None) -> list[dict]:
        now = now or datetime.now()
        return [d for d in self.deadlines(now) if d["_delta"].total_seconds() < 0]

    def due_within(self, days: int = 3, now=None) -> list[dict]:
        now = now or datetime.now()
        horizon = timedelta(days=days)
        return [d for d in self.deadlines(now)
                if timedelta(0) < d["_delta"] <= horizon
                and d["_due"].date() != now.date()]

    def todos(self) -> list[dict]:
        return [t for t in self.data.get("todos", []) if not t.get("done")]

    def _events_today(self, key: str, now: datetime) -> list[dict]:
        today = DAY_KEYS[now.weekday()]
        out = []
        for c in self.data.get(key, []):
            days = [d.strip().lower()[:3] for d in c.get("days", [])]
            if today not in days:
                continue
            start = c.get("start", "")
            try:
                hh, mm = (int(x) for x in start.split(":"))
            except Exception:
                continue
            when = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            out.append({**c, "_start": when, "_delta": when - now})
        out.sort(key=lambda c: c["_start"])
        return out

    def classes_today(self, now=None) -> list[dict]:
        return self._events_today("courses", now or datetime.now())

    def shifts_today(self, now=None) -> list[dict]:
        return self._events_today("shifts", now or datetime.now())

    def starting_soon(self, within_min: int = 25, now=None) -> list[dict]:
        now = now or datetime.now()
        window = timedelta(minutes=within_min)
        return [c for c in self.classes_today(now) + self.shifts_today(now)
                if timedelta(0) < c["_delta"] <= window]

    # ---------------- briefing ----------------

    def briefing(self, now=None) -> list[str]:
        """Human-readable lines for the start-of-session summary."""
        now = now or datetime.now()
        lines: list[str] = []

        cls = self.classes_today(now)
        if cls:
            names = ", ".join(
                f"{c.get('name', '?')} {c.get('start', '')}" for c in cls
            )
            lines.append(f"today's classes: {names}")

        sh = self.shifts_today(now)
        if sh:
            lines.append("shift today: " + ", ".join(
                f"{s.get('title', 'work')} {s.get('start', '')}" for s in sh))

        for d in self.overdue(now):
            lines.append(f"OVERDUE: {d.get('title')} ({humanize(d['_delta'])} ago)")
        for d in self.due_today(now):
            lines.append(f"DUE TODAY: {d.get('title')} ({humanize(d['_delta'])} left)")
        for d in self.due_within(3, now):
            lines.append(f"due in {humanize(d['_delta'])}: {d.get('title')}")

        pending = self.todos()
        if pending:
            lines.append("still pending: " + ", ".join(t.get("title", "?") for t in pending[:3]))

        if not lines:
            lines.append("nothing on the calendar. suspicious. go study anyway")
        return lines
