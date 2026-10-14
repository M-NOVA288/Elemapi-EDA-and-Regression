"""Reading structured logs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable


@dataclass
class LogSet:
    records: list[dict] = field(default_factory=list)
    malformed: int = 0


def parse_ts(value: str) -> datetime:
    # Accepts ISO 8601 with a trailing Z (as produced by JavaScript's toISOString()).
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_lines(lines: Iterable[str]) -> LogSet:
    """Parse JSON-lines. Bad lines are counted, not fatal: a log pipeline must survive garbage input."""
    out = LogSet()
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
            if not isinstance(rec, dict) or "ts" not in rec or "event" not in rec:
                raise ValueError("missing ts/event")
            rec["_ts"] = parse_ts(rec["ts"])
            out.records.append(rec)
        except (ValueError, TypeError):
            out.malformed += 1
    out.records.sort(key=lambda r: r["_ts"])
    return out


def read_file(path: str) -> LogSet:
    with open(path, encoding="utf-8") as f:
        return read_lines(f)


def is_good(rec: dict) -> bool:
    """A record counts against the SLO if it is an error, or explicitly marked ok=false."""
    if rec.get("ok") is False:
        return False
    return rec.get("level") != "error"
