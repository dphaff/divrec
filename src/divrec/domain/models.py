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
    crest_bucket: CrestBucket | None = None


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


def make_account_number(client_number: str, product_code: int) -> str:
    """Deterministic account reference.

    v1 placeholder: format is stable and testable, but can be swapped later.
    """
    return f"{client_number}-{product_code:02d}"


def aggregate_internal_shares_by_bucket(
    internal_holdings: list[InternalHolding],
) -> dict[CrestBucket, int]:
    totals: dict[CrestBucket, int] = {"ISA": 0, "SIPP": 0, "GIA": 0}
    for h in internal_holdings:
        totals[h.crest_bucket] += int(h.shares)
    return totals


def aggregate_cash_by_bucket(client_lines: list[CreditLine]) -> dict[CrestBucket, Decimal]:
    totals: dict[CrestBucket, Decimal] = {
        "ISA": Decimal("0.00"),
        "SIPP": Decimal("0.00"),
        "GIA": Decimal("0.00"),
    }
    for ln in client_lines:
        totals[ln.crest_bucket] = totals[ln.crest_bucket] + ln.cash_credited
    return totals


@dataclass(frozen=True, slots=True)
class BucketReconResult:
    crest_bucket: CrestBucket
    crest_shares: int
    internal_shares: int
    shares_diff: int
    crest_cash: Decimal
    internal_cash_pre_residual: Decimal
    residual_to_house: Decimal
    internal_cash_post_residual: Decimal
    cash_diff_post_residual: Decimal
    pass_bucket: bool


@dataclass(frozen=True, slots=True)
class RunReconResult:
    run_id: str
    isin: str
    record_date: str
    pay_date: str
    bucket_results: list[BucketReconResult]
    pass_run: bool
    fail_reasons: list[str]  # e.g. ["SHARES_MISMATCH:ISA", "RESIDUAL_EXCEEDS_TOLERANCE:SIPP"]