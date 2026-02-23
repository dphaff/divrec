from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

CrestBucket = Literal["ISA", "SIPP", "GIA"]


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
    crest_bucket: CrestBucket
    shares: int
    dividend_per_share: Decimal
    cash_credited: Decimal


@dataclass(frozen=True, slots=True)
class CreditLine:
    run_id: str
    isin: str
    record_date: str
    pay_date: str
    client_number: str
    product_code: int
    account_number: str
    crest_bucket: CrestBucket
    shares: int
    dividend_per_share: Decimal
    cash_credited: Decimal
    line_type: str  # "CLIENT" | "HOUSE_ROUNDING"