from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BreakRow:
    run_id: str
    isin: str
    crest_bucket: str | None
    break_type: str
    details: str
    crest_value: str
    internal_value: str