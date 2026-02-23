from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

@dataclass(frozen=True, slots=True)
class InternalHolding:
    isin: str
    record_date: str  # YYYY-MM-DD
    client_number: str
    product_code: int
    account_number: str
    shares: int

@dataclass(frozen=True, slots=True)
class CrestBucketSnapshot:
    """Single CREST dividend snapshot row at (isin, crest_bucket) grain."""

    isin: str
    record_date: str
    pay_date: str
    crest_bucket: Literal["ISA", "SIPP", "GIA"]
    shares: int
    dividend_per_share: Decimal
    cash_credited: Decimal