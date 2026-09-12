"""
Spending guard.

Every API response reports how many tokens it used. This adds them up, prices
them, and once you've hit the daily or monthly cap Clawd simply stops calling
the API and falls back to the offline comment bank — no errors, no surprise
bill, he just gets a bit dumber until midnight.

Counters live in spend.json next to the app. Delete that file to reset.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

# USD per million tokens. Override in config.json under api.prices if these move.
DEFAULT_PRICES = {
    "claude-haiku-4-5-20251001": {"in": 1.0, "out": 5.0},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0},
    "claude-sonnet-5": {"in": 2.0, "out": 10.0},
    "claude-opus-5": {"in": 10.0, "out": 50.0},
    "_default": {"in": 2.0, "out": 10.0},
}


class Budget:
    def __init__(self, path: str, cfg: dict, log=lambda *a: None):
        self.path = path
        self.cfg = cfg
        self.log = log
        self.data = self._load()
        self.tripped = False          # set the first time a cap is hit

    # ------------------------------------------------------------------

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            self.log(f"spend.json write failed: {e}")

    def _roll(self):
        now = datetime.now()
        day, month = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m")
        if self.data.get("day") != day:
            self.data["day"] = day
            self.data["day_usd"] = 0.0
            self.data["day_calls"] = 0
            self.tripped = False
        if self.data.get("month") != month:
            self.data["month"] = month
            self.data["month_usd"] = 0.0
            self.data["month_calls"] = 0

    # ------------------------------------------------------------------

    def _prices(self, model: str) -> dict:
        table = dict(DEFAULT_PRICES)
        table.update(self.cfg.get("api", {}).get("prices", {}) or {})
        return table.get(model) or table["_default"]

    def cap(self, key: str, default: float) -> float:
        try:
            return float(self.cfg.get("api", {}).get(key, default))
        except (TypeError, ValueError):
            return default

    @property
    def day_usd(self) -> float:
        self._roll()
        return float(self.data.get("day_usd", 0.0))

    @property
    def month_usd(self) -> float:
        self._roll()
        return float(self.data.get("month_usd", 0.0))

    def over(self) -> bool:
        """True once either cap is reached. A cap of 0 means unlimited."""
        self._roll()
        d, m = self.cap("daily_budget_usd", 0.30), self.cap("monthly_budget_usd", 5.0)
        if d > 0 and self.day_usd >= d:
            return True
        if m > 0 and self.month_usd >= m:
            return True
        return False

    def add(self, model: str, in_tok: int, out_tok: int) -> float:
        self._roll()
        p = self._prices(model)
        cost = (in_tok / 1e6) * p["in"] + (out_tok / 1e6) * p["out"]
        self.data["day_usd"] = round(self.day_usd + cost, 6)
        self.data["month_usd"] = round(self.month_usd + cost, 6)
        self.data["day_calls"] = int(self.data.get("day_calls", 0)) + 1
        self.data["month_calls"] = int(self.data.get("month_calls", 0)) + 1
        self._save()
        return cost

    def summary(self) -> str:
        self._roll()
        d, m = self.cap("daily_budget_usd", 0.30), self.cap("monthly_budget_usd", 5.0)
        day = f"${self.day_usd:.3f}" + (f" / ${d:.2f}" if d > 0 else "")
        mon = f"${self.month_usd:.2f}" + (f" / ${m:.2f}" if m > 0 else "")
        calls = self.data.get("day_calls", 0)
        line = f"today {day} ({calls} calls) · this month {mon}"
        return line + ("  — capped, offline until it resets" if self.over() else "")
