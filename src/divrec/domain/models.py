from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InternalHolding:
    isin: str
    record_date: str  # YYYY-MM-DD
    client_number: str
    product_code: int
    account_number: str
    shares: int